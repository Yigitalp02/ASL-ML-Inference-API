# 🚀 ASL ML API Deployment Guide

Complete guide to deploy the ASL ML Inference API on your home server.

---

## 📋 Prerequisites

- [x] Ubuntu Server 24.04 LTS running
- [x] Docker & Docker Compose installed
- [x] SSH access to `bilgin@homeserver`
- [x] Cloudflare domain: `ybilgin.com`
- [x] Cloudflare Tunnel configured

---

## 🎯 What You're Deploying

**Services:**
1. **asl-ml-api**: FastAPI inference server (port 8100)
2. **asl-postgres**: PostgreSQL database for logging

**External Access:**
- Local: `http://192.168.50.100:8200`
- Public: `https://asl.ybilgin.com` (via Cloudflare Tunnel)

**Features:**
- ⚡ <50ms prediction latency
- 📊 Automatic prediction logging
- 📈 Statistics endpoint
- 🔄 Auto-restart on failure
- 🔒 Non-root container user

---

## 📦 Step 1: Upload Files to Server

From your Windows machine, upload the `asl-ml-server/` folder:

```powershell
# Using SCP (from Windows PowerShell)
scp -r asl-ml-server bilgin@192.168.50.100:/tmp/

# OR use WinSCP, FileZilla, or VS Code Remote SSH
```

---

## 🔧 Step 2: Setup on Server

SSH into your server:

```bash
ssh bilgin@192.168.50.100
```

### 2.1. Create Directory Structure

```bash
# Move uploaded files to /opt/stack/
sudo mv /tmp/asl-ml-server /opt/stack/
sudo chown -R bilgin:bilgin /opt/stack/asl-ml-server

# Create config and data directories
sudo mkdir -p /opt/stack/config/asl-ml-api
sudo mkdir -p /opt/stack/data/asl-ml-api/logs
sudo mkdir -p /opt/stack/data/asl-postgres
sudo mkdir -p /opt/stack/ai-models

# Set permissions
sudo chown -R bilgin:bilgin /opt/stack/config/asl-ml-api
sudo chown -R bilgin:bilgin /opt/stack/data/asl-ml-api
sudo chown -R bilgin:bilgin /opt/stack/data/asl-postgres
sudo chown -R bilgin:bilgin /opt/stack/ai-models
```

### 2.2. Copy Database Init Script

```bash
cp /opt/stack/asl-ml-server/init-db.sql /opt/stack/config/asl-ml-api/
```

### 2.3. Copy ML Model

Transfer your trained model from Windows:

```powershell
# From Windows, copy the model
scp iot-sign-glove/models/rf_asl_15letters.pkl bilgin@192.168.50.100:/tmp/
```

Then on the server:

```bash
sudo mv /tmp/rf_asl_15letters.pkl /opt/stack/ai-models/
sudo chown bilgin:bilgin /opt/stack/ai-models/rf_asl_15letters.pkl
```

---

## 🐳 Step 3: Add to Docker Compose

Edit your main docker-compose.yml:

```bash
cd /opt/stack
sudo nano docker-compose.yml
```

Add the services from `docker-compose-service.yml`:

```yaml
# Append this to your existing services section:

  # PostgreSQL database for ASL predictions
  asl-postgres:
    image: postgres:16-alpine
    container_name: asl-postgres
    restart: unless-stopped
    environment:
      POSTGRES_DB: asl_predictions
      POSTGRES_USER: asl_user
      POSTGRES_PASSWORD: ${ASL_DB_PASSWORD:-SecurePassword123!}  # ← Change this!
    volumes:
      - /opt/stack/data/asl-postgres:/var/lib/postgresql/data
      - /opt/stack/config/asl-ml-api/init-db.sql:/docker-entrypoint-initdb.d/init.sql:ro
    networks:
      - stack-network
    healthcheck:
      test: ["CMD-SHELL", "pg_isready -U asl_user -d asl_predictions"]
      interval: 10s
      timeout: 5s
      retries: 5

  # ASL ML Inference API
  asl-ml-api:
    build:
      context: /opt/stack/asl-ml-server
      dockerfile: Dockerfile
    container_name: asl-ml-api
    restart: unless-stopped
    ports:
      - "8100:8000"
    environment:
      - MODEL_PATH=/models/rf_asl_15letters.pkl
      - POSTGRES_HOST=asl-postgres
      - POSTGRES_PORT=5432
      - POSTGRES_DB=asl_predictions
      - POSTGRES_USER=asl_user
      - POSTGRES_PASSWORD=${ASL_DB_PASSWORD:-SecurePassword123!}  # ← Same password!
    volumes:
      - /opt/stack/ai-models:/models:ro
      - /opt/stack/data/asl-ml-api/logs:/app/logs
    depends_on:
      asl-postgres:
        condition: service_healthy
    networks:
      - stack-network
```

