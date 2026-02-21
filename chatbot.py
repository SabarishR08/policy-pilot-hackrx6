"""Policy Pilot: Offline AI-powered document analysis chatbot.

This module provides semantic search and local LLM inference capabilities
to analyze insurance policy documents and answer queries with structured JSON responses.

Example:
    CLI usage:
        python chatbot.py --query "Is knee surgery covered?"
        
    Python import:
        from chatbot import retrieve_chunks, run_llm, normalize_response
"""

import argparse
import json
import logging
import os
import pickle
import re
import sys
from pathlib import Path

import faiss
import numpy as np
import PyPDF2
from jsonschema import ValidationError, validate
from llama_cpp import Llama
from sentence_transformers import SentenceTransformer

# Configure logging
logging.basicConfig(
    format="[%(levelname)s] %(message)s",
    level=logging.INFO,
)
logger = logging.getLogger(__name__)

BASE_DIR = Path(__file__).resolve().parent
DATA_DIR = BASE_DIR / "data"
CLEANED_DIR = BASE_DIR / "cleaned_data"
INDEX_DIR = BASE_DIR / "index"
INDEX_PATH = INDEX_DIR / "faiss.index"
CHUNKS_PATH = INDEX_DIR / "chunks.pkl"
EMBEDDINGS_PATH = INDEX_DIR / "embeddings.npy"

EMBEDDING_MODEL_DIR = BASE_DIR / "all-MiniLM-L6-v2-offline"
DEFAULT_LLM_PATH = BASE_DIR / "models" / "tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf"

RESPONSE_SCHEMA = {
    "type": "object",
    "required": ["Decision", "Amount", "Justification"],
    "properties": {
        "Decision": {"type": "string"},
        "Amount": {"type": "string"},
        "Justification": {
            "type": "array",
            "items": {
                "type": "object",
                "required": ["ClauseID", "Text"],
                "properties": {
                    "ClauseID": {"type": "string"},
                    "Text": {"type": "string"},
                },
            },
        },
    },
}


def extract_text_from_pdf(pdf_path: Path) -> str:
    text = ""
    with pdf_path.open("rb") as handle:
        reader = PyPDF2.PdfReader(handle)
        for page in reader.pages:
            page_text = page.extract_text() or ""
            text += page_text + "\n"
    return text


def clean_text(raw_text: str) -> str:
    cleaned_lines = []
    for line in raw_text.split("\n"):
        line = line.strip()
        if not line:
            continue
        if re.search(r"(Reg\. No\.|Page \d+|www\.|E-mail:)", line, re.I):
            continue
        cleaned_lines.append(line)
    return "\n".join(cleaned_lines)


def chunk_text(text: str, chunk_size: int = 1000, overlap: int = 150) -> list[str]:
    text = re.sub(r"\s+", " ", text).strip()
    if not text:
        return []
    chunks = []
    start = 0
    while start < len(text):
        end = min(len(text), start + chunk_size)
        chunk = text[start:end].strip()
        if chunk:
            chunks.append(chunk)
        if end >= len(text):
            break
        start = max(0, end - overlap)
    return chunks


def load_documents(use_cleaned: bool) -> list[dict]:
    documents = []
    if use_cleaned and CLEANED_DIR.exists():
        for txt_path in sorted(CLEANED_DIR.glob("*.txt")):
            text = txt_path.read_text(encoding="utf-8", errors="ignore")
            documents.append({"source": txt_path.stem, "text": text})
        if documents:
            return documents

    for pdf_path in sorted(DATA_DIR.glob("*.pdf")):
        raw = extract_text_from_pdf(pdf_path)
        documents.append({"source": pdf_path.stem, "text": clean_text(raw)})
    return documents


def build_index(
    embedder: SentenceTransformer,
    use_cleaned: bool,
    chunk_size: int,
    overlap: int,
) -> tuple[faiss.IndexFlatIP, list[dict], np.ndarray]:
    documents = load_documents(use_cleaned)
    if not documents:
        raise FileNotFoundError("No PDF or cleaned text files found.")

    chunks = []
    for doc in documents:
        for idx, chunk in enumerate(chunk_text(doc["text"], chunk_size, overlap)):
            chunks.append(
                {
                    "id": f"{doc['source']}__{idx}",
                    "source": doc["source"],
                    "text": chunk,
                }
            )

    texts = [chunk["text"] for chunk in chunks]
    embeddings = embedder.encode(
        texts,
        batch_size=32,
        show_progress_bar=True,
        normalize_embeddings=True,
    )
    embeddings = np.asarray(embeddings, dtype="float32")

    index = faiss.IndexFlatIP(embeddings.shape[1])
    index.add(embeddings)

    INDEX_DIR.mkdir(parents=True, exist_ok=True)
    faiss.write_index(index, str(INDEX_PATH))
    np.save(EMBEDDINGS_PATH, embeddings)
    with CHUNKS_PATH.open("wb") as handle:
        pickle.dump(chunks, handle)

    return index, chunks, embeddings


def load_index() -> tuple[faiss.Index, list[dict], np.ndarray]:
    if not INDEX_PATH.exists() or not CHUNKS_PATH.exists():
        raise FileNotFoundError("Index not found. Build it first.")
    index = faiss.read_index(str(INDEX_PATH))
    embeddings = None
    if EMBEDDINGS_PATH.exists():
        embeddings = np.load(EMBEDDINGS_PATH)
    with CHUNKS_PATH.open("rb") as handle:
        chunks = pickle.load(handle)
    return index, chunks, embeddings


