"""
Flask web application for PolicyPilot offline policy chatbot.

This module provides a REST API and web interface for querying insurance policies
using semantic search and local LLM inference. Users can upload PDF documents,
build FAISS indexes, and retrieve policy information with LLM-generated responses.

Example:
    Start the web server::

        $ python web_app.py
        Running on http://127.0.0.1:5000

    Then open your browser and upload a PDF, build the index, and query.

Module-level attributes:
    APP: Flask application instance
    STATE: Global dictionary for storing model and index state
"""

import json
import logging
from pathlib import Path

from flask import Flask, redirect, render_template, request, url_for
from werkzeug.utils import secure_filename

from chatbot import (
    BASE_DIR,
    CLEANED_DIR,
    DEFAULT_LLM_PATH,
    build_index,
    build_prompt,
    ensure_model_exists,
    load_index,
    retrieve_chunks,
    run_llm,
)
from sentence_transformers import SentenceTransformer
from llama_cpp import Llama

# Configure logging
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

APP = Flask(__name__)
APP.config["UPLOAD_FOLDER"] = str((BASE_DIR / "data").resolve())
APP.config["MAX_CONTENT_LENGTH"] = 25 * 1024 * 1024  # 25 MB upload limit

STATE = {
    "embedder": None,      # SentenceTransformer model for embeddings
    "index": None,         # FAISS index for semantic search
    "chunks": None,        # List of text chunks corresponding to index
    "llm": None,           # Llama-cpp-python LLM instance
    "status": "",          # Current status message for web UI
}


def get_embedder() -> SentenceTransformer:
    """
    Lazily load and return the sentence transformer for embeddings.
    
    Loads the all-MiniLM-L6-v2-offline model on first call and caches it
    in STATE to avoid reloading on subsequent calls.
    
    Returns:
        SentenceTransformer: Initialized embedding model (384-dimensional).
        
    Raises:
        OSError: If model files not found in BASE_DIR/all-MiniLM-L6-v2-offline/
    """
    if STATE["embedder"] is None:
        logger.info("Loading embedding model: all-MiniLM-L6-v2-offline")
        STATE["embedder"] = SentenceTransformer(str(BASE_DIR / "all-MiniLM-L6-v2-offline"))
        logger.info("Embedding model loaded successfully")
    return STATE["embedder"]


def get_llm(model_path: Path, n_ctx: int, n_threads: int) -> Llama:
    """
    Lazily load and return the LLM for inference.
    
    Initializes llama-cpp-python with specified context and thread parameters.
    The model is cached in STATE to avoid reloading on subsequent calls.
    
    Args:
        model_path: Path to GGUF model file (e.g., tinyllama-1.1b-chat).
        n_ctx: Context window size in tokens (e.g., 2048).
        n_threads: Number of CPU threads for inference (e.g., 4-8).
        
    Returns:
        Llama: Initialized language model ready for inference.
        
    Raises:
        FileNotFoundError: If model file not found at model_path.
        RuntimeError: If llama-cpp-python fails to initialize.
    """
    if STATE["llm"] is None:
        logger.info(f"Loading LLM model from {model_path}")
        ensure_model_exists(model_path)
        STATE["llm"] = Llama(model_path=str(model_path), n_ctx=n_ctx, n_threads=n_threads)
        logger.info(f"LLM model loaded successfully with {n_threads} threads, {n_ctx} context")
    return STATE["llm"]


