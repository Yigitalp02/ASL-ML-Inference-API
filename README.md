# ASL ML Inference API

Cloud-based machine learning inference API for real-time American Sign Language (ASL) recognition from sensor glove data.

**Live API:** [https://api.ybilgin.com](https://api.ybilgin.com)

---

## Features

- **Fast Predictions**: <50ms inference time
- **15 ASL Letters**: A, B, C, D, E, F, I, K, O, S, T, V, W, X, Y
- **Cloud-Powered**: Deployed on home server with Cloudflare Zero Trust
- **PostgreSQL Logging**: Stores prediction history for analytics
- **RESTful API**: Simple JSON endpoints
- **Auto-generated Docs**: Interactive Swagger UI at `/docs`

---

## API Endpoints

### `GET /health`
Check API health and model status.

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_name": "rf_asl_15letters",
  "database_connected": true,
  "uptime_seconds": 123.45
}
```

### `POST /predict`
Predict ASL letter from sensor data.

**Request:**
```json
{
  "flex_sensors": [[512, 678, 345, 890, 234], [510, 680, 344, 891, 235]],
  "device_id": "desktop-app"
}
```

**Response:**
```json
{
  "letter": "A",
  "confidence": 0.85,
  "all_probabilities": {"A": 0.85, "B": 0.05, ...},
  "processing_time_ms": 23.5,
  "model_name": "rf_asl_15letters",
  "timestamp": 1234567890.123
}
```

### `GET /stats`
Get prediction statistics (last 24h).

### `GET /docs`
Interactive API documentation (Swagger UI).

---

## Tech Stack

- **FastAPI**: High-performance Python web framework
- **scikit-learn**: Random Forest ML model
- **PostgreSQL**: Prediction history database
- **Docker**: Containerized deployment
- **Cloudflare**: Zero Trust tunnel for HTTPS

---

## Deployment

The API is deployed on an Ubuntu Server 24.04 LTS home server using Docker Compose.

### Quick Deploy to Server

```bash
# Run the automated deployment script (from Windows)
.\deploy.ps1
```

This will:
1. Upload files to the server via SCP
2. Copy the ML model to `/opt/stack/ai-models/`
3. Build the Docker image
4. Start the service

### Manual Deployment

```bash
# On the server
cd /opt/stack/asl-ml-server
sudo git pull

# Rebuild and restart
cd /opt/stack
sudo docker compose build asl-ml-api
sudo docker compose up -d asl-ml-api

# Check logs
sudo docker compose logs -f asl-ml-api
```

---

## Configuration

The service is configured via environment variables in `/opt/stack/docker-compose.yml`:

```yaml
asl-ml-api:
  build: ./asl-ml-server
  environment:
    - MODEL_PATH=/models/rf_asl_15letters.pkl
    - POSTGRES_HOST=asl-postgres
    - POSTGRES_DB=asl_predictions
  volumes:
    - /opt/stack/ai-models:/models:ro
```

---

## Model Details

- **Type**: Random Forest Classifier
- **Features**: 25 statistical features (mean, std, min, max, range per flex sensor)
- **Training Data**: ASL-Sensor-Dataglove-Dataset (25 users)
- **Validation Accuracy**: ~70-75% (Leave-One-User-Out)
- **Real-World Performance**: 85-95% confidence with real glove

---

## Integration

### Desktop App (Tauri/Rust)

The desktop application calls the API for predictions:

```rust
let response = reqwest::Client::new()
    .post("https://api.ybilgin.com/predict")
    .json(&request_body)
    .send()
    .await?;
```

---

## License

MIT License - See parent repository for details.

---

## Live Demo

Visit [https://api.ybilgin.com/docs](https://api.ybilgin.com/docs) to try the API interactively!
