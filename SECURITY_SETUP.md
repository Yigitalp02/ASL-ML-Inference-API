# API Security Setup Guide

This guide explains how to enable and use API key authentication and rate limiting for your ASL ML API.

---

## Security Features Added

1. **API Key Authentication**: Protects endpoints from unauthorized access
2. **Rate Limiting**: Limits requests to 100/minute per IP address
3. **Request Logging**: Tracks all API usage
4. **Response Headers**: Shows remaining rate limit

---

## Setup on Server

### Step 1: Generate API Keys

Generate secure random API keys:

```bash
# Generate a random API key
openssl rand -hex 32
# Example output: a3d8f7e2b1c9d4e5f6a7b8c9d0e1f2a3b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9

# Generate another one for your mobile app
openssl rand -hex 32
```

### Step 2: Configure Environment Variables

Edit your docker-compose.yml or set environment variables:

```bash
# On your server
cd /opt/stack

# Edit docker-compose.yml
sudo nano docker-compose.yml
```

Add the environment variables to the `asl-ml-api` service:

```yaml
asl-ml-api:
  build: ./asl-ml-server
  environment:
    - MODEL_PATH=/models/rf_asl_15letters.pkl
    - POSTGRES_HOST=asl-postgres
    - POSTGRES_DB=asl_predictions
    # API Security
    - API_KEYS=your-desktop-key-here,your-mobile-key-here,your-friend-key-here
    - RATE_LIMIT_REQUESTS=100
```

**Multiple API Keys**: Separate with commas (no spaces)

**Example:**
```yaml
- API_KEYS=a3d8f7e2b1c9d4e5f6a7b8c9d0e1f2a3,b4c5d6e7f8a9b0c1d2e3f4a5b6c7d8e9
```

### Step 3: Rebuild and Restart

```bash
# Rebuild with new code
sudo docker compose build asl-ml-api

# Restart
sudo docker compose up -d asl-ml-api

# Check logs
sudo docker compose logs -f asl-ml-api
```

You should see:
```
ASL Recognition API Starting...
Version: 1.1.0 (with authentication)
Authentication: Enabled
Rate Limit: 100 requests/minute
```

---

## Using the API with Authentication

### Python

```python
import requests

API_KEY = "your-api-key-here"
API_URL = "https://api.ybilgin.com/predict"

headers = {
    "X-API-Key": API_KEY,
    "Content-Type": "application/json"
}

data = {
    "flex_sensors": [[512, 678, 345, 890, 234]],
    "device_id": "python-client"
}

response = requests.post(API_URL, json=data, headers=headers)

if response.status_code == 200:
    result = response.json()
    print(f"Predicted: {result['letter']}")
    print(f"Confidence: {result['confidence']:.2%}")
    
    # Check rate limit
    remaining = response.headers.get('X-RateLimit-Remaining')
    print(f"Requests remaining: {remaining}")
elif response.status_code == 401:
    print("Error: Missing API key")
elif response.status_code == 403:
    print("Error: Invalid API key")
elif response.status_code == 429:
    print("Error: Rate limit exceeded")
else:
    print(f"Error: {response.json()}")
```

### JavaScript

```javascript
const API_KEY = 'your-api-key-here';
const API_URL = 'https://api.ybilgin.com/predict';

const headers = {
  'X-API-Key': API_KEY,
  'Content-Type': 'application/json'
};

const data = {
  flex_sensors: [[512, 678, 345, 890, 234]],
  device_id: 'js-client'
};

fetch(API_URL, {
  method: 'POST',
  headers: headers,
  body: JSON.stringify(data)
})
.then(response => {
  // Check rate limit
  console.log('Remaining:', response.headers.get('X-RateLimit-Remaining'));
  return response.json();
})
.then(result => {
  console.log('Predicted:', result.letter);
  console.log('Confidence:', result.confidence);
})
.catch(error => {
  console.error('Error:', error);
});
```

### Rust (Tauri)

```rust
use reqwest;
use serde::{Deserialize, Serialize};

#[derive(Serialize)]
struct PredictionRequest {
    flex_sensors: Vec<Vec<f32>>,
    device_id: String,
}

async fn predict_with_auth(
    sensor_data: Vec<Vec<f32>>,
    api_key: &str
) -> Result<String, reqwest::Error> {
    let client = reqwest::Client::new();
    
    let response = client
        .post("https://api.ybilgin.com/predict")
        .header("X-API-Key", api_key)
        .json(&PredictionRequest {
            flex_sensors: sensor_data,
            device_id: "tauri-app".to_string(),
        })
        .send()
        .await?;
    
    // Check rate limit
    if let Some(remaining) = response.headers().get("x-ratelimit-remaining") {
        println!("Requests remaining: {:?}", remaining);
    }
    
    let result: serde_json::Value = response.json().await?;
    Ok(result["letter"].as_str().unwrap().to_string())
}
```

### cURL

```bash
# With API key
curl -X POST "https://api.ybilgin.com/predict" \
  -H "X-API-Key: your-api-key-here" \
  -H "Content-Type: application/json" \
  -d '{
    "flex_sensors": [[512, 678, 345, 890, 234]],
    "device_id": "curl-test"
  }'

# Check health (no API key needed)
curl https://api.ybilgin.com/health
```