def ensure_index(
    rebuild: bool,
    use_cleaned: bool,
    chunk_size: int,
    overlap: int,
) -> None:
    """
    Ensure FAISS index is loaded or built, handling rebuild logic.
    
    This function implements lazy loading with rebuild capability. It either:
    1. Rebuilds the index from PDFs if rebuild=True
    2. Loads from cache if available
    3. Builds from PDFs if no cache exists
    
    Updates STATE["index"] and STATE["chunks"] with the loaded/built data.
    
    Args:
        rebuild: If True, rebuild index from all PDFs in data/ or cleaned_data/.
        use_cleaned: If True, use PDFs from cleaned_data/; otherwise use data/.
        chunk_size: Number of characters per chunk (e.g., 1000).
        overlap: Overlap between consecutive chunks in characters (e.g., 150).
        
    Returns:
        None (updates STATE dictionary in-place)
        
    Raises:
        FileNotFoundError: If no PDFs found and no cache exists.
        ValueError: If invalid chunk_size or overlap parameters.
    """
    embedder = get_embedder()
    if rebuild:
        logger.info(f"Rebuilding index with chunk_size={chunk_size}, overlap={overlap}")
        index, chunks, _ = build_index(embedder, use_cleaned, chunk_size, overlap)
        STATE["index"] = index
        STATE["chunks"] = chunks
        STATE["status"] = f"Index rebuilt from documents ({len(chunks)} chunks)."
        logger.info(f"Index rebuild complete: {len(chunks)} chunks indexed")
        return

    if STATE["index"] is None or STATE["chunks"] is None:
        try:
            logger.info("Attempting to load cached index")
            index, chunks, _ = load_index()
            STATE["index"] = index
            STATE["chunks"] = chunks
            STATE["status"] = f"Loaded existing index ({len(chunks)} chunks)."
            logger.info(f"Loaded cached index with {len(chunks)} chunks")
        except FileNotFoundError:
            logger.warning("No cached index found, building from documents")
            index, chunks, _ = build_index(embedder, use_cleaned, chunk_size, overlap)
            STATE["index"] = index
            STATE["chunks"] = chunks
            STATE["status"] = f"Index built from documents ({len(chunks)} chunks)."
            logger.info(f"Built index from scratch: {len(chunks)} chunks indexed")


@APP.route("/", methods=["GET"])
def home():
    """
    Render home page with current application status.
    
    Displays the web interface for PDF upload, index building, and querying.
    Shows current status, previous answers, and any errors.
    
    Returns:
        str: Rendered HTML template with status information.
    """
    logger.info("Home page accessed")
    return render_template(
        "index.html",
        status=STATE.get("status", ""),
        answer=None,
        error=None,
    )


@APP.route("/upload", methods=["POST"])
def upload():
    """
    Handle PDF file upload request.
    
    Validates file (must be PDF), saves to data/ folder, and updates status.
    Shows error if no file or non-PDF file uploaded. User must rebuild index
    to include the newly uploaded file.
    
    Form parameters:
        pdf: The PDF file to upload (multipart/form-data)
    
    Returns:
        str: Rendered HTML with upload success/error message.
        
    Raises:
        werkzeug.exceptions.BadRequestKeyError: If 'pdf' field missing.
    """
    logger.info("File upload requested")
    file = request.files.get("pdf")
    if file is None or not file.filename:
        logger.warning("Upload rejected: no file selected")
        return render_template("index.html", status="", answer=None, error="No file selected.")

    filename = secure_filename(file.filename)
    if not filename.lower().endswith(".pdf"):
        logger.warning(f"Upload rejected: non-PDF file '{filename}'")
        return render_template("index.html", status="", answer=None, error="Only PDF files are allowed.")

    upload_path = Path(APP.config["UPLOAD_FOLDER"]) / filename
    upload_path.parent.mkdir(parents=True, exist_ok=True)
    file.save(upload_path)
    logger.info(f"File uploaded successfully: {filename}")

    STATE["status"] = f"Uploaded {filename}. Rebuild the index to include it."
    return redirect(url_for("home"))


@APP.route("/build", methods=["POST"])
def build():
    """
    Build or rebuild the FAISS index from PDF documents.
    
    Creates a semantic index from all PDFs in data/ or cleaned_data/ folders.
    This must be done before querying. Supports customization of chunking strategy.
    
    Form parameters:
        use_cleaned: If 'on', use cleaned_data/; otherwise use data/.
        chunk_size: Characters per chunk (default: 1000).
        overlap: Overlap between chunks in characters (default: 150).
    
    Returns:
        redirect: Redirects to home page with updated status.
    """
    logger.info("Index build requested")
    use_cleaned = bool(request.form.get("use_cleaned"))
    chunk_size = int(request.form.get("chunk_size", 1000))
    overlap = int(request.form.get("overlap", 150))
    ensure_index(True, use_cleaned, chunk_size, overlap)
    logger.info(f"Index build completed. Status: {STATE.get('status')}")
    return redirect(url_for("home"))


