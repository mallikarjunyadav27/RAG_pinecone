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

if not OPENAI_API_KEY or not PINECONE_API_KEY:
    raise ValueError("Missing API keys in .env")

# OpenAI
client = OpenAI(api_key=OPENAI_API_KEY)

# Pinecone
pc = Pinecone(api_key=PINECONE_API_KEY)

INDEXES = ["neurology", "general-medicine", "cardiology", "dentist", "pulmonology"]

# Create indexes if not exist
existing = pc.list_indexes().names()
for idx in INDEXES:
    if idx not in existing:
        pc.create_index(
        name=idx,
        dimension=3072,
            metric="cosine",
            spec=ServerlessSpec(cloud="azure", region="eastus2")
        )

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

@app.post("/upload")
async def upload(department: str = Form(...), files: List[UploadFile] = File(...)):
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
    for idx in INDEXES:
        index = pc.Index(idx)
        info = index.describe_index_stats()
        result.append({
            "department": idx,
            "documents": info.total_vector_count
        })
    return result