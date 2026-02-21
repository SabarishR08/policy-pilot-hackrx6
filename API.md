# API Documentation

## REST Endpoints

All endpoints interact with the web UI through Form Data (application/x-www-form-urlencoded).

### GET /

Home page with web interface.

**Response:** HTML form for queries

---

### POST /upload

Upload a PDF document to the system.

**Form Parameters:**
- `pdf` (file, required): PDF file (max 25 MB)

**Response:**
- Success: Redirects to home page with status message
- Error: Shows error message on home page

**Example:**
```bash
curl -X POST -F "pdf=@policy.pdf" http://127.0.0.1:5000/upload
```

---

### POST /build

Build FAISS index from uploaded PDF documents.

**Form Parameters:**
- `use_cleaned` (optional): If present, use cleaned_data/; otherwise data/
- `chunk_size` (integer, default: 1000): Characters per chunk
- `overlap` (integer, default: 150): Overlap between chunks

**Response:**
- Redirects to home page with updated index status
- Shows: "Index rebuilt from documents (X chunks)."

**Example:**
```bash
curl -X POST \
  -d "chunk_size=1200&overlap=200" \
  http://127.0.0.1:5000/build
```

---

### POST /query

Query the policy documents and get LLM response.

**Form Parameters:**

*Required:*
- `query` (string): User's question

*Optional:*
- `use_cleaned` (optional): Use cleaned data for indexing
- `chunk_size` (integer, default: 1000): Chunk size for indexing
- `overlap` (integer, default: 150): Chunk overlap
- `top_k` (integer, default: 3): Number of clauses to retrieve
- `max_tokens` (integer, default: 256): Response length limit
- `temperature` (float, default: 0.2): LLM creativity (0.0-1.0)
- `n_ctx` (integer, default: 2048): Context window size
- `n_threads` (integer, default: 4): CPU threads for inference
- `model_path` (string): Path to GGUF model (optional override)

**Response:**
- Success: Rendered HTML showing JSON response
- Error: Shows error message on page

**Response Format:**
```json
{
  "Decision": "Covered|Not Covered|Partially Covered|Unknown",
  "Amount": "5000|N/A|Variable",
  "Justification": [
    {
      "ClauseID": "FILENAME.pdf__CHUNK_ID",
      "Text": "Relevant clause text from policy..."
    }
  ]
}
```

**Example:**
```bash
curl -X POST \
  -d "query=Is%20knee%20surgery%20covered?" \
  -d "top_k=3" \
  -d "max_tokens=256" \
  -d "temperature=0.2" \
  http://127.0.0.1:5000/query
```

---

## Response Schema

### Standard Response
```json
{
  "Decision": "string",
  "Amount": "string",
  "Justification": [
    {
      "ClauseID": "string",
      "Text": "string"
    }
  ]
}
```

### Valid Decision Values
- `"Covered"` - Service is covered under policy
- `"Not Covered"` - Service is not covered
- `"Partially Covered"` - Coverage limitations apply
- `"Unknown"` - Cannot determine coverage

### Valid Amount Values
- Numeric string: `"5000"`, `"25000"`, etc.
- Variable: `"Variable"`, `"N/A"`, `"Depends on plan"`
- Infinity indicator: `"Unlimited"`

---

## Error Codes

| HTTP Code | Scenario | Message |
|-----------|----------|---------|
| 200 | Success | JSON response or HTML page |
| 400 | Invalid input | "No file selected", "Enter a query." |
| 413 | File too large | Automatic (max 25 MB) |
| 500 | Server error | "Internal server error" |

---

## Python Client Example

```python
import requests
import json

BASE_URL = "http://127.0.0.1:5000"

# Upload PDF
with open("policy.pdf", "rb") as f:
    files = {"pdf": f}
    resp = requests.post(f"{BASE_URL}/upload", files=files)
    print(f"Upload status: {resp.status_code}")

# Build index
resp = requests.post(f"{BASE_URL}/build", data={"chunk_size": 1000})
print(f"Build status: {resp.status_code}")

# Query
payload = {
    "query": "Is knee surgery covered?",
    "top_k": 3,
    "max_tokens": 256,
    "temperature": 0.2
}
resp = requests.post(f"{BASE_URL}/query", data=payload)

# Extract JSON from response HTML (simplified)
print(resp.text)  # Contains HTML with JSON answer
```

---

## CLI Usage

For command-line queries without the web UI:

```bash
# Simple query
python chatbot.py --query "Your question"

# Interactive mode (multiple queries)
python chatbot.py

# Advanced options
python chatbot.py --query "Your question" \
  --top-k 5 \
  --max-tokens 300 \
  --temperature 0.5 \
  --n-threads 8

# Rebuild index
python chatbot.py --rebuild --chunk-size 1200 --overlap 200

# Use alternative LLM
python chatbot.py --model-path models/alternative.gguf --query "Question"
```

---

## Performance Parameters

### Retrieval Parameters
- `top_k`: 1-10 (higher = more context, slower)
- Recommended: 3-5 for balanced accuracy

### Generation Parameters
- `max_tokens`: 50-512 (higher = longer responses, slower)
- `temperature`: 0.0-1.0 (0=deterministic, 1=creative)
- Recommended: 0.1-0.3 for policy queries

### Model Parameters
- `n_ctx`: 512-4096 (larger = more context, more memory)
- `n_threads`: 1-CPU_COUNT (more = faster, uses more CPU)
- Recommended: n_threads = CPU_COUNT - 1

### Indexing Parameters
- `chunk_size`: 300-2000 (balance coverage vs specificity)
- `overlap`: 50-300 (prevents cutting mid-sentence)
- Recommended: chunk_size=1000, overlap=150

---

## Rate Limiting (Production)

Consider adding rate limiting for production deployment:

```python
from flask_limiter import Limiter

limiter = Limiter(app, key_func=lambda: request.remote_addr)

@app.route('/query', methods=['POST'])
@limiter.limit("10 per minute")
def query():
    pass
```

---

## CORS Headers (For Frontend)

If embedding in web application, add CORS support:

```python
from flask_cors import CORS
CORS(app)
```

---

## Health Check

Check if service is operational:

```bash
curl http://127.0.0.1:5000/
```

Returns:
- 200 OK: Service is running
- 500 error: Models not loaded or critical failure

---

## Troubleshooting

### 502 Bad Gateway / Timeout
- Increase LLM context: add `--n-ctx 1024`
- Reduce max_tokens: 128 instead of 256
- Check CPU usage: `top` or Task Manager

### Empty Response
- Rebuild index: go to /build
- Verify PDFs in data/ folder
- Try with higher `top_k`: 5 instead of 3

### Out Of Memory
- Reduce `n_ctx`: 1024 instead of 2048
- Use GPU: set `n_gpu_layers` (requires llama-cpp-python with CUDA)
- Deploy on machine with more RAM

### Model Not Loading
- Verify model file exists and is readable
- Check model path is absolute or relative to working directory
- Ensure sufficient disk space

For more help, see [SETUP.md](SETUP.md) or [EXAMPLES.md](EXAMPLES.md)