---

## Managing API Keys

### Give API Key to Users

1. Generate a key: `openssl rand -hex 32`
2. Add it to `API_KEYS` environment variable
3. Restart the service
4. Send the key to the user securely (email, encrypted message, etc.)

### Revoke an API Key

1. Remove it from `API_KEYS` environment variable
2. Restart the service
3. The key will immediately stop working

### Rotate API Keys

```bash
# 1. Generate new keys
NEW_KEY=$(openssl rand -hex 32)

# 2. Add new keys while keeping old ones
sudo nano /opt/stack/docker-compose.yml
# Add: API_KEYS=old-key1,old-key2,NEW_KEY

# 3. Restart
sudo docker compose up -d asl-ml-api

# 4. Update clients to use new keys

# 5. Remove old keys after clients are updated
# Edit docker-compose.yml, remove old keys
# Restart again
```

---

## Rate Limiting

### Current Limits

- **100 requests per minute** per IP address
- Counter resets every 60 seconds
- Applies to all endpoints except `/health` and `/`

### Check Your Rate Limit

Response headers show your status:
- `X-RateLimit-Limit`: Total allowed (100)
- `X-RateLimit-Remaining`: Requests left
- `X-RateLimit-Reset`: Unix timestamp when counter resets

### Adjust Rate Limit

In `docker-compose.yml`:

```yaml
environment:
  - RATE_LIMIT_REQUESTS=200  # Increase to 200 requests/min
```

---

## Backward Compatibility

### Disable Authentication (Not Recommended)

If you need to disable authentication temporarily:

```yaml
environment:
  - API_KEYS=  # Empty = no authentication
```

**Warning**: This makes your API publicly accessible!

---

## Monitoring

### Check Who's Using the API

```sql
-- Connect to database
docker exec -it asl-postgres psql -U asl_user -d asl_predictions

-- Recent predictions by device
SELECT device_id, COUNT(*) as count, AVG(confidence) as avg_conf
FROM predictions 
WHERE predicted_at > NOW() - INTERVAL '1 hour'
GROUP BY device_id 
ORDER BY count DESC;

-- Usage over time
SELECT 
    DATE_TRUNC('hour', predicted_at) as hour,
    COUNT(*) as predictions
FROM predictions 
WHERE predicted_at > NOW() - INTERVAL '24 hours'
GROUP BY hour 
ORDER BY hour DESC;
```

### View Logs

```bash
# Real-time logs
sudo docker compose logs -f asl-ml-api

# Filter for authentication errors
sudo docker compose logs asl-ml-api | grep -i "invalid\|unauthorized"

# Filter for rate limit hits
sudo docker compose logs asl-ml-api | grep -i "rate limit"
```

---

## Testing

### Test Valid API Key

```bash
curl -X POST "https://api.ybilgin.com/predict" \
  -H "X-API-Key: your-valid-key-here" \
  -H "Content-Type: application/json" \
  -d '{"flex_sensors": [[512, 678, 345, 890, 234]]}'
# Should return 200 OK with prediction
```

### Test Invalid API Key

```bash
curl -X POST "https://api.ybilgin.com/predict" \
  -H "X-API-Key: invalid-key" \
  -H "Content-Type: application/json" \
  -d '{"flex_sensors": [[512, 678, 345, 890, 234]]}'
# Should return 403 Forbidden
```

### Test Missing API Key

```bash
curl -X POST "https://api.ybilgin.com/predict" \
  -H "Content-Type: application/json" \
  -d '{"flex_sensors": [[512, 678, 345, 890, 234]]}'
# Should return 401 Unauthorized
```

### Test Rate Limit

```bash
# Send 101 requests quickly
for i in {1..101}; do
  curl -X POST "https://api.ybilgin.com/predict" \
    -H "X-API-Key: your-key" \
    -H "Content-Type: application/json" \
    -d '{"flex_sensors": [[512, 678, 345, 890, 234]]}'
  echo "Request $i"
done
# Last request should return 429 Rate Limit Exceeded
```

---

## Best Practices

1. **Keep API Keys Secret**: Never commit them to Git
2. **Use Different Keys**: One key per client/user
3. **Rotate Keys Regularly**: Change keys every 3-6 months
4. **Monitor Usage**: Check logs for suspicious activity
5. **Set Appropriate Limits**: Adjust rate limits based on your needs
6. **Use HTTPS**: Always use encrypted connections (already enabled with Cloudflare)

---

## Troubleshooting

### "Authentication: Disabled" in logs

- Check `API_KEYS` environment variable is set
- Make sure there are no extra spaces
- Rebuild and restart the container

### Clients getting 401/403 errors

- Verify API key is correct
- Check for typos in header name (`X-API-Key`)
- Ensure key is in `API_KEYS` environment variable

### Rate limit too restrictive

- Increase `RATE_LIMIT_REQUESTS` in environment
- Consider implementing API key-specific limits
- Use caching on client side to reduce requests

---

## Support

For questions or issues:
- Email: support@ybilgin.com
- Check logs: `sudo docker compose logs asl-ml-api`
- Test health: `curl https://api.ybilgin.com/health`

