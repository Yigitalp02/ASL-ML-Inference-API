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

# ── Feature extraction ────────────────────────────────────────────────────────
# Supports three model formats in priority order:
#   v2_gravity_cascade : Stage1=25 flex features, Stage2=6 gravity features
#   two-stage (prof)   : Stage1=25 flex features, Stage2=29 flex+mean(IMU)
#   legacy single      : 45 features (5 stats x 9 channels)

def _safe_stats(v: np.ndarray):
    v = v[~np.isnan(v)].astype(float)
    if len(v) == 0:
        return 0.0, 0.0, 0.0, 0.0, 0.0
    return (float(np.mean(v)),
            float(np.std(v)) if len(v) >= 2 else 0.0,
            float(np.min(v)),
            float(np.max(v)),
            float(np.max(v) - np.min(v)) if len(v) > 1 else 0.0)

def extract_flex_features(window: np.ndarray) -> np.ndarray:
    """25 features — flex channels 0-4 only. IMU ignored."""
    feats = []
    for i in range(5):
        feats.extend(_safe_stats(window[:, i]))
    return np.array(feats, dtype=np.float64)

def extract_gravity_features(window: np.ndarray) -> np.ndarray:
    """6 yaw-invariant gravity features for v2 Stage 2.
    fwd_z   = 2*(qx*qz + qw*qy)   — fingers up/down tilt
    up_z    = 1 - 2*(qx^2 + qy^2) — back-of-hand up/down tilt
    right_z = 2*(qy*qz - qw*qx)   — wrist roll (P vs Q vs L)
    """
    if window.shape[1] >= 9:
        qw = window[:, 5].astype(float)
        qx = window[:, 6].astype(float)
        qy = window[:, 7].astype(float)
        qz = window[:, 8].astype(float)
    else:
        qw = np.ones(len(window))
        qx = qy = qz = np.zeros(len(window))
    fwd_z   = 2.0 * (qx * qz + qw * qy)
    up_z    = 1.0 - 2.0 * (qx**2 + qy**2)
    right_z = 2.0 * (qy * qz - qw * qx)
    return np.array([
        float(np.mean(fwd_z)),   float(np.std(fwd_z)),
        float(np.mean(up_z)),    float(np.std(up_z)),
        float(np.mean(right_z)), float(np.std(right_z)),
    ], dtype=np.float64)

def extract_stage2_features(window: np.ndarray) -> np.ndarray:
    """29 features — 25 flex + mean(qw,qx,qy,qz). Used by professor's format."""
    feats = list(extract_flex_features(window))
    if window.shape[1] >= 9:
        for i in range(5, 9):
            v = window[:, i].astype(float)
            v = v[~np.isnan(v)]
            feats.append(float(np.mean(v)) if len(v) > 0 else (1.0 if i == 5 else 0.0))
    else:
        feats.extend([1.0, 0.0, 0.0, 0.0])
    return np.array(feats, dtype=np.float64)

def extract_features_from_window(window: np.ndarray) -> np.ndarray:
    """Legacy: 45 features (5 stats x 9 channels). Backward-compatible."""
    if window.shape[1] < 9:
        pad = np.zeros((window.shape[0], 9 - window.shape[1]))
        pad[:, 0] = 1.0
        window = np.hstack([window, pad])
    features = []
    for i in range(9):
        v = window[:, i]
        features.extend([float(np.mean(v)), float(np.std(v)),
                         float(np.min(v)),  float(np.max(v)),
                         float(np.max(v) - np.min(v))])
    return np.array(features, dtype=np.float64)