**Note:** Make sure `stack-network` is defined in your compose file!

---

## 🚀 Step 4: Deploy

### 4.1. Build and Start Services

```bash
cd /opt/stack

# Build the API container
sudo docker compose build asl-ml-api

# Start both services
sudo docker compose up -d asl-postgres asl-ml-api

# Check logs
sudo docker compose logs -f asl-ml-api
```

Expected output:
```
INFO:     Started server process
INFO:     Waiting for application startup.
INFO:     Loading model from /models/rf_asl_15letters.pkl
INFO:     Model loaded: rf_asl_15letters
INFO:     Database pool created
INFO:     Application startup complete.
```

### 4.2. Verify Services

```bash
# Check if containers are running
sudo docker compose ps

# Check API health
curl http://192.168.50.100:8200/health

# Test prediction endpoint
curl -X POST http://192.168.50.100:8200/predict \
  -H "Content-Type: application/json" \
  -d '{"flex_sensors": [512.3, 678.1, 345.9, 890.2, 234.5]}'
```

Expected response:
```json
{
  "letter": "A",
  "confidence": 0.85,
  "all_probabilities": {...},
  "processing_time_ms": 12.5,
  "model_name": "rf_asl_15letters",
  "timestamp": 1234567890.123
}
```

---

## 🌐 Step 5: Configure Cloudflare Tunnel

### 5.1. Add Public Hostname

