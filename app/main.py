"""
ASL ML Inference API
Fast prediction endpoint for IoT sign language glove
Optimized for low latency (<50ms response time)
"""
from fastapi import FastAPI, HTTPException, Request
from fastapi.middleware.cors import CORSMiddleware
from pydantic import BaseModel, Field
from typing import List, Optional, Dict, Union
import joblib
import numpy as np
import logging
from datetime import datetime
from pathlib import Path
import asyncpg
import os
import time

# Logging setup
logging.basicConfig(
    level=logging.INFO,
    format='%(asctime)s - %(name)s - %(levelname)s - %(message)s'
)
logger = logging.getLogger(__name__)

# FastAPI app with comprehensive documentation
app = FastAPI(
    title="ASL Sign Language Recognition API",
    description="""
    **Real-time American Sign Language Recognition API**
    
    This API provides machine learning-powered ASL letter recognition from smart glove sensor data.
    
    ## Features
    
    - **Fast Predictions**: <50ms inference time
    - **15 ASL Letters**: A, B, C, D, E, F, I, K, O, S, T, V, W, X, Y  
    - **Flexible Input**: Accepts single samples or windowed data
    - **High Confidence**: 85-95% accuracy with real glove data
    - **Analytics**: Prediction history and statistics
    - **PostgreSQL Logging**: Stores all predictions for analysis
    
    ## How It Works
    
    1. **Collect sensor data** from your smart glove (5 flex sensors)
    2. **Send data** to `/predict` endpoint
    3. **Receive prediction** with letter and confidence score
    
    ## Quick Start
    
    ### Try it now:
    1. Click on **`POST /predict`** below
    2. Click **"Try it out"**
    3. Use the example request or modify it
    4. Click **"Execute"**
    5. See your prediction result!
    
    ## Input Formats
    
    The API accepts two types of input:
    
    ### Option 1: Windowed Data (Recommended for best accuracy)
    ```json
    {
      "flex_sensors": [
        [512, 678, 345, 890, 234],
        [510, 680, 344, 891, 235],
        [511, 679, 346, 892, 236]
      ]
    }
    ```
    
    ### Option 2: Single Sample (Quick mode)
    ```json
    {
      "flex_sensors": [512, 678, 345, 890, 234]
    }
    ```
    
    ## API Endpoints
    
    - **`POST /predict`** - Make a prediction
    - **`GET /health`** - Check API status
    - **`GET /stats`** - View prediction statistics
    - **`GET /`** - API information
    
    ## Integration Example
    
    ```python
    import requests
    
    # Prepare data
    data = {
        "flex_sensors": [[512, 678, 345, 890, 234]],
        "device_id": "my-glove"
    }
    
    # Make request
    response = requests.post(
        "https://api.ybilgin.com/predict",
        json=data
    )
    
    # Get result
    result = response.json()
    print(f"Predicted: {result['letter']}")
    print(f"Confidence: {result['confidence']:.2%}")
    ```
    
    ## Support
    
    For questions or issues:
    - Email: support@ybilgin.com
    - GitHub: https://github.com/Yigitalp02
    
    ## Notes
    
    - All predictions are logged for quality improvement
    - Response times are typically 20-40ms
    - The model was trained on 25 users' data
    """,
    version="1.0.0",
    contact={
        "name": "IoT Sign Language Team",
        "email": "support@ybilgin.com",
        "url": "https://github.com/Yigitalp02"
    },
    license_info={
        "name": "MIT License",
        "url": "https://opensource.org/licenses/MIT"
    },
    docs_url="/docs",
    redoc_url="/redoc"
)

# CORS - allow desktop app to connect
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],  # In production, restrict to your desktop app
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

# Global model storage
class ModelManager:
    def __init__(self):
        self.model = None
        self.model_name = None
        self.loaded_at = None
        
    def load_model(self, model_path: str):
        """Load ML model from disk"""
        try:
            logger.info(f"Loading model from {model_path}")
            self.model = joblib.load(model_path)
            self.model_name = Path(model_path).stem
            self.loaded_at = datetime.now()
            logger.info(f"Model loaded: {self.model_name}")
            return True
        except Exception as e:
            logger.error(f"Failed to load model: {e}")
            return False

model_manager = ModelManager()

# Database connection pool
db_pool = None

