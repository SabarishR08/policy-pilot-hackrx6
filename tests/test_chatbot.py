import json
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).parent.parent))

from chatbot import build_prompt, chunk_text, extract_json, normalize_response


def test_extract_json_from_text():
    payload = {"Decision": "Approved", "Amount": "5000", "Justification": []}
    wrapped = f"Here is the answer: {json.dumps(payload)} Thank you."
    assert extract_json(wrapped) == payload


def test_normalize_response_accepts_valid():
    data = {
        "Decision": "Rejected",
        "Amount": 0,
        "Justification": [{"ClauseID": 12, "Text": "Waiting period applies."}],
    }
    normalized = normalize_response(data)
    assert normalized == {
        "Decision": "Rejected",
        "Amount": "0",
        "Justification": [{"ClauseID": "12", "Text": "Waiting period applies."}],
    }


def test_normalize_response_fills_defaults():
    data = {"Decision": "Unknown"}
    normalized = normalize_response(data)
    assert normalized is not None
    assert normalized["Amount"] == "N/A"
    assert normalized["Justification"] == []


def test_chunk_text_overlap():
    text = "abcdefghijklmnopqrstuvwxyz"
    chunks = chunk_text(text, chunk_size=10, overlap=3)
    assert chunks == ["abcdefghij", "hijklmnopq", "opqrstuvwx", "vwxyz"]


def test_build_prompt_includes_clause_ids():
    prompt = build_prompt(
        "Is knee surgery covered?",
        [
            {"id": "policy1__1", "text": "Covers inpatient surgery."},
            {"id": "policy1__2", "text": "Excludes pre-existing conditions."},
        ],
    )
    assert "ClauseID: policy1__1" in prompt
    assert "ClauseID: policy1__2" in prompt
