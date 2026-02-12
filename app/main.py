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

# FastAPI app
app = FastAPI(
    title="ASL ML API",
    description="Real-time sign language recognition API",
    version="1.0.0"
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
@app.get("/health", response_model=HealthResponse)
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
@app.post("/predict", response_model=PredictionResponse)
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
@app.get("/stats")
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
@app.get("/")
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

