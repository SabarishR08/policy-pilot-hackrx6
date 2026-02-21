# Production Deployment Guide

## Overview

This guide covers deployment strategies for PolicyPilot on various platforms including local servers, Docker, cloud platforms, and production environments.

## Local Deployment (Development)

### Basic Setup
```bash
# Clone repository
git clone https://github.com/yourusername/PolicyPilot-HackRx.git
cd PolicyPilot-HackRx

# Create virtual environment
python -m venv venv
source venv/bin/activate  # On Windows: venv\Scripts\activate

# Install dependencies
pip install -r requirements.txt

# Download models (if not included)
python download_model.py

# Run application
python web_app.py
```

Access at: **http://127.0.0.1:5000**

## Docker Deployment

### Dockerfile
```dockerfile
FROM python:3.11-slim

WORKDIR /app

# Install system dependencies
RUN apt-get update && apt-get install -y \
    build-essential \
    && rm -rf /var/lib/apt/lists/*

# Copy project files
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

COPY . .

# Create directories
RUN mkdir -p models index data cleaned_data

# Expose port
EXPOSE 5000

# Health check
HEALTHCHECK --interval=30s --timeout=10s --start-period=5s --retries=3 \
    CMD python -c "import urllib.request; urllib.request.urlopen('http://localhost:5000').read()"

# Run application
CMD ["python", "web_app.py"]
```

### Docker Compose
```yaml
version: '3.8'

services:
  app:
    build: .
    ports:
      - "5000:5000"
    volumes:
      - ./models:/app/models
      - ./index:/app/index
      - ./data:/app/data
    environment:
      - FLASK_ENV=production
      - PYTHONUNBUFFERED=1
    restart: unless-stopped
```

### Build and Run
```bash
# Build image
docker build -t policypilot:latest .

# Run container
docker run -p 5000:5000 \
  -v $(pwd)/models:/app/models \
  -v $(pwd)/index:/app/index \
  -v $(pwd)/data:/app/data \
  --name policypilot \
  policypilot:latest

# Or use Docker Compose
docker-compose up -d
```

## Cloud Deployment

### AWS (EC2 + Docker)

```bash
# 1. Launch EC2 instance (Ubuntu 22.04, t3.medium minimum)
# 2. Connect to instance
ssh -i your-key.pem ubuntu@your-instance-ip

# 3. Install Docker
curl -fsSL https://get.docker.com -o get-docker.sh
sudo sh get-docker.sh
sudo usermod -aG docker ubuntu

# 4. Clone and deploy
git clone YOUR_REPO
cd PolicyPilot-HackRx
docker-compose up -d

# 5. Configure security group
# - Allow inbound on port 5000 from your IP
# - Allow inbound on port 22 for SSH
```

### Google Cloud Run (Containerized)

```bash
# 1. Build and push to Container Registry
gcloud builds submit --tag gcr.io/YOUR-PROJECT/policypilot

# 2. Deploy to Cloud Run
gcloud run deploy policypilot \
  --image gcr.io/YOUR-PROJECT/policypilot \
  --platform managed \
  --region us-central1 \
  --memory 2Gi \
  --cpu 2 \
  --allow-unauthenticated
```

### Heroku

```bash
# 1. Create Procfile
echo "web: python web_app.py" > Procfile

# 2. Deploy
heroku create policypilot
git push heroku main

# 3. View logs
heroku logs --tail
```

## Production Configuration

### Environment Variables
```bash
# .env.production
FLASK_ENV=production
FLASK_DEBUG=false
PYTHONUNBUFFERED=1

# Optional: Custom model paths
LLM_MODEL_PATH=/path/to/llama-model.gguf
EMBEDDER_MODEL_PATH=all-MiniLM-L6-v2-offline

# Optional: Performance tuning
LLM_N_THREADS=8
LLM_N_GPU_LAYERS=35  # adjust based on GPU available
```

### Web Server Setup (Gunicorn)

```bash
# Install Gunicorn
pip install gunicorn

# Run with production settings
gunicorn \
  --workers 4 \
  --worker-class sync \
  --bind 0.0.0.0:5000 \
  --timeout 120 \
  --access-logfile - \
  --error-logfile - \
  web_app:app
```

### Nginx Reverse Proxy

```nginx
server {
    listen 80;
    server_name your-domain.com;

    client_max_body_size 100M;

    location / {
        proxy_pass http://127.0.0.1:5000;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
        proxy_set_header X-Forwarded-For $proxy_add_x_forwarded_for;
        proxy_set_header X-Forwarded-Proto $scheme;
        proxy_read_timeout 120s;
        proxy_connect_timeout 120s;
    }
}
```

### SSL/TLS with Let's Encrypt

```bash
# Using Certbot
sudo apt-get install certbot python3-certbot-nginx

# Obtain certificate
sudo certbot certonly --nginx -d your-domain.com

# Add to Nginx config
listen 443 ssl;
ssl_certificate /etc/letsencrypt/live/your-domain.com/fullchain.pem;
ssl_certificate_key /etc/letsencrypt/live/your-domain.com/privkey.pem;
```

## Performance Optimization

### Model Optimization

