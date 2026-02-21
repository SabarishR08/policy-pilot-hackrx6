# Usage Examples

## CLI Mode

### Basic Query
```bash
python chatbot.py --query "Is knee surgery covered?"
```

Output:
```json
{
  "Decision": "Covered",
  "Amount": "N/A",
  "Justification": [
    {
      "ClauseID": "BAJHLIP23020V012223.pdf__45",
      "Text": "Arthroscopic procedures covered under standard plan..."
    }
  ]
}
```

### Interactive Mode
```bash
python chatbot.py
```

Then type your queries:
```
Query: What is the waiting period for maternity?
Query: Are ambulance charges reimbursed?
Query: exit
```

### Advanced Options

#### Control Model Parameters
```bash
# Increase temperature for more creative responses
python chatbot.py --query "Your question" --temperature 0.7

# Limit output length
python chatbot.py --query "Your question" --max-tokens 100

# Retrieve more context chunks
python chatbot.py --query "Your question" --top-k 5
```

#### Optimize for Performance
```bash
# Use more CPU threads
python chatbot.py --query "Your question" --n-threads 8

# Reduce context window for faster inference
python chatbot.py --query "Your question" --n-ctx 1024
```

#### Customize Indexing
```bash
# Rebuild index with larger chunks
python chatbot.py --rebuild --chunk-size 1500

# Use cleaned data if available
python chatbot.py --rebuild --use-cleaned

# Rebuild with custom overlap
python chatbot.py --rebuild --chunk-size 1000 --overlap 200
```

#### Use Custom LLM Model
```bash
# Specify alternative GGUF model
python chatbot.py --model-path models/your-model.gguf --query "Your question"
```

## Web UI Mode

### Start Server
```bash
python web_app.py
```

Then open **http://127.0.0.1:5000** in your browser.

### Using Web Interface

1. **Upload PDF**
   - Click "Upload PDF" button
   - Select a .pdf file
   - Wait for confirmation

2. **Build Index**
   - Click "Build Index" after uploading PDFs
   - Adjust chunking parameters if needed
   - Wait for completion

3. **Ask Questions**
   - Enter query in text area
   - Adjust LLM parameters (optional):
     - Top K: Number of clauses to retrieve (default: 3)
     - Max Tokens: Response length limit (default: 256)
     - Temperature: Creativity level (default: 0.2)
   - Click "Run Query"

4. **View Results**
   - JSON response with Decision, Amount, and Clause citations
   - Copy response for integration

## Python API Usage

### Basic Function Calls

```python
from chatbot import (
    retrieve_chunks, 
    build_prompt, 
    run_llm, 
    normalize_response,
    load_index
)
from sentence_transformers import SentenceTransformer
from llama_cpp import Llama

# Load components
embedder = SentenceTransformer("all-MiniLM-L6-v2-offline")
index, chunks, _ = load_index()
llm = Llama(model_path="models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf")

# Retrieve relevant chunks
query = "Is knee surgery covered?"
context = retrieve_chunks(query, embedder, index, chunks, top_k=3)

# Build prompt and get response
prompt = build_prompt(query, context)
answer = run_llm(llm, prompt, max_tokens=256, temperature=0.2)
normalized = normalize_response(answer)

print(json.dumps(normalized, indent=2))
```

### Custom Query Pipeline

```python
from chatbot import normalize_response, extract_json
import json

# Custom processing
def my_query_handler(user_input: str) -> dict:
    # Your preprocessing
    processed = user_input.lower().strip()
    
    # Your LLM logic
    llm_output = llm(processed, max_tokens=100)
    raw_text = llm_output["choices"][0]["text"]
    
    # Extract and validate
    parsed = extract_json(raw_text)
    result = normalize_response(parsed)
    
    return result or {"Decision": "Unknown", "Amount": "N/A", "Justification": []}

# Use it
response = my_query_handler("Your question here")
print(json.dumps(response, indent=2))
```

### Batch Processing

```python
from chatbot import retrieve_chunks, build_prompt, run_llm, normalize_response
import json

queries = [
    "Is knee surgery covered?",
    "What are waiting periods?",
    "Are ambulance charges reimbursed?"
]

results = []
for query in queries:
    context = retrieve_chunks(query, embedder, index, chunks, top_k=3)
    prompt = build_prompt(query, context)
    answer = run_llm(llm, prompt, max_tokens=256, temperature=0.2)
    normalized = normalize_response(answer)
    
    results.append({
        "query": query,
        "response": normalized
    })

# Save results
with open("results.json", "w") as f:
    json.dump(results, f, indent=2)
```

## Testing & Validation

### Run Unit Tests
```bash
pytest tests/test_chatbot.py -v
```

### Run Integration Tests
```bash
python test_integration.py
```

### Manual Testing

```bash
# Test JSON validation
python -c "
from chatbot import normalize_response
test = {'Decision': 'Approved', 'Amount': '5000', 'Justification': []}
result = normalize_response(test)
print('Test:', 'PASS' if result else 'FAIL')
"

# Test chunking
python -c "
from chatbot import chunk_text
text = 'This is a long document. ' * 100
chunks = chunk_text(text, chunk_size=100, overlap=20)
print(f'Created {len(chunks)} chunks')
"

# Test embeddings
python -c "
from sentence_transformers import SentenceTransformer
model = SentenceTransformer('all-MiniLM-L6-v2-offline')
vec = model.encode('test')
print(f'Embedding dimension: {vec.shape[0]}')
"
```

## Troubleshooting

### High Latency
```bash
# Reduce context window
python chatbot.py --n-ctx 1024 --query "Your question"

# Reduce tokens generated
python chatbot.py --max-tokens 100 --query "Your question"

# Reduce retrieved chunks
python chatbot.py --top-k 2 --query "Your question"
```

### Memory Issues
```bash
# Check available memory
python -c "
import psutil
mem = psutil.virtual_memory()
print(f'Available: {mem.available / (1024**3):.1f} GB')
"

# Rebuild with smaller chunks
python chatbot.py --rebuild --chunk-size 500
```

### No Results Found
```bash
# Rebuild index from scratch
python chatbot.py --rebuild

# Verify PDFs are in data folder
ls data/

# Check index files exist
ls index/
```

## Example Queries

### Coverage Questions
- "Is knee surgery covered?"
- "Are dental treatments reimbursed?"
- "Is COVID-19 treatment covered under the policy?"

### Waiting Period Questions
- "What is the waiting period for new members?"
- "How long before maternity benefits apply?"
- "Is there a waiting period for pre-existing conditions?"

### Amount & Limits Questions
- "What is the maximum claim amount?"
- "Are there daily limits for hospitalization?"
- "What is the deductible?"

### Claim Questions
- "What documents are required for claims?"
- "How long does claim processing take?"
- "Can I claim multiple times per year?"

## Performance Benchmarks

| Operation | Time (First Run) | Time (Cached) |
|-----------|---|---|
| Model Loading | ~30-40s | ~30s |
| Query Embedding | ~0.1s | ~0.1s |
| Chunk Retrieval | ~0.05s | ~0.05s |
| LLM Inference | ~5-15s | ~5-15s |
| **Total** | ~40-70s | ~40-70s |

## Next Steps

- Read [README.md](README.md) for overview
- Review [SETUP.md](SETUP.md) for installation
- Check [CONTRIBUTING.md](CONTRIBUTING.md) to contribute
- Report issues on GitHub

## Questions?

- Create an issue on GitHub
- Join discussions
- Check documentation
