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
INDEXES_STR = os.getenv("INDEXES", "")
PINECONE_INDEX_DIMENSION = int(os.getenv("PINECONE_INDEX_DIMENSION", "3072"))
PINECONE_CLOUD = os.getenv("PINECONE_CLOUD", "aws")
PINECONE_REGION = os.getenv("PINECONE_REGION", "us-east-1")

if not OPENAI_API_KEY or not PINECONE_API_KEY or not INDEXES_STR:
    raise ValueError("Missing API keys or INDEXES in .env")

# Parse indexes and their namespaces from .env
INDEXES = [idx.strip() for idx in INDEXES_STR.split(",")]

# Parse namespaces per index
INDEX_NAMESPACES = {}
for idx in INDEXES:
    # Convert index name to env var format (replace hyphens with underscores)
    env_key = f"NAMESPACES_{idx.upper().replace('-', '_')}"
    namespaces_str = os.getenv(env_key, "")
    if not namespaces_str:
        raise ValueError(f"Missing {env_key} in .env for index '{idx}'")
    INDEX_NAMESPACES[idx] = [ns.strip() for ns in namespaces_str.split(",")]

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
            print(f"✅ Created index: {idx} with namespaces: {', '.join(INDEX_NAMESPACES[idx])}")
        except Exception as e:
            print(f"⚠️  Could not create index '{idx}': {str(e)}")
            print(f"   Note: Existing indexes remain safe. Please create '{idx}' manually in Pinecone console if needed.")
    else:
        print(f"✅ Index exists: {idx} with namespaces: {', '.join(INDEX_NAMESPACES[idx])}")

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

@app.get("/indexes")
def get_indexes():
    """Return list of available indexes"""
    return {"indexes": INDEXES}

@app.get("/namespaces/{index_name}")
def get_namespaces(index_name: str):
    """Return list of available namespaces for a specific index"""
    if index_name not in INDEXES:
        return {
            "error": f"Invalid index: {index_name}. Valid indexes: {', '.join(INDEXES)}",
            "status": 400
        }
    return {"namespaces": INDEX_NAMESPACES[index_name]}

@app.post("/upload")
async def upload(
    index_name: str = Form(...), 
    namespaces: str = Form(...),  # comma-separated namespace names
    files: List[UploadFile] = File(...)
):
    """Upload files to specific index and namespaces(s)"""
    
    # Validate index
    if index_name not in INDEXES:
        return {
            "error": f"Invalid index: {index_name}. Valid indexes: {', '.join(INDEXES)}",
            "status": 400
        }
    
    # Parse and validate namespaces
    namespace_list = [ns.strip() for ns in namespaces.split(",")]
    valid_namespaces = INDEX_NAMESPACES[index_name]
    
    for ns in namespace_list:
        if ns not in valid_namespaces:
            return {
                "error": f"Invalid namespace '{ns}' for index '{index_name}'. Valid namespaces: {', '.join(valid_namespaces)}",
                "status": 400
            }
    
    index = pc.Index(index_name)
    all_chunks = []

    # Extract text from all files
    for file in files:
        text = await extract_text(file)
        # Split by newlines and filter out very small chunks
        chunks = [c.strip() for c in text.split("\n") if len(c.strip()) > 10]
        all_chunks.extend(chunks)

    embeddings = get_embeddings(all_chunks)

    # Upsert to all specified namespaces
    total_uploaded = 0
    for namespace in namespace_list:
        vectors = []
        for chunk, emb in zip(all_chunks, embeddings):
            chunk_id = hashlib.sha256((chunk + namespace).encode()).hexdigest()  # Unique ID per namespace
            vectors.append({
                "id": chunk_id,
                "values": emb,
                "metadata": {
                    "text": chunk,
                    "namespace": namespace,
                    "index": index_name,
                    "organization": os.getenv("ORGANIZATION_NAME", "Unknown"),
                    "timestamp": str(datetime.utcnow())
                }
            })

        BATCH_SIZE = 50  # safe size
        for i in range(0, len(vectors), BATCH_SIZE):
            batch = vectors[i:i + BATCH_SIZE]
            index.upsert(vectors=batch, namespace=namespace)
        
        total_uploaded += len(vectors)

    return {
        "message": f"Upload successful to {len(namespace_list)} namespace(s)",
        "index": index_name,
        "namespaces": namespace_list,
        "chunks_uploaded": total_uploaded
    }

@app.get("/stats")
def stats():
    """Return stats for all indexes and their namespaces"""
    result = []
    existing_indexes = pc.list_indexes().names()
    
    for idx in INDEXES:
        if idx in existing_indexes:
            try:
                index = pc.Index(idx)
                # Get stats for the index (includes all namespaces)
                info = index.describe_index_stats()
                
                # Get stats for each namespace
                for namespace in INDEX_NAMESPACES[idx]:
                    # Check if namespace exists in the stats response
                    if hasattr(info, 'namespaces') and info.namespaces:
                        ns_data = info.namespaces.get(namespace, {})
                        vector_count = ns_data.get('vector_count', 0) if isinstance(ns_data, dict) else getattr(ns_data, 'vector_count', 0)
                    else:
                        vector_count = 0
                    
                    result.append({
                        "index": idx,
                        "namespace": namespace,
                        "documents": vector_count
                    })
            except Exception as e:
                print(f"Error getting stats for index {idx}: {str(e)}")
                # If error, show all namespaces with 0
                for namespace in INDEX_NAMESPACES[idx]:
                    result.append({
                        "index": idx,
                        "namespace": namespace,
                        "documents": 0
                    })
        else:
            # Index doesn't exist yet, show all namespaces with 0
            for namespace in INDEX_NAMESPACES[idx]:
                result.append({
                    "index": idx,
                    "namespace": namespace,
                    "documents": 0
                })
    
    return result