async def get_db_pool():
    """Initialize PostgreSQL connection pool"""
    global db_pool
    if db_pool is None:
        db_host = os.getenv("POSTGRES_HOST", "postgres")
        db_port = int(os.getenv("POSTGRES_PORT", "5432"))
        db_name = os.getenv("POSTGRES_DB", "asl_predictions")
        db_user = os.getenv("POSTGRES_USER", "asl_user")
        db_pass = os.getenv("POSTGRES_PASSWORD", "asl_password")
        
        try:
            db_pool = await asyncpg.create_pool(
                host=db_host,
                port=db_port,
                database=db_name,
                user=db_user,
                password=db_pass,
                min_size=2,
                max_size=10
            )
            logger.info("Database pool created")
        except Exception as e:
            logger.error(f"Database connection failed: {e}")
            db_pool = None
    return db_pool

# Feature extraction function (matches training script)
def extract_features_from_window(window: np.ndarray) -> np.ndarray:
    """
    Extract 25 statistical features from a window of sensor samples.
    For each of the 5 flex sensors, computes: mean, std, min, max, range
    
    Args:
        window: numpy array of shape (n_samples, 5) where n_samples >= 1
        
    Returns:
        numpy array of 25 features
    """
    features = []
    
    for finger_idx in range(5):
        finger_values = window[:, finger_idx]
        features.extend([
            np.mean(finger_values),
            np.std(finger_values),
            np.min(finger_values),
            np.max(finger_values),
            np.max(finger_values) - np.min(finger_values)  # range
        ])
    
    return np.array(features)


# Request/Response models
class SensorData(BaseModel):
    """
    Raw sensor data from glove.
    Can accept either:
    1. A window of samples (preferred, for best accuracy): List[List[float]] 
    2. A single sample (quick mode): List[float]
    """
    flex_sensors: Union[List[List[float]], List[float]] = Field(
        ..., 
        description="Flex sensor readings. Either [[f1,f2,f3,f4,f5], ...] for windowed data, or [f1,f2,f3,f4,f5] for single sample"
    )
    timestamp: Optional[float] = Field(default_factory=time.time)
    device_id: Optional[str] = Field(default="desktop-app", description="Source device identifier")
    
    class Config:
        json_schema_extra = {
            "example": {
                "flex_sensors": [[512.3, 678.1, 345.9, 890.2, 234.5], [510.1, 680.5, 344.2, 891.3, 235.8]],
                "timestamp": 1234567890.123,
                "device_id": "glove-001"
            }
        }

class PredictionResponse(BaseModel):
    """Prediction result"""
    letter: str = Field(..., description="Predicted ASL letter")
    confidence: float = Field(..., description="Confidence score (0-1)")
    all_probabilities: Dict[str, float] = Field(..., description="All class probabilities")
    processing_time_ms: float = Field(..., description="Inference time in milliseconds")
    model_name: str = Field(..., description="Model used for prediction")
    timestamp: float = Field(..., description="Server timestamp")

class HealthResponse(BaseModel):
    """API health status"""
    status: str
    model_loaded: bool
    model_name: Optional[str]
    model_loaded_at: Optional[str]
    database_connected: bool
    uptime_seconds: float

# Startup event
@app.on_event("startup")
async def startup_event():
    """Load model on startup"""
    # Try to load model
    model_path = os.getenv("MODEL_PATH", "/models/rf_asl_15letters.pkl")
    
    if not Path(model_path).exists():
        logger.warning(f"Model not found at {model_path}, trying alternatives...")
        # Try alternative paths
        alternative_paths = [
            "/models/rf_asl_calibrated.pkl",
            "/opt/stack/ai-models/rf_asl_15letters.pkl",
            "./models/rf_asl_15letters.pkl"
        ]
        for alt_path in alternative_paths:
            if Path(alt_path).exists():
                model_path = alt_path
                break
    
    if Path(model_path).exists():
        model_manager.load_model(model_path)
    else:
        logger.error("No model found! Please mount model to /models/")
    
    # Initialize database pool
    await get_db_pool()

# Shutdown event
@app.on_event("shutdown")
async def shutdown_event():
    """Cleanup on shutdown"""
    global db_pool
    if db_pool:
        await db_pool.close()
        logger.info("Database pool closed")

# Health check endpoint
@app.get(
    "/health",
    response_model=HealthResponse,
    tags=["System"],
    summary="Health Check",
    description="""
    Check if the API and ML model are running properly.
    
    Returns:
    - **status**: "healthy" or "degraded"
    - **model_loaded**: Whether the ML model is loaded
    - **model_name**: Name of the loaded model
    - **database_connected**: PostgreSQL connection status
    - **uptime_seconds**: How long the API has been running
    
    **Use this endpoint** to verify the API is ready before making predictions.
    """,
    responses={
        200: {
            "description": "API is operational",
            "content": {
                "application/json": {
                    "example": {
                        "status": "healthy",
                        "model_loaded": True,
                        "model_name": "rf_asl_15letters",
                        "model_loaded_at": "2026-02-18T16:30:00",
                        "database_connected": True,
                        "uptime_seconds": 123.45
                    }
                }
            }
        }
    }
)
async def health_check():
    """Check API health status"""
    pool = await get_db_pool()
    
    return HealthResponse(
        status="healthy" if model_manager.model is not None else "degraded",
        model_loaded=model_manager.model is not None,
        model_name=model_manager.model_name,
        model_loaded_at=model_manager.loaded_at.isoformat() if model_manager.loaded_at else None,
        database_connected=pool is not None,
        uptime_seconds=time.time() - (model_manager.loaded_at.timestamp() if model_manager.loaded_at else time.time())
    )

