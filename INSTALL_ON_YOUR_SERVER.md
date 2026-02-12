# 🏠 Installation Guide for Your Specific Server

Step-by-step guide tailored for `bilgin@homeserver` (Ubuntu 24.04)

---

## ✅ What We're Adding

- **ASL ML API**: FastAPI inference server (256 MB RAM)
- **PostgreSQL**: Database for logging (128 MB RAM)
- **Total**: ~384 MB RAM, 1 CPU core

**Comparison to your services:**
- LLAMA AI: 8,000 MB (20x larger)
- This project: 384 MB ✅

---

## 📦 Step 1: Upload Files to Server

From Windows PowerShell:

```powershell
# Navigate to project
cd C:\Users\Yigit\Desktop\iot-sign-language-desktop

# Upload server code
scp -r asl-ml-server bilgin@192.168.50.100:/tmp/

# Upload ML model
scp iot-sign-glove\models\rf_asl_15letters.pkl bilgin@192.168.50.100:/tmp/
```

---

## 🔧 Step 2: Setup Directories on Server

SSH into server:

```bash
ssh bilgin@192.168.50.100
```

Run these commands:

```bash
# Move files to /opt/stack/
sudo mv /tmp/asl-ml-server /opt/stack/
sudo chown -R bilgin:bilgin /opt/stack/asl-ml-server

# Create data directories
sudo mkdir -p /opt/stack/config/asl-ml-api
sudo mkdir -p /opt/stack/data/asl-ml-api/logs
sudo mkdir -p /opt/stack/data/asl-postgres

# Set permissions
sudo chown -R bilgin:bilgin /opt/stack/config/asl-ml-api
sudo chown -R bilgin:bilgin /opt/stack/data/asl-ml-api
sudo chown -R bilgin:bilgin /opt/stack/data/asl-postgres

# Copy database init script
cp /opt/stack/asl-ml-server/init-db.sql /opt/stack/config/asl-ml-api/

# Move ML model to ai-models (you already have this folder!)
sudo mv /tmp/rf_asl_15letters.pkl /opt/stack/ai-models/
sudo chown bilgin:bilgin /opt/stack/ai-models/rf_asl_15letters.pkl

echo "✓ Setup complete!"
```

---

## 📝 Step 3: Add to Your Docker Compose

Edit your main compose file:

```bash
sudo nano /opt/stack/docker-compose.yml
```

**Scroll to the bottom**, just **before** `# --- AĞ TANIMLARI ---`, and add these services:

```yaml
  # -------------------------------------------------------
  # 8. ASL ML API
  # -------------------------------------------------------
  asl-postgres:
    image: postgres:16-alpine
    container_name: asl-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: asl_predictions
      POSTGRES_USER: asl_user
      POSTGRES_PASSWORD: YourStrongPassword123  # <--- CHANGE THIS!
    volumes:
      - /opt/stack/data/asl-postgres:/var/lib/postgresql/data
      - /opt/stack/config/asl-ml-api/init-db.sql:/docker-entrypoint-initdb.d/init.sql:ro
    networks:
      - data-net
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U asl_user -d asl_predictions"]
      interval: 10s
      timeout: 5s
      retries: 5
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 128M

  asl-ml-api:
    build:
      context: /opt/stack/asl-ml-server
      dockerfile: Dockerfile
    container_name: asl-ml-api
    restart: unless-stopped
    ports:
      - "8200:8000"
    environment:
      - MODEL_PATH=/models/rf_asl_15letters.pkl
      - POSTGRES_HOST=asl-postgres
      - POSTGRES_PORT=5432
      - POSTGRES_DB=asl_predictions
      - POSTGRES_USER=asl_user
      - POSTGRES_PASSWORD=YourStrongPassword123  # <--- SAME PASSWORD!
    volumes:
      - /opt/stack/ai-models:/models:ro
      - /opt/stack/data/asl-ml-api/logs:/app/logs
    depends_on:
      asl-postgres:
        condition: service_healthy
    networks:
      - proxy-net
      - data-net
    healthcheck:
      test: ["CMD", "python", "-c", "import requests; requests.get('http://localhost:8000/health')"]
      interval: 30s
      timeout: 10s
      retries: 3
      start_period: 40s
    deploy:
      resources:
        limits:
          cpus: '0.5'
          memory: 256M
```

**Save and exit**: `Ctrl+X`, then `Y`, then `Enter`

---

## 🚀 Step 4: Deploy

Build and start the services:

```bash
cd /opt/stack

# Build the API container
sudo docker compose build asl-ml-api

# Start both services
sudo docker compose up -d asl-postgres asl-ml-api

# Watch logs (Ctrl+C to exit)
sudo docker compose logs -f asl-ml-api
```

Expected output:
```
INFO:     Loading model from /models/rf_asl_15letters.pkl
INFO:     Model loaded: rf_asl_15letters
INFO:     Database pool created
INFO:     Application startup complete.
INFO:     Uvicorn running on http://0.0.0.0:8000
```

---

## 🧪 Step 5: Test Locally

