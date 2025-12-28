# Deployment Guide

## Quick Start (Self-Hosted)

### Prerequisites
- Docker & Docker Compose
- OpenRouter API key (get one at [openrouter.ai](https://openrouter.ai))

### 5-Minute Setup

1. **Clone and configure:**
```bash
git clone https://github.com/ventoetc/LLM-cost-optimization.git
cd LLM-cost-optimization

# Copy environment template
cp backend/.env.example backend/.env

# Edit .env and add your OpenRouter API key
nano backend/.env
```

2. **Start the stack:**
```bash
docker-compose up -d
```

3. **Verify it's running:**
```bash
curl http://localhost:8000/health
# Should return: {"status": "healthy"}
```

4. **Make your first request:**
```bash
curl -X POST http://localhost:8000/api/v1/query \
  -H "Content-Type: application/json" \
  -d '{
    "prompt": "Explain quantum computing to a 10 year old",
    "user_id": "test-user"
  }'
```

That's it! The system will:
- Analyze your prompt
- Decompose if needed
- Route to optimal models
- Cross-check responses
- Return verified answer with cost breakdown

---

## Production Deployment

### Option A: Cloud Platform (Railway, Render, Fly.io)

**Railway (Recommended):**
1. Fork this repo
2. Create new project in Railway
3. Add service → Deploy from GitHub
4. Add environment variables (see `.env.example`)
5. Deploy

**Render:**
1. Create new Web Service
2. Connect GitHub repo
3. Build command: `cd backend && pip install -r requirements.txt`
4. Start command: `cd backend && uvicorn main:app --host 0.0.0.0 --port $PORT`
5. Add environment variables

### Option B: VPS (DigitalOcean, Linode, etc.)

```bash
# On your VPS
git clone https://github.com/ventoetc/LLM-cost-optimization.git
cd LLM-cost-optimization

# Setup environment
cp backend/.env.example backend/.env
nano backend/.env  # Add your API keys

# Start with Docker Compose
docker-compose up -d

# Setup reverse proxy (Nginx)
sudo apt install nginx
sudo nano /etc/nginx/sites-available/llm-optimizer
```

**Nginx config:**
```nginx
server {
    listen 80;
    server_name your-domain.com;

    location / {
        proxy_pass http://localhost:3000;
        proxy_http_version 1.1;
        proxy_set_header Upgrade $http_upgrade;
        proxy_set_header Connection 'upgrade';
        proxy_set_header Host $host;
        proxy_cache_bypass $http_upgrade;
    }

    location /api {
        proxy_pass http://localhost:8000;
        proxy_http_version 1.1;
        proxy_set_header Host $host;
        proxy_set_header X-Real-IP $remote_addr;
    }
}
```

```bash
# Enable and restart
sudo ln -s /etc/nginx/sites-available/llm-optimizer /etc/nginx/sites-enabled/
sudo nginx -t
sudo systemctl restart nginx

# Setup SSL with Let's Encrypt
sudo apt install certbot python3-certbot-nginx
sudo certbot --nginx -d your-domain.com
```

### Option C: Kubernetes

See `k8s/` directory for Helm charts and manifests.

---

## Configuration

### Environment Variables

**Required:**
```bash
OPENROUTER_API_KEY=sk-or-v1-...
```

**Optional (for direct provider access):**
```bash
ANTHROPIC_API_KEY=sk-ant-...
OPENAI_API_KEY=sk-...
```

**Application settings:**
```bash
DATABASE_URL=sqlite+aiosqlite:///./data/llm_optimizer.db
DEBUG=false
LOG_LEVEL=info
DECOMPOSER_MODEL=anthropic/claude-3-haiku
BASELINE_MODEL=anthropic/claude-opus-4-5
```

### Model Configuration

Edit `backend/app/core/config.py` to customize:
- Which models are available
- Cost per token for each model
- Default routing strategy

---

## Monitoring

### Health Check
```bash
curl http://localhost:8000/health
```

### Metrics Endpoint
```bash
curl http://localhost:8000/api/v1/metrics/summary
```

### Logs
```bash
# Docker logs
docker-compose logs -f backend

# Or if running directly
tail -f backend/logs/app.log
```

---

## Scaling

### Horizontal Scaling

The backend is stateless (except for SQLite). For production:

1. **Switch to PostgreSQL:**
```bash
DATABASE_URL=postgresql://user:pass@host:5432/llm_optimizer
```

2. **Run multiple backend instances:**
```yaml
# docker-compose.yml
services:
  backend:
    ...
    deploy:
      replicas: 3
```

3. **Add load balancer** (Nginx, HAProxy, or cloud LB)

### Vertical Scaling

For high-volume usage:
- 2+ CPU cores
- 4GB+ RAM
- SSD storage for database

---

## Security Checklist

- [ ] Change default secrets
- [ ] Use HTTPS (Let's Encrypt)
- [ ] Restrict API access (API keys, IP whitelist)
- [ ] Regular backups of database
- [ ] Keep dependencies updated
- [ ] Monitor for unusual usage patterns
- [ ] Set rate limits

---

## Cost Optimization

**Your infrastructure costs:**
- Small VPS: ~$5-10/month (1000-5000 requests/day)
- Medium: ~$20-40/month (10k-50k requests/day)
- Large: ~$100+/month (100k+ requests/day)

**Your API costs:**
Pass-through from OpenRouter (you pay what you use)

**Total cost per 1000 requests:** ~$0.50-2.00 (depends on complexity)

Compare to ChatGPT Plus: $20/month for unlimited (but single model, no verification)

---

## Troubleshooting

**Backend won't start:**
```bash
# Check logs
docker-compose logs backend

# Common issues:
# - Missing API key: Add to .env
# - Port conflict: Change port in docker-compose.yml
# - Database issue: Delete data/ directory and restart
```

**API returns errors:**
```bash
# Test OpenRouter connection
curl https://openrouter.ai/api/v1/models \
  -H "Authorization: Bearer $OPENROUTER_API_KEY"

# Check rate limits
# OpenRouter has rate limits - wait a minute and retry
```

**High costs:**
```bash
# Check which models are being used
curl http://localhost:8000/api/v1/metrics/detail

# Adjust routing in config.py to use cheaper models
```

---

## Getting Help

- **Documentation:** See README.md
- **Issues:** GitHub Issues
- **Community:** Discussions tab
- **Enterprise support:** Available with managed service

---

## Migrating to Managed Service

When you're ready for managed hosting:

1. Export your data: `docker-compose exec backend python export_data.py`
2. Sign up for managed service
3. Import your data and team settings
4. Point your clients to new API endpoint

We'll handle the migration for you - zero downtime.
