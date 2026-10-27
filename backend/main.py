"""
PULSE Backend - FastAPI Application Entry Point
Patient Update & Log Structuring Engine
NLP-based Clinical Handover Information Extraction and Event Structuring System
"""

import os
from contextlib import asynccontextmanager
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware
from backend.api.routes import router as api_router
from backend.api.training_routes import training_router
from backend.dataset.loader import dataset_loader
from backend.database.database import db
from backend.extraction.clinical_bert_extractor import clinical_bert_extractor

@asynccontextmanager
async def lifespan(app: FastAPI):
    # Startup: discover reports and calculate dataset stats
    print("Initializing PULSE backend...")
    reports = dataset_loader.discover_reports()
    print(f"Discovered {len(reports)} nursing handover reports in dataset directory.")
    stats = dataset_loader.calculate_statistics()
    print(f"Dynamic Corpus Stats: {stats['total_reports']} reports, avg words: {stats['average_word_count']}")
    # Sync reports cache to SQLite
    try:
        db.sync_reports_cache(reports)
        print("Synchronized reports index to SQLite cache.")
    except Exception as e:
        print(f"Notice: SQLite cache sync skipped: {e}")
    if clinical_bert_extractor.is_available():
        warmup_ms = clinical_bert_extractor.warmup()
        print(f"Bio_ClinicalBERT warmup complete in {warmup_ms} ms.")
    else:
        print("Bio_ClinicalBERT weights not loaded — hybrid rule fallback active.")
    yield
    print("Shutting down PULSE backend...")

app = FastAPI(
    title="PULSE: Patient Update & Log Structuring Engine",
    description="NLP-based Clinical Handover Information Extraction and Event Structuring System",
    version="1.0.0-prototype",
    lifespan=lifespan
)

# Enable CORS for local development
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Mount API routes
app.include_router(api_router)
app.include_router(training_router)

@app.get("/")
async def root():
    return {
        "name": "PULSE API",
        "description": "Patient Update & Log Structuring Engine",
        "subtitle": "NLP-based Clinical Handover Information Extraction and Event Structuring System",
        "docs_url": "/docs",
        "health_check": "/api/health",
        "disclaimer": "PULSE is an AI-assisted clinical information-organization prototype. It does not diagnose, prescribe treatment, or replace professional clinical judgment."
    }

if __name__ == "__main__":
    import uvicorn
    uvicorn.run("backend.main:app", host="127.0.0.1", port=8000, reload=True)