# Prediction endpoint
@app.post(
    "/predict",
    response_model=PredictionResponse,
    tags=["Prediction"],
    summary="Predict ASL Sign",
    description="""
    Predict ASL letter from smart glove sensor data.
    
    ## Input Format
    
    Send 5 flex sensor readings (one per finger). You can send either:
    
    ### Windowed Data (Recommended)
    Multiple samples for better accuracy:
    ```json
    {
      "flex_sensors": [
        [512, 678, 345, 890, 234],
        [510, 680, 344, 891, 235],
        [511, 679, 346, 892, 236]
      ],
      "device_id": "my-glove"
    }
    ```
    
    ### Single Sample (Quick Mode)
    One sample for faster response:
    ```json
    {
      "flex_sensors": [512, 678, 345, 890, 234],
      "device_id": "my-glove"
    }
    ```
    
    ## Output
    
    Returns:
    - **letter**: Predicted ASL letter (A-Y, 15 letters total)
    - **confidence**: Score from 0-1 (higher is better)
    - **all_probabilities**: Confidence for all possible letters
    - **processing_time_ms**: How long the prediction took
    - **model_name**: Which ML model was used
    
    ## Tips
    
    - Send **100-150 samples** (2-3 seconds at 50Hz) for best accuracy
    - Ensure sensors are **calibrated** properly
    - Check **confidence score** - values >0.8 are very reliable
    
    ## Example Usage
    
    ```python
    import requests
    
    response = requests.post(
        "https://api.ybilgin.com/predict",
        json={
            "flex_sensors": [[512, 678, 345, 890, 234]],
            "device_id": "glove-001"
        }
    )
    
    result = response.json()
    print(f"Letter: {result['letter']}")
    print(f"Confidence: {result['confidence']:.2%}")
    ```
    """,
    responses={
        200: {
            "description": "Successful prediction",
            "content": {
                "application/json": {
                    "example": {
                        "letter": "A",
                        "confidence": 0.92,
                        "all_probabilities": {
                            "A": 0.92,
                            "S": 0.04,
                            "B": 0.02,
                            "C": 0.01
                        },
                        "processing_time_ms": 23.5,
                        "model_name": "rf_asl_15letters",
                        "timestamp": 1708268123.456
                    }
                }
            }
        },
        503: {
            "description": "Model not loaded",
            "content": {
                "application/json": {
                    "example": {"detail": "Model not loaded"}
                }
            }
        },
        500: {
            "description": "Prediction error",
            "content": {
                "application/json": {
                    "example": {"detail": "Prediction failed: Invalid sensor data"}
                }
            }
        }
    }
)
async def predict(sensor_data: SensorData):
    """
    Predict ASL letter from sensor data
    
    Optimized for <50ms response time
    """
    start_time = time.time()
    
    # Check if model is loaded
    if model_manager.model is None:
        raise HTTPException(status_code=503, detail="Model not loaded")
    
    try:
        # Convert sensor data to numpy array
        sensor_array = np.array(sensor_data.flex_sensors)
        
        # Check if it's windowed data or single sample
        if sensor_array.ndim == 1:
            # Single sample - convert to window with 1 sample
            # This gives less accurate results but still works
            sensor_array = sensor_array.reshape(1, -1)
        elif sensor_array.ndim == 2:
            # Already windowed data (multiple samples x 5 sensors)
            pass
        else:
            raise ValueError(f"Invalid sensor data shape: {sensor_array.shape}")
        
        # Extract 25 statistical features from the window
        features = extract_features_from_window(sensor_array).reshape(1, -1)
        
        # Validate feature count
        if features.shape[1] != 25:
            raise ValueError(f"Expected 25 features, got {features.shape[1]}")
        
        # Get prediction
        prediction = model_manager.model.predict(features)[0]
        
        # Get probabilities if available
        if hasattr(model_manager.model, 'predict_proba'):
            probabilities = model_manager.model.predict_proba(features)[0]
            classes = model_manager.model.classes_
            
            # Create probability dictionary
            prob_dict = {
                str(cls): float(prob) 
                for cls, prob in zip(classes, probabilities)
            }
            
            # Get confidence (max probability)
            confidence = float(max(probabilities))
        else:
            prob_dict = {str(prediction): 1.0}
            confidence = 1.0
        
        processing_time = (time.time() - start_time) * 1000  # Convert to ms
        
        # Log prediction to database (async, don't wait)
        # Store the extracted features (25 values) instead of raw sensor data for consistency
        app.state.last_prediction = {
            "letter": str(prediction),
            "confidence": confidence,
            "sensor_data": features[0].tolist(),  # Store the 25 features
            "timestamp": sensor_data.timestamp,
            "device_id": sensor_data.device_id,
            "processing_time_ms": processing_time
        }
        
        # Store in background
        pool = await get_db_pool()
        if pool:
            try:
                async with pool.acquire() as conn:
                    await conn.execute(
                        """
                        INSERT INTO predictions 
                        (letter, confidence, sensor_data, device_id, processing_time_ms, predicted_at)
                        VALUES ($1, $2, $3, $4, $5, NOW())
                        """,
                        str(prediction),
                        confidence,
                        features[0].tolist(),  # Store the 25 features
                        sensor_data.device_id,
                        processing_time
                    )
            except Exception as e:
                logger.warning(f"Failed to log prediction: {e}")
        
        return PredictionResponse(
            letter=str(prediction),
            confidence=confidence,
            all_probabilities=prob_dict,
            processing_time_ms=processing_time,
            model_name=model_manager.model_name,
            timestamp=time.time()
        )
        
    except Exception as e:
        logger.error(f"Prediction error: {e}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Prediction failed: {str(e)}")

