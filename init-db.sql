-- Database initialization for ASL ML API
-- Creates tables for storing predictions and analytics

-- Create predictions table
CREATE TABLE IF NOT EXISTS predictions (
    id SERIAL PRIMARY KEY,
    letter VARCHAR(5) NOT NULL,
    confidence FLOAT NOT NULL,
    sensor_data FLOAT[] NOT NULL,
    device_id VARCHAR(100) DEFAULT 'unknown',
    processing_time_ms FLOAT,
    predicted_at TIMESTAMP DEFAULT NOW(),
    created_at TIMESTAMP DEFAULT NOW()
);

-- Create indexes for common queries
CREATE INDEX IF NOT EXISTS idx_predictions_letter ON predictions(letter);
CREATE INDEX IF NOT EXISTS idx_predictions_predicted_at ON predictions(predicted_at DESC);
CREATE INDEX IF NOT EXISTS idx_predictions_device_id ON predictions(device_id);
CREATE INDEX IF NOT EXISTS idx_predictions_confidence ON predictions(confidence);

-- Create view for daily statistics
CREATE OR REPLACE VIEW daily_stats AS
SELECT 
    DATE(predicted_at) as date,
    COUNT(*) as total_predictions,
    AVG(confidence) as avg_confidence,
    AVG(processing_time_ms) as avg_processing_time_ms,
    COUNT(DISTINCT device_id) as unique_devices
FROM predictions
GROUP BY DATE(predicted_at)
ORDER BY date DESC;

-- Create view for letter frequency
CREATE OR REPLACE VIEW letter_frequency AS
SELECT 
    letter,
    COUNT(*) as count,
    AVG(confidence) as avg_confidence,
    MIN(confidence) as min_confidence,
    MAX(confidence) as max_confidence
FROM predictions
GROUP BY letter
ORDER BY count DESC;

-- Grant permissions (if needed)
GRANT ALL PRIVILEGES ON DATABASE asl_predictions TO asl_user;
GRANT ALL PRIVILEGES ON ALL TABLES IN SCHEMA public TO asl_user;
GRANT ALL PRIVILEGES ON ALL SEQUENCES IN SCHEMA public TO asl_user;