1. Go to: [Cloudflare Zero Trust Dashboard](https://one.dash.cloudflare.com/)
2. Navigate to: **Networks → Tunnels → Your Tunnel → Public Hostname**
3. Click **Add a public hostname**
4. Configure:
   - **Subdomain**: `asl`
   - **Domain**: `ybilgin.com`
   - **Service**: 
     - Type: `HTTP`
     - URL: `192.168.50.100:8200`

5. **Save**

### 5.2. Test External Access

```bash
# From any device (phone, laptop, etc.)
curl https://asl.ybilgin.com/health
```

### 5.3. Optional: Add Authentication

In Cloudflare Zero Trust:
1. **Access → Applications → Add an application**
2. Select: **Self-hosted**
3. Configure:
   - **Application name**: ASL ML API
   - **Subdomain**: `asl.ybilgin.com`
   - **Policy**: One-time PIN (email verification)

---

## 📊 Step 6: Monitor & Test

### Check API Documentation

Visit: `https://asl.ybilgin.com/docs`

This opens the interactive Swagger UI where you can test endpoints.

### View Statistics

```bash
curl https://asl.ybilgin.com/stats
```

Shows:
- Total predictions
- Average confidence
- Top predicted letters
- Processing times

### View Logs

```bash
# Real-time logs
sudo docker compose logs -f asl-ml-api

# Last 100 lines
sudo docker compose logs --tail=100 asl-ml-api
```

---

## 🔄 Step 7: Update Desktop App

Update your Tauri app to use the new API endpoint.

### Modify Rust Backend

Edit `src-tauri/src/main.rs`:

```rust
// Option 1: Use cloud API
let api_url = "https://asl.ybilgin.com/predict";

// Option 2: Use local API (when on home network)
let api_url = "http://192.168.50.100:8200/predict";

// Option 3: Try cloud, fallback to local Python
// (implement fallback logic)
```

### Update Prediction Function

```rust
#[tauri::command]
async fn predict_from_api(sensor_data: Vec<f64>) -> Result<String, String> {
    let client = reqwest::Client::new();
    let response = client
        .post("https://asl.ybilgin.com/predict")
        .json(&serde_json::json!({
            "flex_sensors": sensor_data,
            "device_id": "desktop-app"
        }))
        .send()
        .await
        .map_err(|e| format!("API request failed: {}", e))?;
    
    let result: serde_json::Value = response.json().await
        .map_err(|e| format!("Failed to parse response: {}", e))?;
    
    Ok(result.to_string())
}
```

---

## 🔧 Maintenance

### Update Model

```bash
# Upload new model
scp new_model.pkl bilgin@192.168.50.100:/opt/stack/ai-models/rf_asl_15letters.pkl

# Restart API
sudo docker compose restart asl-ml-api
```

### Update API Code

```bash
cd /opt/stack/asl-ml-server

# Pull latest changes (if using git)
sudo git pull

# Rebuild and restart
cd /opt/stack
sudo docker compose build asl-ml-api
sudo docker compose up -d asl-ml-api
```

### Backup Database

```bash
# Export predictions
sudo docker compose exec asl-postgres pg_dump -U asl_user asl_predictions > backup.sql

# Copy to HDD
sudo cp backup.sql /mnt/data/backups/asl-predictions-$(date +%Y%m%d).sql
```

### View Database

```bash
# Connect to PostgreSQL
sudo docker compose exec asl-postgres psql -U asl_user -d asl_predictions

# Run queries
SELECT COUNT(*) FROM predictions;
SELECT letter, COUNT(*) FROM predictions GROUP BY letter;
```

---

## 🐛 Troubleshooting

### API Not Starting

```bash
# Check logs
sudo docker compose logs asl-ml-api

# Common issues:
# 1. Model not found - check /opt/stack/ai-models/
# 2. Database not ready - check asl-postgres health
# 3. Port conflict - change 8100 to another port
```

### Model Not Loading

```bash
# Verify model exists
ls -lh /opt/stack/ai-models/

# Check model permissions
sudo chown bilgin:bilgin /opt/stack/ai-models/*.pkl

# Test model loading manually
sudo docker compose exec asl-ml-api python -c "import joblib; joblib.load('/models/rf_asl_15letters.pkl')"
```

### Database Connection Failed

```bash
# Check if postgres is running
sudo docker compose ps asl-postgres

# Check postgres logs
sudo docker compose logs asl-postgres

# Restart postgres
sudo docker compose restart asl-postgres
```

---

## 📈 Performance Benchmarks

Expected performance on your hardware (i7-4700HQ, 16GB RAM):

- **Inference Time**: 5-15ms
- **Total Response Time**: 20-50ms (including network + database)
- **Throughput**: ~200 predictions/second
- **Memory Usage**: ~150MB per worker
- **Startup Time**: ~5 seconds

---

## 🎉 Success Checklist

- [ ] Services running: `sudo docker compose ps`
- [ ] Health check passes: `curl http://192.168.50.100:8200/health`
- [ ] Prediction works locally: `curl -X POST http://192.168.50.100:8200/predict ...`
- [ ] External access works: `curl https://asl.ybilgin.com/health`
- [ ] Swagger docs accessible: `https://asl.ybilgin.com/docs`
- [ ] Database logging works: `sudo docker compose exec asl-postgres psql ...`

---

## 🔗 Next Steps

1. ✅ Deploy API (you're here!)
2. 🔄 Update desktop app to use API
3. 📊 Build analytics dashboard (optional)
4. 📱 Create mobile app (future)
5. 🔄 Implement automatic model retraining (future)

---

## 📞 API Endpoints Summary

| Endpoint | Method | Description |
|----------|--------|-------------|
| `/` | GET | API information |
| `/health` | GET | Health check |
| `/predict` | POST | Predict ASL letter |
| `/stats` | GET | Statistics |
| `/docs` | GET | Swagger UI |
| `/redoc` | GET | ReDoc documentation |

---

**Questions?** Check the logs first: `sudo docker compose logs -f asl-ml-api`