# Statistics endpoint
@app.get(
    "/stats",
    tags=["Analytics"],
    summary="Get Prediction Statistics",
    description="""
    Get analytics about API usage and prediction performance.
    
    Returns statistics for:
    - Total predictions made
    - Average confidence (last 24 hours)
    - Average processing time (last hour)
    - Most predicted letters (last 24 hours)
    
    Useful for monitoring model performance and usage patterns.
    """,
    responses={
        200: {
            "description": "Statistics retrieved",
            "content": {
                "application/json": {
                    "example": {
                        "total_predictions": 1523,
                        "last_24h_avg_confidence": 0.87,
                        "last_1h_avg_processing_ms": 28.3,
                        "top_letters_24h": [
                            {"letter": "A", "count": 45},
                            {"letter": "S", "count": 38},
                            {"letter": "B", "count": 32}
                        ]
                    }
                }
            }
        }
    }
)
async def get_statistics():
    """Get prediction statistics"""
    pool = await get_db_pool()
    if not pool:
        raise HTTPException(status_code=503, detail="Database not available")
    
    try:
        async with pool.acquire() as conn:
            # Total predictions
            total = await conn.fetchval("SELECT COUNT(*) FROM predictions")
            
            # Average confidence
            avg_confidence = await conn.fetchval(
                "SELECT AVG(confidence) FROM predictions WHERE predicted_at > NOW() - INTERVAL '24 hours'"
            )
            
            # Letter distribution
            letter_dist = await conn.fetch(
                """
                SELECT letter, COUNT(*) as count 
                FROM predictions 
                WHERE predicted_at > NOW() - INTERVAL '24 hours'
                GROUP BY letter 
                ORDER BY count DESC 
                LIMIT 10
                """
            )
            
            # Average processing time
            avg_time = await conn.fetchval(
                "SELECT AVG(processing_time_ms) FROM predictions WHERE predicted_at > NOW() - INTERVAL '1 hour'"
            )
            
            return {
                "total_predictions": total,
                "last_24h_avg_confidence": float(avg_confidence) if avg_confidence else 0,
                "last_1h_avg_processing_ms": float(avg_time) if avg_time else 0,
                "top_letters_24h": [
                    {"letter": row["letter"], "count": row["count"]} 
                    for row in letter_dist
                ]
            }
    except Exception as e:
        logger.error(f"Stats error: {e}")
        raise HTTPException(status_code=500, detail=str(e))

# Root endpoint
@app.get(
    "/",
    tags=["Info"],
    summary="API Information",
    description="""
    Get basic information about the ASL Recognition API.
    
    Returns:
    - Service name and version
    - Available endpoints
    - Model status
    
    **Tip**: Visit `/docs` for interactive API documentation!
    """
)
async def root():
    """API information"""
    return {
        "service": "ASL ML Inference API",
        "version": "1.0.0",
        "status": "operational",
        "endpoints": {
            "predict": "POST /predict",
            "health": "GET /health",
            "stats": "GET /stats",
            "docs": "GET /docs"
        },
        "model": model_manager.model_name if model_manager.model else "not loaded"
    }

