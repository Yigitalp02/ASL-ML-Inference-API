# 🚀 Quick Reference Card

One-page cheat sheet for ASL ML API.

---

## 📡 Endpoints

```bash
# Health check
GET http://192.168.50.100:8100/health
GET https://asl.ybilgin.com/health

# Predict letter
POST http://192.168.50.100:8100/predict
POST https://asl.ybilgin.com/predict
Body: {"flex_sensors": [512.3, 678.1, 345.9, 890.2, 234.5]}

# Statistics
GET http://192.168.50.100:8100/stats

# Interactive docs
GET http://192.168.50.100:8100/docs
```

---

## 🐳 Docker Commands

```bash
# Build
sudo docker compose build asl-ml-api

# Start
sudo docker compose up -d asl-ml-api asl-postgres

# Stop
sudo docker compose stop asl-ml-api asl-postgres

# Restart
sudo docker compose restart asl-ml-api

# Logs
sudo docker compose logs -f asl-ml-api
sudo docker compose logs --tail=100 asl-ml-api

# Status
sudo docker compose ps

# Rebuild & restart
sudo docker compose build asl-ml-api && sudo docker compose up -d asl-ml-api
```

---

## 📂 Directory Structure

```
/opt/stack/
├── asl-ml-server/          # Source code
├── config/asl-ml-api/      # Config files
│   └── init-db.sql
├── data/asl-ml-api/        # Logs
│   └── logs/
├── data/asl-postgres/      # Database data
└── ai-models/              # ML models
    └── rf_asl_15letters.pkl
```

---

## 🔄 Update Workflows

### Update Model

```bash
# Upload new model
scp new_model.pkl bilgin@192.168.50.100:/opt/stack/ai-models/rf_asl_15letters.pkl

# Restart API
ssh bilgin@192.168.50.100
cd /opt/stack
sudo docker compose restart asl-ml-api
```

### Update Code

```bash
# SSH to server
ssh bilgin@192.168.50.100

# Pull changes (if using git)
cd /opt/stack/asl-ml-server
git pull

# Rebuild and restart
cd /opt/stack
sudo docker compose build asl-ml-api
sudo docker compose up -d asl-ml-api
```

---

## 🧪 Testing

```bash
# Test script (bash)
./test_api.sh http://192.168.50.100:8100

# Test client (Python)
python test_client.py

# Load test
python test_client.py --load 100

# Manual curl test
curl -X POST http://192.168.50.100:8100/predict \
  -H "Content-Type: application/json" \
  -d '{"flex_sensors": [512.3, 678.1, 345.9, 890.2, 234.5]}'
```

---

## 🗄️ Database

```bash
# Connect to PostgreSQL
sudo docker compose exec asl-postgres psql -U asl_user -d asl_predictions

# View predictions
SELECT * FROM predictions ORDER BY predicted_at DESC LIMIT 10;

# Letter frequency
SELECT letter, COUNT(*) FROM predictions GROUP BY letter;

# Daily stats
SELECT * FROM daily_stats;

# Backup
sudo docker compose exec asl-postgres pg_dump -U asl_user asl_predictions > backup.sql
```

---

## 🌐 Cloudflare Setup

1. Go to: [Cloudflare Zero Trust](https://one.dash.cloudflare.com/)
2. Networks → Tunnels → Your Tunnel → Public Hostname
3. Add hostname:
   - Subdomain: `asl`
   - Domain: `ybilgin.com`
   - Service: `http://192.168.50.100:8100`
4. Test: `curl https://asl.ybilgin.com/health`

---

## 🐛 Troubleshooting

```bash
# Check if services are running
sudo docker compose ps

# View recent logs
sudo docker compose logs --tail=50 asl-ml-api

# Check health
curl http://192.168.50.100:8100/health

# Restart everything
sudo docker compose restart asl-postgres asl-ml-api

# Check model exists
sudo docker compose exec asl-ml-api ls -l /models/

# Test database connection
sudo docker compose exec asl-ml-api python -c \
  "import asyncpg; print('DB test OK')"
```

---

## 📊 Monitoring

```bash
# Container stats
sudo docker stats asl-ml-api

# Disk usage
df -h /opt/stack/

# Database size
sudo docker compose exec asl-postgres psql -U asl_user -d asl_predictions -c \
  "SELECT pg_size_pretty(pg_database_size('asl_predictions'));"

# Prediction count
curl http://192.168.50.100:8100/stats | jq '.total_predictions'
```

---

## 🔒 Security Checklist

- [ ] Change default database password
- [ ] Configure Cloudflare WAF
- [ ] Enable Cloudflare Access (email OTP)
- [ ] Set up log rotation
- [ ] Configure backup cron job
- [ ] Monitor error logs
- [ ] Test disaster recovery

---

## 🚀 Performance Tips

- **Cold start**: ~5 seconds
- **Inference**: 5-15ms
- **Total latency**: 20-50ms
- **Throughput**: ~200 req/s

To improve:
- Use multiple workers (edit Dockerfile)
- Add Redis caching
- Use load balancer (nginx)
- Enable connection pooling (already enabled)

---

## 📞 Support

**Logs**: `sudo docker compose logs -f asl-ml-api`

**Docs**: `http://192.168.50.100:8100/docs`

**Health**: `curl http://192.168.50.100:8100/health`

---

**Deployment Guide**: See `DEPLOYMENT_GUIDE.md` for full instructions

