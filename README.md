# ASL ML Inference API

Fast, scalable ML inference server for real-time American Sign Language recognition.

---

## Overview

This is a production-ready FastAPI service that provides real-time sign language predictions from IoT glove sensor data. Designed for low-latency (<50ms) inference with automatic logging and analytics.

### Features

- **Fast**: <50ms prediction latency
- **Logging**: Automatic prediction storage in PostgreSQL
- **Analytics**: Built-in statistics endpoints
- **Secure**: Non-root container, CORS configured
- **Containerized**: Docker Compose ready
- **Documented**: Auto-generated Swagger/ReDoc docs
- **Production Ready**: Health checks, graceful shutdown, error handling

---

## Architecture

```
┌─────────────┐      ┌──────────────┐      ┌─────────────┐
│  IoT Glove  │ ───► │ Desktop App  │ ───► │  FastAPI    │
│   (5 flex)  │      │   (Tauri)    │      │   Server    │
└─────────────┘      └──────────────┘      └──────┬──────┘
                                                   │
                                            ┌──────▼──────┐
                                            │ PostgreSQL  │
                                            │  (Logging)  │
                                            └─────────────┘
```

---

## Project Structure

```
asl-ml-server/
├── app/
│   └── main.py              # FastAPI application
├── Dockerfile               # Container definition
├── requirements.txt         # Python dependencies
├── init-db.sql             # Database schema
├── docker-compose-service.yml  # Service definition
├── DEPLOYMENT_GUIDE.md     # Complete deployment guide
└── README.md               # This file
```

---

## Quick Start

### Prerequisites

- Docker & Docker Compose
- Trained ML model (.pkl file)
- Python 3.11+ (for local development)

### Local Development

```bash
# Install dependencies
pip install -r requirements.txt

# Set environment variables
export MODEL_PATH=../iot-sign-glove/models/rf_asl_15letters.pkl
export POSTGRES_HOST=localhost
export POSTGRES_DB=asl_predictions
export POSTGRES_USER=asl_user
export POSTGRES_PASSWORD=password

# Run locally
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

Visit: http://localhost:8000/docs

### Docker Deployment

See [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md) for complete instructions.

Quick version:

```bash
# Build
docker compose build asl-ml-api

# Run
docker compose up -d asl-ml-api asl-postgres

# Check logs
docker compose logs -f asl-ml-api

# Test
curl http://localhost:8200/health
```

---

## API Endpoints

### POST /predict

Predict ASL letter from sensor data.

**Request:**
```json
{
  "flex_sensors": [512.3, 678.1, 345.9, 890.2, 234.5],
  "timestamp": 1234567890.123,
  "device_id": "glove-001"
}
```

**Response:**
```json
{
  "letter": "A",
  "confidence": 0.85,
  "all_probabilities": {
    "A": 0.85,
    "B": 0.10,
    "C": 0.05
  },
  "processing_time_ms": 12.5,
  "model_name": "rf_asl_15letters",
  "timestamp": 1234567890.123
}
```

### GET /health

Health check endpoint.

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_name": "rf_asl_15letters",
  "model_loaded_at": "2024-01-01T12:00:00",
  "database_connected": true,
  "uptime_seconds": 3600.5
}
```

### GET /stats

Get prediction statistics.

**Response:**
```json
{
  "total_predictions": 1234,
  "last_24h_avg_confidence": 0.82,
  "last_1h_avg_processing_ms": 15.3,
  "top_letters_24h": [
    {"letter": "A", "count": 150},
    {"letter": "E", "count": 120}
  ]
}
```

### GET /docs

Interactive Swagger UI for testing endpoints.

### GET /

API information and available endpoints.

---

## Configuration

