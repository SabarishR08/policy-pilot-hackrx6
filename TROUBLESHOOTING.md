# Troubleshooting Guide

## Installation Issues

### Issue: `ModuleNotFoundError: No module named 'xxx'`

**Solution:**
```bash
# Reinstall all dependencies
pip install --upgrade --force-reinstall -r requirements.txt

# Or install individually
pip install faiss-cpu flask jsonschema llama-cpp-python numpy PyPDF2 pytest sentence-transformers
```

**Note:** On Windows, `llama-cpp-python` requires Visual C++ build tools. See [SETUP.md](SETUP.md#windows-specific) for details.

### Issue: `pip install` takes 30+ minutes (especially `llama-cpp-python`)

**Solution - Use prebuilt wheels:**
```bash
# Option 1: Use conda (faster, pre-compiled)
conda install -c conda-forge llama-cpp-python

# Option 2: Install pre-built wheel
pip install llama-cpp-python==0.2.74 --no-build-isolation

# Option 3: Skip local LLM, use API (temporary workaround)
# Modify chatbot.py to use remote API
```

### Issue: `RuntimeError: CUDA not available` (GPU support)

**Solution:**
```bash
# For NVIDIA GPU support
pip install llama-cpp-python[cuda] --no-cache-dir

# Or use conda
conda install -c conda-forge llama-cpp-python-cuda
```

---

## Model Loading Issues

### Issue: `FileNotFoundError: Model not found at default location`

**Solution:**

1. Check model location:
```bash
# Verify embedding model exists
ls -la all-MiniLM-L6-v2-offline/
# Should contain: config.json, tokenizer.json, model.safetensors, etc.

# Verify LLM model exists
ls -la models/
# Should contain: tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf (638 MB)
```

2. Download models if missing:
```bash
# Download embedding model
python -c "from sentence_transformers import SentenceTransformer; \
SentenceTransformer('all-MiniLM-L6-v2-offline')"

# Download LLM model
python download_model.py
```

3. Specify custom paths:
```bash
# CLI
python chatbot.py --query "?" --embedding-model /custom/path --model-path /custom/model.gguf

# Web UI (form field)
# Paste absolute path in "model_path" field
```

### Issue: `OSError: libomp.dll not found` (macOS/OpenMP)

**Solution:**
```bash
# macOS
brew install libomp

# Linux Ubuntu
sudo apt-get install libomp-dev

# Windows (Visual C++ already includes this)
# Reinstall Visual C++ Build Tools
```

### Issue: Model loads but takes 40+ seconds

**Solution:**
```bash
# This is normal for first load. To verify:
import time
from sentence_transformers import SentenceTransformer
start = time.time()
model = SentenceTransformer('all-MiniLM-L6-v2-offline')
print(f"Load time: {time.time() - start:.1f}s")
# Expect: 20-40 seconds first time, <1s on subsequent runs
```

---

## Index Building Issues

### Issue: `FileNotFoundError: No PDF files found in data/`

**Solution:**
1. Upload PDFs via web UI: http://127.0.0.1:5000 → "Upload PDF"
2. Or copy PDFs manually:
```bash
cp /path/to/*.pdf data/
```
3. If using cleaned data:
```bash
cp /path/to/cleaned/*.pdf cleaned_data/
python chatbot.py --rebuild --use-cleaned
```

### Issue: `MemoryError: Unable to allocate X GiB for index`

**Solution (reduce index size):**
```bash
# Smaller chunks = fewer embeddings
python chatbot.py --rebuild --chunk-size 500 --overlap 50

# Or delete some PDFs
rm data/large_document.pdf
python chatbot.py --rebuild
```

**Solution (add virtual memory):**
```bash
# Linux
sudo fallocate -l 4G /swapfile
sudo chmod 600 /swapfile
sudo mkswap /swapfile
sudo swapon /swapfile

# Windows: Settings → System → Storage → Change virtual memory
# macOS: Increase available disk space
```

### Issue: Index build completes but shows 0 chunks

**Solution:**
```bash
# Check PDFs are readable
python -c "
import PyPDF2
with open('data/policy.pdf', 'rb') as f:
    reader = PyPDF2.PdfReader(f)
    print(f'Pages: {len(reader.pages)}')
    print(f'First page text: {reader.pages[0].extract_text()[:100]}')
"

# If PDFs are image-based, convert to text first:
# Use online tool: https://www.ilovepdf.com/extract-pdf-text
```

---

## Query Issues

### Issue: Empty or "Unknown" responses

**Solution:**

1. **Rebuild index:**
```bash
python web_app.py
# Then click "Build Index" in web UI
```

2. **Verify PDFs were indexed:**
```bash
ls -la index/
# Should show: faiss.index, embeddings.npy, etc.
```

3. **Check index contents:**
```bash
python -c "
import numpy as np
emb = np.load('index/embeddings.npy')
print(f'Chunks indexed: {emb.shape[0]}')  # Should be > 0
"
```

4. **Increase context retrieval:**
```bash
# Web UI: Change "Top K" from 3 to 5-7
# CLI: python chatbot.py --query "?" --top-k 7
```

### Issue: Slow responses (30+ seconds per query)

**Causes & Solutions:**

| Cause | Solution |
|-------|----------|
| Large context window (`n_ctx`) | Reduce from 2048 to 1024 |
| High max_tokens | Reduce from 256 to 128 |
| Single-threaded inference | Increase `n_threads` to CPU count |
| Disk I/O (models loading) | Use SSD, not spinning disk |
| CPU thermal throttling | Stop other apps, let CPU cool |

**Benchmark script:**
```bash
python -c "
import time, json
from chatbot import *

embedder = SentenceTransformer('all-MiniLM-L6-v2-offline')
index, chunks, _ = load_index()
llm = Llama(model_path='models/tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf', n_ctx=1024, n_threads=8)

query = 'Is knee surgery covered?'
start = time.time()
context = retrieve_chunks(query, embedder, index, chunks, 3)
t1 = time.time() - start
prompt = build_prompt(query, context)
start = time.time()
answer = run_llm(llm, prompt, 128, 0.2)
t2 = time.time() - start
print(f'Retrieval: {t1:.2f}s, LLM: {t2:.2f}s, Total: {t1+t2:.2f}s')
"
```

### Issue: Irrelevant or hallucinated responses

**Solution:**

1. **Reduce hallucination:**
```bash
# Lower temperature (less creative)
# Web UI: Set temperature to 0.1 (default 0.2)
# CLI: python chatbot.py --query "?" --temperature 0.1
```

2. **Increase context:**
```bash
# More chunks to ground answer
# Web UI: Increase "Top K" to 5-7
# CLI: python chatbot.py --query "?" --top-k 7
```

3. **Improve prompt:**
```bash
# Edit prompt_template in chatbot.py to be more specific
# E.g., start with: "Based ONLY on the following policy clauses, answer..."
```

---

## Web UI Issues

### Issue: Flask error: `Address already in use`

**Solution:**
```bash
# Option 1: Find and kill process using port 5000
# Windows PowerShell
Get-Process | Where-Object {$_.Handles -like "*5000*"}
Stop-Process -Id <PID> -Force

# macOS/Linux
lsof -i :5000
kill -9 <PID>

# Option 2: Use different port
python web_app.py 5001  # Edit web_app.py to change port
```

### Issue: Page takes 30+ seconds to load after query

**Solution:**
1. This is **normal** for the first query (models loading)
2. Subsequent queries should be 5-15 seconds (LLM inference time)
3. To verify models are loading:
```bash
# Check browser console (F12 → Console)
# Should see logs of model loading
```

### Issue: `/upload` route hangs or fails

**Solution:**
```bash
# Increase max upload size (edit web_app.py)
APP.config["MAX_CONTENT_LENGTH"] = 100 * 1024 * 1024  # 100 MB

# Or check file permissions
ls -la data/
# Should be writable by your user
```

### Issue: JSON response is malformed

**Solution:**
```bash
# Check raw response in browser developer console (F12)
# Should be valid JSON in textarea

# If invalid, check chatbot.py normalize_response()
python -c "
from chatbot import normalize_response
test = {'Decision': 'Covered'}
result = normalize_response(test)
print(result)
"
```

---

## Performance Optimization

### Low Performance on CPU

**Recommended settings for CPU:**
```bash
# Smaller models, smaller context
python chatbot.py \
  --query "?" \
  --n-ctx 1024 \           # Not 2048
  --n-threads 8 \          # Match CPU cores
  --max-tokens 128 \       # Not 256
  --top-k 3                # Default is fine
```

### High Memory Usage

**Monitor with system tools:**
```bash
# Real-time monitoring
watch -n 1 'free -h; ps aux | grep python'  # Linux
df -h  # Disk space
du -sh *  # Directory sizes
```

**Reduce memory footprint:**
```bash
# Option 1: Smaller chunk size
python chatbot.py --rebuild --chunk-size 500

# Option 2: Remove large PDFs temporarily
mv data/large.pdf data_backup/

# Option 3: Use GPU
# Requires CUDA-enabled GPU and proper llama-cpp-python build
```

---

## Testing Issues

### Issue: `pytest` reports import errors

**Solution:**
```bash
# Ensure PYTHONPATH includes project directory
export PYTHONPATH="${PYTHONPATH}:$(pwd)"  # macOS/Linux
set PYTHONPATH=%cd%::%PYTHONPATH%        # Windows

# Or run from project directory
cd /path/to/PolicyPilot-HackRx
pytest tests/ -v
```

### Issue: Test hangs or times out

**Solution:**
```bash
# Run with timeout
pytest tests/ --timeout=60  # 60 second timeout per test

# Run specific test
pytest tests/test_chatbot.py::test_chunk_text -v
```

### Issue: Model tests fail in CI/CD

**Solution (GitHub Actions):**
```yaml
# Add to .github/workflows/tests.yml
- name: Download models
  run: python download_model.py
  
- name: Run tests
  timeout-minutes: 10
  run: pytest tests/ -v
```

---

## System Errors

### Issue: `segmentation fault` (crash without error)

**Usually caused by:** Out of memory, incompatible CUDA version

**Solution:**
```bash
# Check available memory
free -h  # Linux
Get-ComputerInfo -Property TotalPhysicalMemory  # Windows

# Increase swap if needed
# See "MemoryError" section above

# Or if GPU related:
nvidia-smi  # Check CUDA availability
# Reinstall llama-cpp-python without GPU support
pip install llama-cpp-python --force-reinstall --no-cache-dir
```

### Issue: `libomp.dll not found` (Windows)

**Solution:**
```bash
# Reinstall Visual C++ Build Tools
# Download from: https://visualstudio.microsoft.com/visual-cpp-build-tools/
# Or use conda (includes OpenMP)
conda install -c conda-forge llama-cpp-python
```

---

## Getting More Help

| Resource | Use When |
|----------|----------|
| [README.md](README.md) | Overview, quick start |
| [SETUP.md](SETUP.md) | Installation issues |
| [EXAMPLES.md](EXAMPLES.md) | Usage questions |
| [API.md](API.md) | API/integration questions |
| [DEPLOYMENT.md](DEPLOYMENT.md) | Production setup |
| GitHub Issues | Bug reports, feature requests |

**Report a bug:**
```bash
# Include this information
uname -a           # System info
pip list           # Installed packages
python --version   # Python version
# Your commands and error output
```

---

## Quick Reference

```bash
# Check everything is working
python test_integration.py

# Run minimal test
python -c "from sentence_transformers import SentenceTransformer; print('OK')"

# Clear cache and rebuild
rm -rf index/
python chatbot.py --rebuild

# Quick performance test
time python chatbot.py --query "test"

# Check disk usage
du -sh . --ignore=venv

# Update environment
pip install --upgrade -r requirements.txt
```

Good luck! For persistent issues, create an issue on GitHub.