```python
# web_app.py configuration
PRODUCTION_CONFIG = {
    "n_threads": 8,           # Adjust to CPU count
    "n_gpu_layers": 35,       # For GPU deployment
    "n_ctx": 1024,            # Reduce context if memory constrained
    "n_batch": 512,           # Larger batch for throughput
    "top_k": 3,               # Retrieved chunks
    "temperature": 0.2,       # Lower for consistency
}
```

### Caching Strategy

```python
# Add Flask caching for repeated queries
from flask_caching import Cache

cache = Cache(app, config={'CACHE_TYPE': 'simple'})

@app.route('/query', methods=['POST'])
@cache.cached(timeout=3600, query_string=True)
def query():
    # Query handling with automatic caching
    pass
```

### Load Balancing (Multi-instance)

```yaml
# docker-compose with load balancing
version: '3.8'

services:
  nginx:
    image: nginx:latest
    ports:
      - "80:80"
    volumes:
      - ./nginx.conf:/etc/nginx/nginx.conf
    depends_on:
      - app1
      - app2

  app1:
    build: .
    environment:
      - FLASK_ENV=production

  app2:
    build: .
    environment:
      - FLASK_ENV=production
```

## Monitoring & Logging

### Structured Logging

```python
import logging
from pythonjsonlogger import jsonlogger

# Configure JSON logging for production
logger = logging.getLogger()
handler = logging.StreamHandler()
formatter = jsonlogger.JsonFormatter()
handler.setFormatter(formatter)
logger.addHandler(handler)
```

### Health Checks

```python
# Add health check endpoint
@app.route('/health', methods=['GET'])
def health_check():
    return {
        'status': 'healthy',
        'models_loaded': STATE.get('llm') is not None,
        'index_loaded': STATE.get('index') is not None,
    }, 200
```

### Monitoring Commands

```bash
# Monitor resource usage
top
ps aux | grep python

# Check logs
tail -f app.log | grep ERROR
journalctl -u policypilot -f
```

## Scaling Strategies

### Vertical Scaling (Single Machine)
- Increase CPU cores for LLM inference
- Increase RAM for larger indexes
- Use GPU acceleration (CUDA for nvidia-docker)

### Horizontal Scaling (Multiple Machines)
- Deploy multiple instances behind load balancer
- Share models across instances (NFS mount)
- Use shared cache/database for session management

### Auto-scaling (Cloud)

```bash
# AWS Auto Scaling Group
aws autoscaling create-auto-scaling-group \
  --auto-scaling-group-name policypilot-asg \
  --launch-configuration policypilot-lc \
  --min-size 1 \
  --max-size 5 \
  --desired-capacity 2
```

## Security Hardening

### HTTPS Only
```python
from flask_talisman import Talisman

Talisman(app)  # Enforce HTTPS, set security headers
```

### Rate Limiting
```python
from flask_limiter import Limiter

limiter = Limiter(app, key_func=lambda: request.remote_addr)

@app.route('/query', methods=['POST'])
@limiter.limit("10 per minute")
def query():
    pass
```

### Input Validation
```python
# Validate file uploads
def allowed_file(filename):
    return '.' in filename and \
           filename.rsplit('.', 1)[1].lower() == 'pdf'

# Sanitize inputs
from markupsafe import escape
clean_query = escape(request.form.get('query', ''))
```

### Authentication (Optional)
```python
from flask_httpauth import HTTPBasicAuth

auth = HTTPBasicAuth()

@auth.verify_password
def verify_password(username, password):
    return username == os.getenv('API_USER') and \
           password == os.getenv('API_PASSWORD')

@app.route('/query', methods=['POST'])
@auth.login_required
def query():
    pass
```

## Backup & Recovery

### Data Backup Strategy

```bash
# Backup indexes and data
tar -czf backup_$(date +%Y%m%d).tar.gz \
  index/ data/ cleaned_data/

# Backup to S3
aws s3 cp backup_*.tar.gz s3://your-backup-bucket/

# Schedule with cron
0 2 * * * /path/to/backup-script.sh
```

### Database Recovery

```bash
# Restore from backup
tar -xzf backup_20240101.tar.gz
# Rebuild FAISS index if needed
python chatbot.py --rebuild
```

## Troubleshooting

| Issue | Solution |
|-------|----------|
| Out of Memory | Reduce `n_ctx`, use smaller model, add swap |
| High Latency | Increase `n_threads`, reduce `top_k`, enable GPU |
| Model fails to load | Check model path, verify permissions, enough disk space |
| Index corrupted | Rebuild: `python chatbot.py --rebuild` |
| Port already in use | Kill process or bind to different port |

## Production Checklist

- [ ] All unit tests passing (`pytest tests/ -v`)
- [ ] Integration tests pass (`python test_integration.py`)
- [ ] Environment variables configured
- [ ] HTTPS/SSL configured
- [ ] Health checks operational
- [ ] Logging configured (JSON format)
- [ ] Rate limiting enabled
- [ ] Input validation active
- [ ] Backup strategy in place
- [ ] Monitoring alerts set
- [ ] Documentation updated
- [ ] Load tested under expected traffic

## Getting Help

- Read [README.md](README.md) for overview
- Check [SETUP.md](SETUP.md) for installation issues
- See [EXAMPLES.md](EXAMPLES.md) for usage patterns
- Report issues on GitHub