```bash
# Test health endpoint
curl http://192.168.50.100:8200/health

# Test prediction
curl -X POST http://192.168.50.100:8200/predict \
  -H "Content-Type: application/json" \
  -d '{"flex_sensors": [512.3, 678.1, 345.9, 890.2, 234.5]}'
```

Expected response:
```json
{
  "letter": "A",
  "confidence": 0.85,
  "processing_time_ms": 12.5,
  ...
}
```

---

## 🌐 Step 6: Configure Cloudflare Tunnel

1. Go to: https://one.dash.cloudflare.com/
2. Navigate to: **Networks → Tunnels → Your Tunnel**
3. Click: **Public Hostname → Add a public hostname**
4. Configure:
   - **Subdomain**: `asl`
   - **Domain**: `ybilgin.com`
   - **Service Type**: `HTTP`
   - **URL**: `192.168.50.100:8200`
5. **Save**

Test external access:

```bash
curl https://asl.ybilgin.com/health
```

---

## 📊 Step 7: Add to Homepage Dashboard (Optional)

Edit your homepage config:

```bash
nano /home/bilgin/homepage/config/services.yaml
```

Add this section:

```yaml
- IoT Projects:
    - ASL ML API:
        icon: brain-circuit
        href: https://asl.ybilgin.com/docs
        description: Sign Language Inference API
        widget:
          type: customapi
          url: http://192.168.50.100:8200/health
          mappings:
            - field: status
              label: Status
            - field: model_name
              label: Model
```

Restart homepage:

```bash
cd /home/bilgin/homepage
sudo docker compose restart homepage
```

Visit: `https://homepage.ybilgin.com`

---

## ✅ Verification Checklist

Run these checks:

```bash
# 1. Check containers are running
sudo docker compose ps | grep asl

# 2. Check resource usage
sudo docker stats asl-ml-api asl-postgres --no-stream

# 3. Test local API
curl http://192.168.50.100:8200/health | jq

# 4. Test public API
curl https://asl.ybilgin.com/health | jq

# 5. View logs
sudo docker compose logs --tail=50 asl-ml-api

# 6. Check database
sudo docker compose exec asl-postgres psql -U asl_user -d asl_predictions -c "SELECT COUNT(*) FROM predictions;"
```

Expected resource usage:
```
CONTAINER     CPU %    MEM USAGE / LIMIT
asl-ml-api    2%       150MB / 256MB
asl-postgres  1%       80MB / 128MB
```

---

## 🔄 Maintenance Commands

### View Logs
```bash
sudo docker compose logs -f asl-ml-api
sudo docker compose logs --tail=100 asl-ml-api
```

### Restart Service
```bash
sudo docker compose restart asl-ml-api
```

### Update Model
```bash
# Upload new model from Windows
scp new_model.pkl bilgin@192.168.50.100:/opt/stack/ai-models/rf_asl_15letters.pkl

# Restart API
ssh bilgin@192.168.50.100
cd /opt/stack
sudo docker compose restart asl-ml-api
```

### View Database
```bash
sudo docker compose exec asl-postgres psql -U asl_user -d asl_predictions

# Inside psql:
SELECT * FROM predictions ORDER BY predicted_at DESC LIMIT 10;
SELECT letter, COUNT(*) FROM predictions GROUP BY letter;
\q  # to exit
```

### Check Stats
```bash
curl http://192.168.50.100:8200/stats | jq
```

---

## 🐛 Troubleshooting

### API Not Starting

```bash
# Check logs
sudo docker compose logs asl-ml-api

# Common issues:
# 1. Model not found
ls -lh /opt/stack/ai-models/rf_asl_15letters.pkl

# 2. Database not ready
sudo docker compose ps asl-postgres
sudo docker compose logs asl-postgres

# 3. Port conflict (should be fixed - using 8200)
sudo netstat -tulpn | grep 8200
```

### Can't Connect from Outside

```bash
# Check Cloudflare Tunnel
cd /home/bilgin/homepage
sudo docker compose logs cloudflared

# Test local first
curl http://192.168.50.100:8200/health

# Then test public
curl https://asl.ybilgin.com/health
```

---

## 🎉 Success!

If all checks pass:

- ✅ Local API: `http://192.168.50.100:8200/docs`
- ✅ Public API: `https://asl.ybilgin.com/docs`
- ✅ RAM Usage: ~384 MB (way less than LLAMA!)
- ✅ Ready for desktop app integration

**Next**: Update your desktop app to use `https://asl.ybilgin.com/predict`

---

## 📞 Quick Commands

```bash
# Start
cd /opt/stack && sudo docker compose up -d asl-ml-api asl-postgres

# Stop
sudo docker compose stop asl-ml-api asl-postgres

# Restart
sudo docker compose restart asl-ml-api

# Logs
sudo docker compose logs -f asl-ml-api

# Stats
sudo docker stats asl-ml-api

# Health
curl http://192.168.50.100:8200/health
```

---

**That's it!** Your server is now running a production ML API! 🚀

