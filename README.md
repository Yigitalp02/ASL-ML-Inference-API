# ASL ML Inference API

**Real-time American Sign Language Recognition API**

Cloud-based machine learning inference API for ASL recognition from sensor glove data.

**Live API:** [https://api.ybilgin.com](https://api.ybilgin.com)  
**Interactive Docs:** [https://api.ybilgin.com/docs](https://api.ybilgin.com/docs)

---

## Quick Start

### Try the API (No Code Required!)

1. Go to [**https://api.ybilgin.com/docs**](https://api.ybilgin.com/docs)
2. Click on **`POST /predict`**
3. Click **"Try it out"**
4. Use the example data or modify it
5. Click **"Execute"**
6. See your prediction!

### Example with Python

```python
import requests

# API endpoint
url = "https://api.ybilgin.com/predict"

# Sensor data (5 flex sensors)
data = {
    "flex_sensors": [
        [512, 678, 345, 890, 234],  # Sample 1
        [510, 680, 344, 891, 235],  # Sample 2
        [511, 679, 346, 892, 236]   # Sample 3
    ],
    "device_id": "my-glove"
}

# Make request
response = requests.post(url, json=data)
result = response.json()

# Print result
print(f"Predicted Letter: {result['letter']}")
print(f"Confidence: {result['confidence']:.2%}")
print(f"Processing Time: {result['processing_time_ms']:.1f}ms")
```

---

## Features

- **Fast Predictions**: <50ms inference time
- **15 ASL Letters**: A, B, C, D, E, F, I, K, O, S, T, V, W, X, Y
- **Cloud-Powered**: Deployed with Docker + Cloudflare Zero Trust
- **PostgreSQL Logging**: Stores prediction history for analytics
- **RESTful API**: Simple JSON endpoints
- **Auto-generated Docs**: Interactive Swagger UI at `/docs`
- **High Accuracy**: 85-95% confidence with real glove data

---

## API Endpoints

### `GET /` - API Information
Get basic service information.

```bash
curl https://api.ybilgin.com/
```

### `GET /health` - Health Check
Check API health and model status.

```bash
curl https://api.ybilgin.com/health
```

**Response:**
```json
{
  "status": "healthy",
  "model_loaded": true,
  "model_name": "rf_asl_15letters",
  "model_loaded_at": "2026-02-18T16:30:00",
  "database_connected": true,
  "uptime_seconds": 123.45
}
```

### `POST /predict` - Predict ASL Sign (Main Endpoint)
Predict ASL letter from sensor data.

**Request:**
```json
{
  "flex_sensors": [
    [512, 678, 345, 890, 234],
    [510, 680, 344, 891, 235]
  ],
  "device_id": "desktop-app"
}
```

**Response:**
```json
{
  "letter": "A",
  "confidence": 0.92,
  "all_probabilities": {
    "A": 0.92,
    "S": 0.04,
    "B": 0.02
  },
  "processing_time_ms": 23.5,
  "model_name": "rf_asl_15letters",
  "timestamp": 1708268123.456
}
```

### `GET /stats` - Prediction Statistics
Get analytics about API usage (last 24h).

```bash
curl https://api.ybilgin.com/stats
```

**Response:**
```json
{
  "total_predictions": 1523,
  "last_24h_avg_confidence": 0.87,
  "last_1h_avg_processing_ms": 28.3,
  "top_letters_24h": [
    {"letter": "A", "count": 45},
    {"letter": "S", "count": 38}
  ]
}
```

### `GET /docs` - Interactive Documentation
Swagger UI for testing the API directly in your browser.

### `GET /redoc` - Alternative Documentation
ReDoc-styled API documentation.

---

## Usage Examples

### Python

```python
import requests

def predict_asl_letter(sensor_readings):
    """Predict ASL letter from sensor data"""
    response = requests.post(
        "https://api.ybilgin.com/predict",
        json={
            "flex_sensors": sensor_readings,
            "device_id": "python-client"
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        return result['letter'], result['confidence']
    else:
        return None, 0

# Example usage
sensor_data = [[512, 678, 345, 890, 234]]
letter, confidence = predict_asl_letter(sensor_data)
print(f"Predicted: {letter} ({confidence:.2%})")
```

### JavaScript (Node.js)

```javascript
const axios = require('axios');

async function predictASL(sensorData) {
  try {
    const response = await axios.post(
      'https://api.ybilgin.com/predict',
      {
        flex_sensors: sensorData,
        device_id: 'js-client'
      }
    );
    
    const { letter, confidence } = response.data;
    console.log(`Predicted: ${letter} (${(confidence * 100).toFixed(1)}%)`);
    return response.data;
  } catch (error) {
    console.error('Prediction failed:', error.message);
  }
}

// Example usage
const sensorData = [[512, 678, 345, 890, 234]];
predictASL(sensorData);
```

### Rust (for Tauri Desktop App)

```rust
use serde::{Deserialize, Serialize};
use reqwest;

#[derive(Serialize)]
struct PredictionRequest {
    flex_sensors: Vec<Vec<f32>>,
    device_id: String,
}

#[derive(Deserialize)]
struct PredictionResponse {
    letter: String,
    confidence: f64,
    processing_time_ms: f64,
}

async fn predict_asl(sensor_data: Vec<Vec<f32>>) -> Result<PredictionResponse, reqwest::Error> {
    let client = reqwest::Client::new();
    let request = PredictionRequest {
        flex_sensors: sensor_data,
        device_id: "tauri-app".to_string(),
    };
    
    let response = client
        .post("https://api.ybilgin.com/predict")
        .json(&request)
        .send()
        .await?
        .json::<PredictionResponse>()
        .await?;
    
    Ok(response)
}
```

### cURL

```bash
# Make a prediction
curl -X POST "https://api.ybilgin.com/predict" \
  -H "Content-Type: application/json" \
  -d '{
    "flex_sensors": [[512, 678, 345, 890, 234]],
    "device_id": "curl-test"
  }'

# Health check
curl https://api.ybilgin.com/health

# Statistics
curl https://api.ybilgin.com/stats
```

---

## Input Data Format

### Flex Sensors (Required)

The API expects **5 flex sensor values** (one per finger):
- Thumb (flex_1)
- Index (flex_2)
- Middle (flex_3)
- Ring (flex_4)
- Pinkie (flex_5)

**Value Range:** 0-1023 (Arduino analog read range)

### Input Formats

#### Option 1: Windowed Data (Recommended)
Multiple samples for better accuracy:
```json
{
  "flex_sensors": [
    [512, 678, 345, 890, 234],
    [510, 680, 344, 891, 235],
    [511, 679, 346, 892, 236]
  ]
}
```

#### Option 2: Single Sample (Quick Mode)
One sample for faster response:
```json
{
  "flex_sensors": [512, 678, 345, 890, 234]
}
```

### Tips for Best Results

DO:
- Send 100-150 samples (2-3 seconds at 50Hz sampling rate)
- Ensure sensors are calibrated
- Hold the sign steady during data collection
- Use windowed data for best accuracy

DON'T:
- Send partial or incomplete data
- Mix samples from different signs
- Ignore low confidence scores (<0.7)

---

## Supported ASL Letters

The model recognizes **15 letters**:

| Letter | Typical Confidence | Notes |
|--------|-------------------|-------|
| A | 90-95% | Very distinct |
| B | 85-90% | High confidence |
| C | 85-90% | Clear pattern |
| D | 85-92% | Reliable |
| E | 88-93% | Strong signal |
| F | 80-88% | Good accuracy |
| I | 92-96% | Excellent |
| K | 82-88% | Moderate |
| O | 90-95% | Very distinct |
| S | 93-97% | Excellent |
| T | 75-85% | Can confuse with X |
| V | 88-92% | Good |
| W | 85-90% | Reliable |
| X | 78-86% | Can confuse with T |
| Y | 90-94% | Very good |

**Why these 15 letters?**
- They have distinct finger bending patterns
- Can be recognized with only flex sensors (no IMU needed)
- Form useful words (DEAF, WAVY, TAXI, etc.)

---

## Tech Stack

- **FastAPI**: High-performance Python web framework
- **scikit-learn**: Random Forest ML model
- **PostgreSQL**: Prediction history database
- **Docker**: Containerized deployment
- **Cloudflare**: Zero Trust tunnel for HTTPS
- **Ubuntu Server 24.04 LTS**: Deployment environment

---

## Model Details

- **Type**: Random Forest Classifier
- **Features**: 25 statistical features (mean, std, min, max, range per sensor)
- **Training Data**: ASL-Sensor-Dataglove-Dataset (25 users, 40 gestures each)
- **Validation Method**: Leave-One-User-Out Cross-Validation
- **Validation Accuracy**: ~70-75%
- **Real-World Performance**: 85-95% with calibrated glove
- **Inference Time**: 20-40ms

---

## Deployment

The API is deployed on an Ubuntu Server 24.04 LTS home server using Docker Compose with Cloudflare Zero Trust tunnel.

### Quick Deploy to Server

```powershell
# From Windows, run the automated deployment script
.\deploy.ps1
```

This script will:
1. Upload files to the server via SCP
2. Copy the ML model to `/opt/stack/ai-models/`
3. Build the Docker image
4. Start the service with Docker Compose
5. Show service logs

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

# Check status
sudo docker compose ps asl-ml-api
```

---

## Response Codes

| Code | Description |
|------|-------------|
| 200 | Success - Prediction completed |
| 422 | Validation Error - Invalid input format |
| 500 | Internal Server Error - Prediction failed |
| 503 | Service Unavailable - Model not loaded |

---

## Support & Contributing

### Get Help

- **API Issues**: Check `/docs` for interactive testing
- **Email**: support@ybilgin.com
- **GitHub**: https://github.com/Yigitalp02

### Contributing

We welcome contributions! Areas that need help:
- Support for more ASL letters
- Improved model accuracy
- Mobile SDK (iOS/Android)
- Performance optimizations

---

## License

MIT License - See [LICENSE](LICENSE) file for details.

---

**Happy Coding! Let us know what you build with this API!**

For more information, visit: [https://api.ybilgin.com/docs](https://api.ybilgin.com/docs)