### Environment Variables

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_PATH` | `/models/rf_asl_15letters.pkl` | Path to ML model |
| `POSTGRES_HOST` | `postgres` | Database host |
| `POSTGRES_PORT` | `5432` | Database port |
| `POSTGRES_DB` | `asl_predictions` | Database name |
| `POSTGRES_USER` | `asl_user` | Database user |
| `POSTGRES_PASSWORD` | `asl_password` | Database password |

### Model Requirements

The API expects a scikit-learn Random Forest model with:
- Input: 5 features (flex sensor values)
- Output: String labels (A-Z letters)
- Methods: `predict()`, `predict_proba()`, `classes_`

Supported model files:
- `rf_asl_15letters.pkl` (recommended)
- `rf_asl_calibrated.pkl`
- Any scikit-learn classifier with above interface

---

## Database Schema

### Table: predictions

| Column | Type | Description |
|--------|------|-------------|
| id | SERIAL | Primary key |
| letter | VARCHAR(5) | Predicted letter |
| confidence | FLOAT | Confidence score (0-1) |
| sensor_data | FLOAT[] | Raw sensor values |
| device_id | VARCHAR(100) | Source device |
| processing_time_ms | FLOAT | Inference time |
| predicted_at | TIMESTAMP | Prediction time |
| created_at | TIMESTAMP | Row creation time |

### Views

- `daily_stats`: Aggregated daily statistics
- `letter_frequency`: Letter distribution and accuracy

---

## Testing

### Health Check

```bash
curl http://localhost:8200/health
```

### Test Prediction

```bash
curl -X POST http://localhost:8200/predict \
  -H "Content-Type: application/json" \
  -d '{
    "flex_sensors": [512.3, 678.1, 345.9, 890.2, 234.5],
    "device_id": "test-client"
  }'
```

### Load Testing

```bash
# Install Apache Bench
sudo apt install apache2-utils

# Run load test (1000 requests, 10 concurrent)
ab -n 1000 -c 10 -p test-payload.json -T application/json \
  http://localhost:8200/predict
```

---

## Performance

Benchmarked on i7-4700HQ, 16GB RAM:

- **Cold Start**: ~5 seconds
- **Inference Time**: 5-15ms
- **Total Response**: 20-50ms (including DB logging)
- **Throughput**: ~200 requests/second
- **Memory**: ~150MB per worker

---

## Security

- Non-root container user
- Read-only model mount
- CORS configured
- Input validation (Pydantic)
- SQL injection protection (parameterized queries)
- No secrets in code (environment variables)

**Production Recommendations:**
- Use strong database password
- Enable Cloudflare WAF
- Add rate limiting (e.g., nginx)
- Enable access logs
- Set up monitoring (Prometheus/Grafana)

---

## Troubleshooting

### Model Not Loading

```bash
# Check if model exists
docker compose exec asl-ml-api ls -l /models/

# Check model format
docker compose exec asl-ml-api python -c \
  "import joblib; m = joblib.load('/models/rf_asl_15letters.pkl'); print(m)"
```

### Database Connection Issues

```bash
# Check if postgres is running
docker compose ps asl-postgres

# Test connection
docker compose exec asl-ml-api python -c \
  "import asyncpg; import asyncio; asyncio.run(asyncpg.connect(host='asl-postgres', user='asl_user', password='password', database='asl_predictions'))"
```

### High Latency

```bash
# Check container resources
docker stats asl-ml-api

# Enable debug logging
docker compose logs -f asl-ml-api
```

---

## Updates

### Update Model

```bash
# Replace model file
cp new_model.pkl /opt/stack/ai-models/rf_asl_15letters.pkl

# Restart API (picks up new model)
docker compose restart asl-ml-api
```

### Update Code

```bash
# Pull latest code
cd /opt/stack/asl-ml-server
git pull

# Rebuild and restart
cd /opt/stack
docker compose build asl-ml-api
docker compose up -d asl-ml-api
```

---

## Integration

### Desktop App (Tauri/Rust)

```rust
use reqwest;
use serde_json::json;

async fn predict_letter(sensors: Vec<f64>) -> Result<String, Box<dyn std::error::Error>> {
    let client = reqwest::Client::new();
    let res = client
        .post("https://asl.ybilgin.com/predict")
        .json(&json!({
            "flex_sensors": sensors,
            "device_id": "desktop-app"
        }))
        .send()
        .await?
        .json::<serde_json::Value>()
        .await?;
    
    Ok(res["letter"].as_str().unwrap().to_string())
}
```

### Python Client

```python
import requests

def predict_letter(sensors):
    response = requests.post(
        "https://asl.ybilgin.com/predict",
        json={
            "flex_sensors": sensors,
            "device_id": "python-client"
        }
    )
    return response.json()

# Use it
result = predict_letter([512.3, 678.1, 345.9, 890.2, 234.5])
print(f"Predicted: {result['letter']} (confidence: {result['confidence']})")
```

---

## License

Same as parent project.

---

## Credits

- Built with [FastAPI](https://fastapi.tiangolo.com/)
- ML models trained with [scikit-learn](https://scikit-learn.org/)
- Deployed with [Docker](https://www.docker.com/)

---

**For deployment instructions, see [DEPLOYMENT_GUIDE.md](./DEPLOYMENT_GUIDE.md)**