# Request/Response models
class SensorData(BaseModel):
    """
    Normalized sensor data from glove (0.0 - 1.0 per finger).
    Can accept either:
    1. A window of samples (preferred, for best accuracy): List[List[float]]
    2. A single sample (quick mode): List[float]
    imu: optional current quaternion [w, x, y, z] for v2 Stage 2 disambiguation.
    """
    flex_sensors: Union[List[List[float]], List[float]] = Field(
        ...,
        description="Normalized sensor readings. Either [[f1..f5], ...] for windowed or [f1..f5] for single sample."
    )
    imu: Optional[List[float]] = Field(
        default=None,
        description="Current IMU quaternion [w, x, y, z] — used by v2 model for orientation disambiguation."
    )
    timestamp: Optional[float] = Field(default_factory=time.time)
    device_id: Optional[str] = Field(default="desktop-app", description="Source device identifier")

    class Config:
        json_schema_extra = {
            "example": {
                "flex_sensors": [[0.02, 0.68, 0.78, 0.65, 0.68], [0.02, 0.69, 0.77, 0.64, 0.67]],
                "imu": [1.0, 0.0, 0.0, 0.0],
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
    # Load best available model — prefer 21-letter IMU model, fall back to old 15-letter models
    model_path = os.getenv("MODEL_PATH", "/models/rf_asl_21letters_imu.pkl")

    if not Path(model_path).exists():
        logger.warning(f"Model not found at {model_path}, trying alternatives...")
        alternative_paths = [
            "/models/rf_asl_v2_gravity_cascade.pkl",
            "/opt/stack/ai-models/rf_asl_v2_gravity_cascade.pkl",
            "/models/rf_asl_21letters_imu.pkl",
            "/opt/stack/ai-models/rf_asl_21letters_imu.pkl",
            "/models/rf_asl_15letters_normalized_97pct_45feat_seed1_feb26.pkl",
            "/models/rf_asl_15letters_normalized_97pct_seed1_feb26.pkl",
            "/models/rf_asl_15letters_normalized_96pct_seed1.pkl",
            "/models/rf_asl_15letters_normalized.pkl",
            "/models/rf_asl_15letters.pkl",
            "/opt/stack/ai-models/rf_asl_15letters_normalized_97pct_seed1_feb26.pkl",
            "/opt/stack/ai-models/rf_asl_15letters_normalized_96pct_seed1.pkl",
            "/opt/stack/ai-models/rf_asl_15letters.pkl",
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
        sensor_array = np.array(sensor_data.flex_sensors, dtype=np.float64)

        # Check if it's windowed data or single sample
        if sensor_array.ndim == 1:
            # Single sample - convert to window with 1 sample
            sensor_array = sensor_array.reshape(1, -1)
        elif sensor_array.ndim == 2:
            # Already windowed data (multiple samples x 5 sensors)
            pass
        else:
            raise ValueError(f"Invalid sensor data shape: {sensor_array.shape}")

        # Clamp to 0-1 range (app sends normalized values)
        sensor_array = np.clip(sensor_array, 0.0, 1.0)

        # If IMU quaternion was sent, append it as columns so feature
        # extractors can read it from cols 5-8.
        if sensor_data.imu and len(sensor_data.imu) == 4:
            imu_cols = np.tile(sensor_data.imu, (sensor_array.shape[0], 1))
            sensor_array = np.hstack([sensor_array, imu_cols])

        model = model_manager.model
        prediction = None
        prob_dict  = {}
        confidence = 0.0

        # ── v2 gravity cascade ────────────────────────────────────────────────
        if isinstance(model, dict) and model.get("format") == "v2_gravity_cascade":
            s1   = model["stage_1_model"]
            f1   = extract_flex_features(sensor_array).reshape(1, -1)
            probs1 = s1.predict_proba(f1)[0]
            prediction = str(s1.predict(f1)[0])
            confidence = float(max(probs1))
            prob_dict  = {str(c): float(p) for c, p in zip(s1.classes_, probs1)}

            families  = model.get("families", {})
            s2_models = model.get("stage_2_models", {})
            fg = extract_gravity_features(sensor_array).reshape(1, -1)
            for fam_name, members in families.items():
                if prediction in members and fam_name in s2_models:
                    clf   = s2_models[fam_name]
                    p2    = clf.predict_proba(fg)[0]
                    prediction = str(clf.predict(fg)[0])
                    confidence = float(max(p2))
                    for c, p in zip(clf.classes_, p2):
                        prob_dict[str(c)] = float(p)
                    break

        # ── professor's two-stage cascade ─────────────────────────────────────
        elif isinstance(model, dict) and "stage_1_model" in model:
            s1 = model["stage_1_model"]
            f1 = extract_flex_features(sensor_array).reshape(1, -1)
            f2 = extract_stage2_features(sensor_array).reshape(1, -1)
            probs1 = s1.predict_proba(f1)[0]
            prediction = str(s1.predict(f1)[0])
            confidence = float(max(probs1))
            prob_dict  = {str(c): float(p) for c, p in zip(s1.classes_, probs1)}

            if "disamb_dgq" in model:
                for clf_key in ("disamb_dgq", "disamb_kp"):
                    clf = model.get(clf_key)
                    if clf and prediction in [str(c) for c in clf.classes_]:
                        p2 = clf.predict_proba(f2)[0]
                        prediction = str(clf.predict(f2)[0])
                        confidence = float(max(p2))
                        for c, p in zip(clf.classes_, p2):
                            prob_dict[str(c)] = float(p)
                        break
            elif "stage_2_model" in model:
                triggers = model.get("imu_trigger_letters") or model.get("trigger_letters", [])
                if prediction in triggers:
                    clf = model["stage_2_model"]
                    p2  = clf.predict_proba(f2)[0]
                    prediction = str(clf.predict(f2)[0])
                    confidence = float(max(p2))
                    for c, p in zip(clf.classes_, p2):
                        prob_dict[str(c)] = float(p)

        # ── legacy single model (45 features) ─────────────────────────────────
        else:
            features = extract_features_from_window(sensor_array).reshape(1, -1)
            prediction = str(model.predict(features)[0])
            if hasattr(model, "predict_proba"):
                probs = model.predict_proba(features)[0]
                prob_dict  = {str(c): float(p) for c, p in zip(model.classes_, probs)}
                confidence = float(max(probs))
            else:
                prob_dict  = {str(prediction): 1.0}
                confidence = 1.0
        
        processing_time = (time.time() - start_time) * 1000  # Convert to ms

        # Store in background (store flex features for DB — always 25 values)
        flex_feats = extract_flex_features(sensor_array).tolist()
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
                        flex_feats,
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

