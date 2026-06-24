"""
Configuration file for Spatial Transcriptomics Intelligent Analysis Platform
"""
import os
from pathlib import Path
from dotenv import load_dotenv

# Load environment variables
load_dotenv()

# Base directory
BASE_DIR = Path(__file__).parent

# Storage directories
STORAGE_DIR = BASE_DIR / "storage"
UPLOADS_DIR = STORAGE_DIR / "uploads"
CACHE_DIR = STORAGE_DIR / "cache"
RESULTS_DIR = STORAGE_DIR / "results"
PLOTS_DIR = STORAGE_DIR / "plots"

# Create directories if they don't exist
for dir_path in [UPLOADS_DIR, CACHE_DIR, RESULTS_DIR, PLOTS_DIR]:
    dir_path.mkdir(parents=True, exist_ok=True)

# API Keys (for LLM)
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
ANTHROPIC_API_KEY = os.getenv("ANTHROPIC_API_KEY", "")

# Default Analysis Parameters
DEFAULT_PARAMS = {
    "qc": {
        "min_genes": 200,
        "min_cells": 3,
        "max_pct_mito": 20.0,
    },
    "preprocessing": {
        "n_top_genes": 2000,
        "target_sum": 1e4,
    },
    "clustering": {
        "n_pcs": 50,
        "n_neighbors": 15,
        "resolution": 1.0,
        "method": "leiden",
    },
    "visualization": {
        "figsize": (10, 8),
        "dpi": 150,
    },
}

# Agent Configuration
AGENT_CONFIG = {
    "max_retries": 3,
    "timeout_seconds": 300,
    "model_name": "gpt-4",  # or "claude-3-opus-20240229"
}

# Supported file formats
SUPPORTED_FORMATS = [".h5ad", ".h5", ".csv", ".txt"]

# Example datasets
EXAMPLE_DATASETS = {
    "mouse_organogenesis": {
        "name": "Digital reconstruction of full embryos during early mouse organogenesis",
        "doi": "https://doi.org/10.1016/j.cell.2025.05.035",
        "geo_accession": "GSE278603",
        "format": "h5ad",
    }
}
