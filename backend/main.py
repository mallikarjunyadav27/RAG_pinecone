import os
import hashlib
from datetime import datetime
from fastapi import FastAPI, UploadFile, File, Form
from fastapi.middleware.cors import CORSMiddleware
from typing import List

import pdfplumber
from docx import Document
from dotenv import load_dotenv

from openai import OpenAI
from pinecone import Pinecone, ServerlessSpec

# Load env
load_dotenv()

OPENAI_API_KEY = os.getenv("OPENAI_API_KEY")
PINECONE_API_KEY = os.getenv("PINECONE_API_KEY")
DEPARTMENTS_STR = os.getenv("DEPARTMENTS", "")
PINECONE_INDEX_DIMENSION = int(os.getenv("PINECONE_INDEX_DIMENSION", "3072"))
PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")
PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1")

if not OPENAI_API_KEY or not PINECONE_API_KEY or not DEPARTMENTS_STR:
    raise ValueError("Missing API keys or DEPARTMENTS in .env")

# Parse departments from .env
INDEXES = [dept.strip() for dept in DEPARTMENTS_STR.split(",")]

# OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# Pinecone
pc = Pinecone(api_key=PINECONE_API_KEY)

# Create indexes if not exist (safe - won't affect existing indexes)
existing = pc.list_indexes().names()
for idx in INDEXES:
    if idx not in existing:
        try:
            pc.create_index(
                name=idx,
                dimension=PINECONE_INDEX_DIMENSION,
                metric="cosine",
                spec=ServerlessSpec(cloud=PINECONE_CLOUD, region=PINECONE_REGION)
            )
            print(f"✅ Created index: {idx}")
        except Exception as e:
            print(f"⚠️  Could not create index '{idx}': {str(e)[:100]}...")
            print(f"   Note: Existing indexes remain safe. Please create '{idx}' manually in Pinecone console if needed.")
    else:
        print(f"✅ Index exists: {idx}")

app = FastAPI()

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# 🔹 File text extraction
async def extract_text(file):
    name = file.filename.lower()

    if name.endswith(".pdf"):
        with pdfplumber.open(file.file) as pdf:
            return "\n".join([p.extract_text() or "" for p in pdf.pages])

    elif name.endswith(".docx"):
        doc = Document(file.file)
        return "\n".join([p.text for p in doc.paragraphs])

    elif name.endswith(".txt"):
        return (await file.read()).decode()

    return ""

# 🔹 Embedding
def get_embeddings(chunks, batch_size=100):
    all_embeddings = []
    for i in range(0, len(chunks), batch_size):
        batch = chunks[i:i + batch_size]
        res = client.embeddings.create(
            model="text-embedding-3-large",
            input=batch
        )
        all_embeddings.extend([r.embedding for r in res.data])
    return all_embeddings

@app.get("/")
def health():
    return {"status": "Backend running"}

@app.get("/departments")
def get_departments():
    """Return list of available departments"""
    return {"departments": INDEXES}

@app.post("/upload")
async def upload(department: str = Form(...), files: List[UploadFile] = File(...)):
    # Validate department
    if department not in INDEXES:
        return {
            "error": f"Invalid department: {department}. Valid departments: {', '.join(INDEXES)}",
            "status": 400
        }
    
    index = pc.Index(department)

    all_chunks = []

    for file in files:
        text = await extract_text(file)
        # Split by newlines and filter out very small chunks
        chunks = [c.strip() for c in text.split("\n") if len(c.strip()) > 10]
        all_chunks.extend(chunks)

    embeddings = get_embeddings(all_chunks)

    vectors = []
    for chunk, emb in zip(all_chunks, embeddings):
        chunk_id = hashlib.sha256(chunk.encode()).hexdigest()
        vectors.append({
            "id": chunk_id,
            "values": emb,
            "metadata": {
                "text": chunk,
                "department": department,
                "organization": os.getenv("ORGANIZATION_NAME", "Unknown"),
                "timestamp": str(datetime.utcnow())
            }
        })

    BATCH_SIZE = 50  # safe size

    for i in range(0, len(vectors), BATCH_SIZE):
        batch = vectors[i:i + BATCH_SIZE]
        index.upsert(vectors=batch)

    return {
        "message": "Upload successful",
        "chunks_uploaded": len(vectors)
    }

@app.get("/stats")
def stats():
    result = []
    existing_indexes = pc.list_indexes().names()
    for idx in INDEXES:
        if idx in existing_indexes:
            try:
                index = pc.Index(idx)
                info = index.describe_index_stats()
                result.append({
                    "department": idx,
                    "documents": info.total_vector_count
                })
            except Exception as e:
                # Include index with 0 documents if there's an error
                result.append({
                    "department": idx,
                    "documents": 0
                })
        else:
            # Index doesn't exist yet, show with 0 documents
            result.append({
                "department": idx,
                "documents": 0
            })
    return result