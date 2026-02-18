# ASL ML Inference API

Real-time American Sign Language Recognition API powered by machine learning.

Cloud-based inference API for ASL recognition from sensor glove data using Random Forest classification.

**Live API**: [https://api.ybilgin.com](https://api.ybilgin.com)  
**Interactive Docs**: [https://api.ybilgin.com/docs](https://api.ybilgin.com/docs)  
**Version**: 2.0.0  
**Last Updated**: February 2026

---

## Quick Start

### Try the API (No Code Required)

1. Visit [https://api.ybilgin.com/docs](https://api.ybilgin.com/docs)
2. Click on `POST /predict` endpoint
3. Click "Try it out"
4. Add your API key in X-API-Key header
5. Use the example data or modify it
6. Click "Execute"
7. View your prediction results

### Example with Python

```python
import requests

url = "https://api.ybilgin.com/predict"
headers = {
    "X-API-Key": "your-api-key-here",
    "Content-Type": "application/json"
}

data = {
    "flex_sensors": [
        [512, 678, 345, 890, 234],  # Sample 1
        [510, 680, 344, 891, 235],  # Sample 2
        [511, 679, 346, 892, 236]   # Sample 3
    ],
    "device_id": "my-glove"
}

response = requests.post(url, headers=headers, json=data)
result = response.json()

print(f"Predicted Letter: {result['letter']}")
print(f"Confidence: {result['confidence']:.2%}")
print(f"Processing Time: {result['processing_time_ms']:.1f}ms")
```

---

## Features

- **Fast Predictions**: Less than 50ms inference time
- **15 ASL Letters**: A, B, C, D, E, F, I, K, O, S, T, V, W, X, Y
- **API Key Authentication**: Secure access control
- **Rate Limiting**: 100 requests per minute per IP
- **Cloud Deployment**: Docker + Cloudflare Zero Trust
- **PostgreSQL Logging**: Stores prediction history for analytics
- **RESTful API**: Simple JSON request/response
- **Auto-generated Docs**: Interactive Swagger UI
- **High Accuracy**: 85-95% confidence with calibrated glove data

---

## API Endpoints

### GET / - API Information
Get basic service information.

```bash
curl https://api.ybilgin.com/
```

**Response:**
```json
{
  "name": "ASL ML Inference API",
  "version": "2.0.0",
  "description": "Real-time ASL recognition from sensor glove data"
}
```

### GET /health - Health Check
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
  "database_connected": true,
  "uptime_seconds": 123456,
  "authentication_enabled": true,
  "rate_limiting_enabled": true
}
```

### POST /predict - Predict ASL Sign
Predict ASL letter from sensor data.

**Authentication Required**: X-API-Key header

**Request:**
```json
{
  "flex_sensors": [
    [512, 678, 345, 890, 234],
    [510, 680, 344, 891, 235],
    [511, 679, 346, 892, 236]
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
    "E": 0.02,
    "B": 0.01
  },
  "processing_time_ms": 23.5,
  "model_name": "rf_asl_15letters",
  "timestamp": 1708268123.456
}
```

### GET /stats - Prediction Statistics
Get analytics about API usage.

**Authentication Required**: X-API-Key header

```bash
curl -H "X-API-Key: your-key" https://api.ybilgin.com/stats
```

**Response:**
```json
{
  "total_predictions": 1523,
  "predictions_today": 145,
  "unique_devices": 5,
  "average_confidence": 0.87,
  "letter_distribution": {
    "A": 120,
    "B": 98,
    "C": 75
  }
}
```

### GET /docs - Interactive Documentation
Swagger UI for testing the API directly in browser.

### GET /redoc - Alternative Documentation
ReDoc-styled API documentation.

---

## Usage Examples

### Python

```python
import requests

def predict_asl_letter(sensor_readings, api_key):
    """Predict ASL letter from sensor data"""
    response = requests.post(
        "https://api.ybilgin.com/predict",
        headers={"X-API-Key": api_key},
        json={
            "flex_sensors": sensor_readings,
            "device_id": "python-client"
        }
    )
    
    if response.status_code == 200:
        result = response.json()
        return result['letter'], result['confidence']
    elif response.status_code == 401:
        raise Exception("Invalid API key")
    elif response.status_code == 429:
        raise Exception("Rate limit exceeded")
    else:
        raise Exception(f"API error: {response.status_code}")

# Example usage
sensor_data = [[512, 678, 345, 890, 234]]
api_key = "your-api-key-here"
letter, confidence = predict_asl_letter(sensor_data, api_key)
print(f"Predicted: {letter} ({confidence:.2%})")
```

### JavaScript (Node.js)

```javascript
const axios = require('axios');

async function predictASL(sensorData, apiKey) {
  try {
    const response = await axios.post(
      'https://api.ybilgin.com/predict',
      {
        flex_sensors: sensorData,
        device_id: 'js-client'
      },
      {
        headers: {
          'X-API-Key': apiKey,
          'Content-Type': 'application/json'
        }
      }
    );
    
    const { letter, confidence } = response.data;
    console.log(`Predicted: ${letter} (${(confidence * 100).toFixed(1)}%)`);
    return response.data;
  } catch (error) {
    if (error.response?.status === 401) {
      console.error('Invalid API key');
    } else if (error.response?.status === 429) {
      console.error('Rate limit exceeded');
    } else {
      console.error('Prediction failed:', error.message);
    }
  }
}

// Example usage
const sensorData = [[512, 678, 345, 890, 234]];
const apiKey = 'your-api-key-here';
predictASL(sensorData, apiKey);
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

async fn predict_asl(
    sensor_data: Vec<Vec<f32>>,
    api_key: &str
) -> Result<PredictionResponse, reqwest::Error> {
    let client = reqwest::Client::new();
    let request = PredictionRequest {
        flex_sensors: sensor_data,
        device_id: "tauri-app".to_string(),
    };
    
    let response = client
        .post("https://api.ybilgin.com/predict")
        .header("X-API-Key", api_key)
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
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "flex_sensors": [[512, 678, 345, 890, 234]],
    "device_id": "curl-test"
  }'

# Health check
curl https://api.ybilgin.com/health

# Statistics (requires API key)
curl -H "X-API-Key: your-api-key-here" \
  https://api.ybilgin.com/stats
```

---

## Input Data Format

### Flex Sensors (Required)

The API expects 5 flex sensor values (one per finger):
- Thumb (flex_1)
- Index (flex_2)
- Middle (flex_3)
- Ring (flex_4)
- Pinkie (flex_5)

**Value Range**: 0-1023 (Arduino ADC range)

### Input Formats

**Option 1: Windowed Data (Recommended)**
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

**Option 2: Single Sample (Quick Mode)**
One sample for faster response:
```json
{
  "flex_sensors": [512, 678, 345, 890, 234]
}
```

### Best Practices

**DO:**
- Send 100-200 samples (2-4 seconds at 50Hz sampling)
- Calibrate sensors before collection
- Hold sign steady during collection
- Use windowed data for better accuracy

**DON'T:**
- Send partial or incomplete data
- Mix samples from different signs
- Ignore low confidence scores (below 0.7)
- Exceed rate limits

---

## Supported ASL Letters

The model recognizes 15 letters:

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
- Distinct finger bending patterns
- No IMU/orientation sensors needed
- Form useful words (DEAF, WAVY, TAXI, etc.)

---

## Authentication

### API Key Authentication

All protected endpoints require an API key in the request header:

```http
X-API-Key: your-api-key-here
```

### Getting an API Key

Contact the project maintainer or follow the instructions in `SECURITY_SETUP.md` to generate a new API key.

### Protected Endpoints

- `POST /predict` - Requires API key
- `GET /stats` - Requires API key

### Public Endpoints

- `GET /` - No authentication required
- `GET /health` - No authentication required
- `GET /docs` - No authentication required
- `GET /redoc` - No authentication required

---

## Rate Limiting

- **Limit**: 100 requests per minute per IP address
- **Window**: 60 seconds rolling window
- **Headers**:
  - `X-RateLimit-Limit`: Maximum requests allowed
  - `X-RateLimit-Remaining`: Remaining requests in window
- **Response**: 429 Too Many Requests when limit exceeded

---

## Tech Stack

- **Framework**: FastAPI (Python 3.11)
- **ML Model**: scikit-learn Random Forest Classifier
- **Database**: PostgreSQL 15 (prediction logging)
- **Container**: Docker + Docker Compose
- **Reverse Proxy**: Cloudflare Zero Trust tunnel
- **Server**: Ubuntu Server 24.04 LTS
- **Deployment**: Automated via deploy.ps1 script

---

## Model Details

- **Type**: Random Forest Classifier
- **Features**: 25 statistical features (mean, std, min, max, range per sensor)
- **Training Data**: ASL-Sensor-Dataglove-Dataset (25 users, 40 gestures each)
- **Validation Method**: Leave-One-User-Out Cross-Validation
- **Validation Accuracy**: ~70-75%
- **Real-World Performance**: 85-95% with calibrated glove
- **Inference Time**: 20-40ms
- **Model Size**: ~2-5MB

---

## Deployment

The API is deployed on a home server using Docker Compose with Cloudflare tunnel.

### Quick Deploy (Windows)

```powershell
# From Windows, run automated deployment
.\deploy.ps1
```

This script:
1. Uploads files via SCP
2. Copies ML model to server
3. Builds Docker image
4. Starts service
5. Shows logs

### Manual Deployment

```bash
# SSH to server
ssh user@server

# Navigate to directory
cd /opt/stack/asl-ml-server

# Pull latest code
sudo git pull origin main

# Rebuild and restart
sudo docker compose down
sudo docker compose up -d --build

# Check logs
sudo docker compose logs -f asl-ml-api

# Check status
sudo docker compose ps
```

---

## Response Codes

| Code | Description |
|------|-------------|
| 200 | Success - Prediction completed |
| 401 | Unauthorized - Missing or invalid API key |
| 403 | Forbidden - Invalid API key |
| 422 | Validation Error - Invalid input format |
| 429 | Too Many Requests - Rate limit exceeded |
| 500 | Internal Server Error - Prediction failed |
| 503 | Service Unavailable - Model not loaded |

---

## Error Handling

All errors return JSON with detail message:

```json
{
  "detail": "Invalid API key"
}
```

Common errors:
- `"API Key missing. Please provide an X-API-Key header."`
- `"Invalid API Key."`
- `"Rate limit exceeded. Try again in X seconds."`
- `"Invalid input format"`

---

## Monitoring

### Health Check
```bash
curl https://api.ybilgin.com/health
```

### Statistics
```bash
curl -H "X-API-Key: your-key" https://api.ybilgin.com/stats
```

### Server Logs
```bash
sudo docker compose logs -f asl-ml-api
```

---

## Development

### Local Setup

```bash
# Clone repository
git clone <repository-url>
cd ASL-ML-Inference-API

# Create virtual environment
python3 -m venv venv
source venv/bin/activate  # Linux/Mac
# or
venv\Scripts\activate  # Windows

# Install dependencies
pip install -r requirements.txt

# Set environment variables
cp .env.example .env
# Edit .env with your configuration

# Run development server
uvicorn app.main:app --reload --host 0.0.0.0 --port 8000
```

### Testing

```bash
# Health check
curl http://localhost:8000/health

# Test prediction
curl -X POST http://localhost:8000/predict \
  -H "X-API-Key: your-test-key" \
  -H "Content-Type: application/json" \
  -d '{"flex_sensors": [[512, 678, 345, 890, 234]]}'
```

---

## Documentation

- **SECURITY_SETUP.md**: API key generation and security configuration
- **PROJECT_STATE.md**: Complete project documentation
- **README.md**: This file

---

## Support

### Get Help

- **API Issues**: Check `/docs` for interactive testing
- **Email**: support@ybilgin.com
- **GitHub**: https://github.com/Yigitalp02

### Contributing

Contributions welcome! Areas needing help:
- Support for more ASL letters
- Improved model accuracy
- Performance optimizations
- Additional language support

---

## License

MIT License - Part of Computer Science Graduation Project

**Author**: Yigit Alp Bilgin  
**Year**: 2026

For more information, visit: [https://api.ybilgin.com/docs](https://api.ybilgin.com/docs)
