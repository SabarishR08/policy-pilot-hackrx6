# Installation & Setup Guide

## Prerequisites

- **Python**: 3.10 or higher
- **RAM**: 12GB minimum (8GB with optimizations)
- **Disk**: 1.5GB for models and dependencies
- **OS**: Windows, macOS, Linux

## Option 1: Quick Start (Recommended)

### 1. Clone Repository
```bash
git clone https://github.com/username/PolicyPilot.git
cd PolicyPilot
```

### 2. Create Virtual Environment
```bash
# Windows
python -m venv venv
venv\Scripts\activate

# macOS/Linux
python3 -m venv venv
source venv/bin/activate
```

### 3. Install Dependencies
```bash
pip install -r requirements.txt
```

### 4. Verify Installation
```bash
python test_integration.py
```

Expected output:
```
✓ Found 5 PDF(s) in data/
✓ Embedding model found: all-MiniLM-L6-v2-offline
✓ LLM model found: tinyllama-1.1b-chat-v1.0.Q4_K_M.gguf
✓ FAISS index already built

All checks passed! ✓
```

## Option 2: From Source with Development Tools

### 1. Clone & Navigate
```bash
git clone https://github.com/username/PolicyPilot.git
cd PolicyPilot
```

### 2. Create Virtual Environment
```bash
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate
```

### 3. Install in Development Mode
```bash
pip install -e ".[dev]"
```

### 4. Run Tests
```bash
pytest tests/ -v
```

## Platform-Specific Notes

### Windows
- May require Visual C++ Build Tools for `llama-cpp-python`
  - Download: https://visualstudio.microsoft.com/visual-cpp-build-tools/
  - Select: Desktop development with C++

### macOS
- Arm64 (Apple Silicon): Ensure Python is arm64 native
  ```bash
  python -c "import platform; print(platform.machine())"  # Should output: arm64
  ```
- Intel Mac: Works with standard installation

### Linux
- Debian/Ubuntu:
  ```bash
  sudo apt-get update
  sudo apt-get install python3.10 python3.10-venv build-essential
  ```
- RHEL/CentOS:
  ```bash
  sudo yum install python310 python310-devel
  ```

## Troubleshooting

### Issue: `ModuleNotFoundError: No module named 'llama_cpp'`
**Solution:**
```bash
pip install --upgrade llama-cpp-python
```

### Issue: `FileNotFoundError: Index not found`
**Solution:**
Build the index from PDFs:
```bash
python chatbot.py --rebuild
```

### Issue: Out of Memory
**Solution:**
Reduce context size:
```bash
python chatbot.py --n-ctx 1024 --query "your question"
```

### Issue: Slow Performance
**Solution:**
Use Q4 quantization (already default) and increase n_threads:
```bash
python chatbot.py --n-threads 8 --query "your question"
```

## Verifying the Installation

### Check All Components
```bash
python test_integration.py
```

### Run Quick Test
```bash
python chatbot.py --query "Is knee surgery covered?" --max-tokens 100
```

### Launch Web UI
```bash
python web_app.py
# Open http://127.0.0.1:5000
```

## Updating

### Pull Latest Changes
```bash
git pull origin main
```

### Update Dependencies
```bash
pip install -r requirements.txt --upgrade
```

### Rebuild Models (if needed)
```bash
python chatbot.py --rebuild
```

## Uninstalling

### Remove Everything
```bash
# Deactivate virtual environment
deactivate

# Remove venv folder
rm -rf venv  # or rmdir venv on Windows

# Remove project directory
cd ..
rm -rf PolicyPilot
```

## Docker Setup (Optional)

### Build Docker Image
```bash
docker build -t policy-pilot .
```

### Run Container
```bash
docker run -p 5000:5000 policy-pilot
```

## Next Steps

1. **Run CLI Tutorial**: `python chatbot.py`
2. **Launch Web UI**: `python web_app.py`
3. **Read Documentation**: See [README.md](README.md)
4. **Check Examples**: See [EXAMPLES.md](EXAMPLES.md)
5. **Contribute**: See [CONTRIBUTING.md](CONTRIBUTING.md)

## Getting Help

- **Documentation**: Check [README.md](README.md)
- **Issues**: Report on [GitHub Issues](https://github.com/username/PolicyPilot/issues)
- **Discussions**: Join [GitHub Discussions](https://github.com/username/PolicyPilot/discussions)

## System Requirements

| Component | Minimum | Recommended |
|-----------|---------|-------------|
| RAM | 8GB | 12GB+ |
| CPU Cores | 2 | 4+ |
| Disk (free) | 1.5GB | 3GB+ |
| Python | 3.10 | 3.11+ |

## Performance Tips

1. **First Run**: Expected to take 2-3 minutes (model loading)
2. **Subsequent Runs**: ~5-30 seconds depending on query complexity
3. **Multi-threading**: Use `--n-threads 8` for 8-core CPU
4. **Memory**: Monitor with `htop` (Linux/Mac) or Task Manager (Windows)