@APP.route("/query", methods=["POST"])
def query():
    """
    Process a user query against the indexed policy documents.
    
    Retrieves relevant clauses via semantic search and generates a response
    using the local LLM. Validates the response against JSON schema.
    Allows customization of retrieval and generation parameters.
    
    Form parameters:
        query: The user's question (required).
        use_cleaned: If 'on', use cleaned data for indexing.
        chunk_size: Chunk size for indexing (default: 1000).
        overlap: Chunk overlap for indexing (default: 150).
        top_k: Number of clauses to retrieve (default: 3).
        max_tokens: Max tokens in LLM response (default: 256).
        temperature: LLM creativity (0.0-1.0, default: 0.2).
        n_ctx: LLM context window size (default: 2048).
        n_threads: CPU threads for inference (default: 4).
        model_path: Path to GGUF model (default: models/tinyllama-*.gguf).
    
    Returns:
        str: Rendered HTML with JSON response or error message.
        
    Raises:
        ValueError: If invalid numeric parameters provided.
    """
    logger.info("Query received")
    user_query = request.form.get("query", "").strip()
    if not user_query:
        logger.warning("Query rejected: empty query")
        return render_template("index.html", status="", answer=None, error="Enter a query.")

    # Extract form parameters
    use_cleaned = bool(request.form.get("use_cleaned"))
    chunk_size = int(request.form.get("chunk_size", 1000))
    overlap = int(request.form.get("overlap", 150))
    top_k = int(request.form.get("top_k", 3))
    max_tokens = int(request.form.get("max_tokens", 256))
    temperature = float(request.form.get("temperature", 0.2))
    n_ctx = int(request.form.get("n_ctx", 2048))
    n_threads = int(request.form.get("n_threads", 4))
    model_path = Path(request.form.get("model_path") or DEFAULT_LLM_PATH)

    logger.info(f"Query processing: '{user_query[:50]}...' with top_k={top_k}, temp={temperature}")

    # Ensure index is ready
    ensure_index(False, use_cleaned, chunk_size, overlap)

    # Perform semantic search and LLM inference
    embedder = get_embedder()
    llm = get_llm(model_path, n_ctx, n_threads)
    context = retrieve_chunks(user_query, embedder, STATE["index"], STATE["chunks"], top_k)
    logger.info(f"Retrieved {len(context)} relevant chunks")
    
    prompt = build_prompt(user_query, context)
    answer = run_llm(llm, prompt, max_tokens, temperature)
    logger.info(f"LLM response generated: {json.dumps(answer)[:100]}...")

    if not answer.get("Justification"):
        answer["Justification"] = [
            {"ClauseID": chunk["id"], "Text": chunk["text"]} for chunk in context
        ]

    pretty = json.dumps(answer, indent=2)
    return render_template(
        "index.html",
        status=STATE.get("status", ""),
        answer=pretty,
        error=None,
    )


if __name__ == "__main__":
    """
    Main entry point for Flask web application.
    
    Initializes required directories (data/, cleaned_data/) and starts
    the development server. For production, use Gunicorn instead:
    
        gunicorn --workers 4 --bind 0.0.0.0:5000 web_app:APP
    """
    logger.info("Initializing PolicyPilot web application")
    logger.info(f"Upload folder: {APP.config['UPLOAD_FOLDER']}")
    logger.info(f"Max upload size: {APP.config['MAX_CONTENT_LENGTH'] / (1024*1024):.0f} MB")
    
    DATA_DIR = BASE_DIR / "data"
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    CLEANED_DIR.mkdir(parents=True, exist_ok=True)
    
    logger.info("Starting Flask development server at http://127.0.0.1:5000")
    logger.info("Press Ctrl+C to stop")
    APP.run(host="127.0.0.1", port=5000, debug=False)
