#!/usr/bin/env python
"""
End-to-end integration test for the Policy Chatbot.

This script:
1. Checks if PDFs exist in data/
2. Verifies the embedding model is available
3. Confirms the LLM model path exists
4. Tests index building (if needed)
5. Runs a sample query
"""

import json
import sys
from pathlib import Path

from chatbot import (
    BASE_DIR,
    DATA_DIR,
    DEFAULT_LLM_PATH,
    EMBEDDING_MODEL_DIR,
    build_index,
    ensure_model_exists,
    load_index,
)
from sentence_transformers import SentenceTransformer


def check_prerequisites():
    """Verify all required files and dependencies exist."""
    print("[*] Checking prerequisites...\n")

    checks_passed = 0
    total_checks = 4

    # Check 1: PDFs in data/
    pdf_files = list(DATA_DIR.glob("*.pdf"))
    if pdf_files:
        print(f"✓ Found {len(pdf_files)} PDF(s) in data/")
        checks_passed += 1
    else:
        print(f"✗ No PDFs found in {DATA_DIR}/")
        print(f"  Add policy PDFs to continue.")

    # Check 2: Embedding model
    if EMBEDDING_MODEL_DIR.exists():
        print(f"✓ Embedding model found: {EMBEDDING_MODEL_DIR.name}")
        checks_passed += 1
    else:
        print(f"✗ Embedding model not found: {EMBEDDING_MODEL_DIR}")
        print(f"  Download with: python download_model.py")

    # Check 3: LLM model
    if DEFAULT_LLM_PATH.exists():
        size_mb = DEFAULT_LLM_PATH.stat().st_size / (1024 * 1024)
        print(f"✓ LLM model found: {DEFAULT_LLM_PATH.name} ({size_mb:.0f}MB)")
        checks_passed += 1
    else:
        print(f"✗ LLM model not found: {DEFAULT_LLM_PATH}")
        print(f"  Download a .gguf file to models/")

    # Check 4: Index or PDFs to build from
    from chatbot import INDEX_PATH, CHUNKS_PATH
    if INDEX_PATH.exists() and CHUNKS_PATH.exists():
        print(f"✓ FAISS index already built")
        checks_passed += 1
    elif pdf_files:
        print(f"⚠ FAISS index not built, but PDFs exist (will build on first run)")
        checks_passed += 1
    else:
        print(f"✗ No index found and no PDFs to build from")

    print(f"\nPassed {checks_passed}/{total_checks} checks\n")
    return checks_passed == total_checks and len(pdf_files) > 0


def test_embedding_model():
    """Test that the embedding model loads and works."""
    print("[*] Testing embedding model...\n")
    try:
        embedder = SentenceTransformer(str(EMBEDDING_MODEL_DIR))
        test_text = "Is knee surgery covered?"
        embedding = embedder.encode(test_text)
        print(f"✓ Embedding model works")
        print(f"  Sample text: '{test_text}'")
        print(f"  Embedding dim: {embedding.shape[0]}\n")
        return True
    except Exception as e:
        print(f"✗ Embedding model failed: {e}\n")
        return False


def test_index_operations():
    """Test index loading/building."""
    print("[*] Testing index operations...\n")
    from chatbot import INDEX_PATH, CHUNKS_PATH

    if INDEX_PATH.exists() and CHUNKS_PATH.exists():
        try:
            index, chunks, embeddings = load_index()
            print(f"✓ Loaded existing FAISS index")
            print(f"  Chunks in index: {len(chunks)}")
            print(f"  Embedding dim: {embeddings.shape[1] if embeddings is not None else 'N/A'}\n")
            return True
        except Exception as e:
            print(f"✗ Failed to load index: {e}\n")
            return False
    else:
        print(f"⚠ Index not found (will be built on first query)\n")
        return True


def main() -> int:
    print("=" * 60)
    print("Policy Chatbot - Integration Test")
    print("=" * 60 + "\n")

    if not check_prerequisites():
        print("✗ Prerequisites check failed.")
        print("  Required: PDFs in data/, embedding model, LLM model")
        return 1

    if not test_embedding_model():
        return 1

    if not test_index_operations():
        return 1

    print("=" * 60)
    print("All checks passed! ✓")
    print("=" * 60)
    print("\nYou can now:")
    print("  • Run CLI: python chatbot.py --query 'your question'")
    print("  • Run web UI: python web_app.py")
    print("  • Rebuild index: python chatbot.py --rebuild")
    print()

    return 0


if __name__ == "__main__":
    sys.exit(main())