def retrieve_chunks(
    query: str,
    embedder: SentenceTransformer,
    index: faiss.Index,
    chunks: list[dict],
    top_k: int,
) -> list[dict]:
    query_vec = embedder.encode([query], normalize_embeddings=True)
    query_vec = np.asarray(query_vec, dtype="float32")
    _, indices = index.search(query_vec, top_k)
    results = []
    for idx in indices[0]:
        if idx < 0:
            continue
        results.append(chunks[idx])
    return results


def build_prompt(query: str, context_chunks: list[dict]) -> str:
    context_text = "\n\n".join(
        f"ClauseID: {chunk['id']}\nText: {chunk['text']}" for chunk in context_chunks
    )
    return (
        "You are an insurance claim assistant. "
        "Answer only using the provided clauses. "
        "Return a JSON object with keys: Decision, Amount, Justification. "
        "Justification must be a list of {ClauseID, Text}. "
        "Return only JSON, no extra text.\n\n"
        f"Query: {query}\n\nRelevant Clauses:\n{context_text}\n"
    )


def extract_json(text: str) -> dict | None:
    start = text.find("{")
    end = text.rfind("}")
    if start == -1 or end == -1 or end <= start:
        return None
    candidate = text[start : end + 1]
    try:
        return json.loads(candidate)
    except json.JSONDecodeError:
        return None


def normalize_response(data: dict | None) -> dict | None:
    if not isinstance(data, dict):
        return None
    decision = str(data.get("Decision", "Unknown"))
    amount = str(data.get("Amount", "N/A"))
    justification = data.get("Justification", [])
    if not isinstance(justification, list):
        justification = []

    cleaned = []
    for item in justification:
        if not isinstance(item, dict):
            continue
        clause_id = item.get("ClauseID")
        text = item.get("Text")
        if clause_id is None or text is None:
            continue
        cleaned.append({"ClauseID": str(clause_id), "Text": str(text)})

    candidate = {
        "Decision": decision,
        "Amount": amount,
        "Justification": cleaned,
    }
    try:
        validate(instance=candidate, schema=RESPONSE_SCHEMA)
    except ValidationError:
        return None
    return candidate


def run_llm(
    llm: Llama,
    prompt: str,
    max_tokens: int,
    temperature: float,
) -> dict:
    response = llm(
        prompt,
        max_tokens=max_tokens,
        temperature=temperature,
        stop=["</s>"],
    )
    raw = response.get("choices", [{}])[0].get("text", "").strip()
    parsed = extract_json(raw)
    normalized = normalize_response(parsed)
    if normalized is not None:
        return normalized
    return {
        "Decision": "Unknown",
        "Amount": "N/A",
        "Justification": [],
    }


def ensure_model_exists(path: Path) -> None:
    if not path.exists():
        raise FileNotFoundError(f"LLM model not found: {path}")


def main() -> int:
    parser = argparse.ArgumentParser(description="Offline policy document chatbot")
    parser.add_argument("--build-index", action="store_true", help="Build the FAISS index")
    parser.add_argument("--rebuild", action="store_true", help="Rebuild index from scratch")
    parser.add_argument("--use-cleaned", action="store_true", help="Use cleaned_data/*.txt if available")
    parser.add_argument("--query", type=str, help="Single query to run")
    parser.add_argument("--top-k", type=int, default=3, help="Number of chunks to retrieve")
    parser.add_argument("--chunk-size", type=int, default=1000, help="Chunk size in characters")
    parser.add_argument("--overlap", type=int, default=150, help="Chunk overlap in characters")
    parser.add_argument("--max-tokens", type=int, default=256, help="Max tokens to generate")
    parser.add_argument("--temperature", type=float, default=0.2, help="LLM temperature")
    parser.add_argument("--n-ctx", type=int, default=2048, help="LLM context size")
    parser.add_argument("--n-threads", type=int, default=4, help="LLM CPU threads")
    parser.add_argument("--model-path", type=str, default=str(DEFAULT_LLM_PATH), help="Path to GGUF model")
    args = parser.parse_args()

    embedder = SentenceTransformer(str(EMBEDDING_MODEL_DIR))

    if args.rebuild:
        if INDEX_PATH.exists():
            INDEX_PATH.unlink(missing_ok=True)
        if CHUNKS_PATH.exists():
            CHUNKS_PATH.unlink(missing_ok=True)
        if EMBEDDINGS_PATH.exists():
            EMBEDDINGS_PATH.unlink(missing_ok=True)

    if args.build_index or args.rebuild or not INDEX_PATH.exists() or not CHUNKS_PATH.exists():
        print("[*] Building index...")
        index, chunks, _ = build_index(
            embedder,
            use_cleaned=args.use_cleaned,
            chunk_size=args.chunk_size,
            overlap=args.overlap,
        )
    else:
        index, chunks, _ = load_index()

    ensure_model_exists(Path(args.model_path))
    print("[*] Loading LLM...")
    llm = Llama(model_path=args.model_path, n_ctx=args.n_ctx, n_threads=args.n_threads)

    def handle_query(query: str) -> None:
        context = retrieve_chunks(query, embedder, index, chunks, args.top_k)
        prompt = build_prompt(query, context)
        answer = run_llm(llm, prompt, args.max_tokens, args.temperature)
        if not answer.get("Justification"):
            answer["Justification"] = [
                {"ClauseID": chunk["id"], "Text": chunk["text"]} for chunk in context
            ]
        print(json.dumps(answer, indent=2))

    if args.query:
        handle_query(args.query)
        return 0

    print("Enter your insurance query below. Type 'exit' to quit.\n")
    while True:
        user_query = input("Query: ").strip()
        if user_query.lower() in {"exit", "quit"}:
            break
        handle_query(user_query)

    return 0


if __name__ == "__main__":
    sys.exit(main())
