# PolicyPilot: Offline Insurance Policy Query System

[![Python](https://img.shields.io/badge/Python-3.10%2B-blue)](https://www.python.org/downloads/)
[![License](https://img.shields.io/badge/License-MIT-green)](LICENSE)

A local-only system for querying insurance policy documents using semantic search and language models. Processes PDF documents, creates searchable indexes, and retrieves relevant clauses with LLM-generated responses.

## Overview

PolicyPilot enables users to ask questions about insurance policies stored as PDFs. The system extracts relevant policy clauses using vector similarity search and generates responses using a local language model. All processing occurs on-device with no external API calls.

## Technical Stack

- **Text Embedding**: all-MiniLM-L6-v2 (384-dimensional vectors, 22 MB)
- **Vector Search**: FAISS with inner-product similarity
- **Language Model**: TinyLlama 1.1B (quantized GGUF, 638 MB)
- **PDF Processing**: PyPDF2 for text extraction
- **Web Interface**: Flask
- **CLI Interface**: argparse
- **Testing**: pytest (5 unit tests)

## How It Works

1. **Indexing**: PDF documents are split into chunks, converted to embeddings, and indexed in FAISS
2. **Query**: User query is converted to embedding and similar chunks are retrieved
3. **Generation**: Retrieved chunks provide context for a local LLM to generate responses
4. **Output**: Structured JSON response with decision, amount, and clause references

Typical query latency: 5-15 seconds (1-2 seconds retrieval, 4-13 seconds LLM inference)

## Requirements

- Python 3.10+
- 8+ GB RAM
- 2+ GB disk space
- CPU with 4+ cores recommended

## System Architecture
User Query
  -> Embedding Model
  -> Vector Search (FAISS)
  -> Relevant Clauses
  -> Local LLM (TinyLlama)
  -> Structured JSON Answer

## Core Technologies Used
- Python: main programming language
- FAISS: fast vector similarity search
- Sentence Transformers: text embeddings
- PyPDF2: PDF text extraction
- TinyLlama GGUF: local LLM inference
- llama-cpp-python: runs the model locally

## Folder Structure
Create this manually:

project/
|
|-- chatbot.py
|-- requirements.txt
|-- data/
|   |-- policy1.pdf
|   |-- policy2.pdf
|   `-- ...
|-- models/
|   `-- tinyllama.gguf
|-- index/   (auto created)
`-- README.md

## Step-by-Step Setup

### Step 1 - Install Python
Install Python 3.10 or later.

Check:
python --version

### Step 2 - Create Virtual Environment
python -m venv venv

Activate:

Windows:
venv\Scripts\activate

Linux or Mac:
source venv/bin/activate

### Step 3 - Install Dependencies
pip install PyPDF2 sentence-transformers faiss-cpu numpy llama-cpp-python

### Step 4 - Download TinyLlama Model
Download a .gguf quantized file (Q4 or Q5 recommended).

Place it inside:
models/

Example:
models/tinyllama-1.1b-chat.Q4.gguf

### Step 5 - Add PDFs
Put your policy documents inside:
data/

### Step 6 - Add Script File
Create:
chatbot.py

Paste the script you already have.

### Step 7 - Run Project
Basic interactive mode:
python chatbot.py

Single query:
python chatbot.py --query "Is knee surgery covered?"

Rebuild the index:
python chatbot.py --rebuild

Web UI:
python web_app.py
Open http://127.0.0.1:5000 in your browser.

## Example Queries
- Is knee surgery covered?
- What is the waiting period for maternity?
- Are ambulance charges reimbursed?

## Testing
Install dependencies, then run:
pytest

## What Happens When Script Runs

### Phase 1 - Text Extraction
Reads all PDFs and extracts text page-by-page.

### Phase 2 - Chunking
Splits long text into smaller chunks (about 1000 characters).

Why:
Embedding models work best on shorter semantic sections.

### Phase 3 - Embedding Creation
Each chunk is converted into a vector using:
all-MiniLM-L6-v2

Vectors represent meaning numerically.

### Phase 4 - Vector Database
Vectors are stored in a FAISS index for fast search.

Saved files:
- index/faiss.index
- index/chunks.pkl

Next runs load these instantly.

### Phase 5 - Model Loading
TinyLlama loads locally. No internet needed.

### Phase 6 - Query Processing
User types:
Is knee surgery covered?

System:
- Converts query to an embedding
- Searches similar clauses
- Selects top matches
- Sends them to the LLM as context

### Phase 7 - LLM Reasoning
Model receives context plus question and generates structured output:
{
  decision: approved or rejected,
  amount: value,
  justification: clauses
}

## Output Format
Example response:
{
  "Decision": "Rejected",
  "Amount": "N/A",
  "Justification": [
    {
      "ClauseID": "policy2__143",
      "Text": "Treatment excluded during waiting period."
    }
  ]
}

## Key Design Advantages
- Works offline
- Runs on low-RAM laptops
- Uses semantic understanding
- Provides clause citations
- Returns machine-readable JSON

## Performance Optimization Tips
If slow:
- Reduce chunk size
- Reduce top_k results
- Use Q4 model instead of Q8

If you hit context errors:
- Lower MAX_GEN_TOKENS
- Reduce retrieved clauses

## Hardware Requirements
Minimum:
- 8GB RAM
- CPU only

Recommended:
- 12GB RAM
- SSD storage

## Running in Google Colab (Alternative)
If local install fails:
- Upload PDFs
- Upload model
- Run the script in a notebook

Colab handles dependencies automatically.

## How to Upload to GitHub
Initialize repo:
git init
git add .
git commit -m "initial"

Push:
git remote add origin YOUR_REPO_URL
git push -u origin main

Do NOT upload:
- models/
- index/

Add them to .gitignore.

## Possible Future Improvements
You can extend this project with:
- Web UI interface
- Upload documents dynamically
- Speech input
- Highlighted clause viewer
- Confidence score
- Streaming responses

## Real-World Use Cases
This architecture can power:
- Legal document assistants
- Policy analysis tools
- Contract review AI
- Research assistants
- Compliance checking bots

## Final Explanation (Simple Words)
You built a system that reads documents, understands them, finds relevant parts, and answers questions intelligently. It is a mini ChatGPT trained on your documents only.
