# ScholarLab/backend/app/services/analytics.py
import joblib
import pandas as pd
import os
import logging

logger = logging.getLogger(__name__)

MODEL_PATH = os.path.join(os.path.dirname(__file__), "../ml/models/xgboost_risk_model.joblib")

# Load model into memory during module initialization
try:
    risk_model = joblib.load(MODEL_PATH)
    logger.info("XGBoost Risk Model successfully loaded into memory.")
except Exception as e:
    logger.error(f"Failed to load ML model at {MODEL_PATH}. Did you run the training script? Error: {e}")
    risk_model = None

async def predict_student_risk(
    attendance_rate: float, 
    avg_arrival_delay_mins: float, 
    curriculum_engagement_score: float, 
    spatial_anomalies: int, 
    biometric_failures: int
) -> dict:
    """
    Runs real-time inference on a student's behavioral telemetry.
    Returns the risk probability and a human-readable classification.
    """
    if not risk_model:
        return {"error": "Predictive model is currently unavailable."}

    # Construct the feature vector exactly as the model was trained
    features = pd.DataFrame([{
        "attendance_rate": attendance_rate,
        "avg_arrival_delay_mins": avg_arrival_delay_mins,
        "curriculum_engagement_score": curriculum_engagement_score,
        "spatial_anomalies": spatial_anomalies,
        "biometric_failures": biometric_failures
    }])

    # Predict probabilities: [Prob_Safe, Prob_At_Risk]
    probabilities = risk_model.predict_proba(features)[0]
    risk_probability = float(probabilities[1]) * 100  # Convert to percentage
    
    # Determine risk tier
    if risk_probability >= 75.0:
        tier = "High Risk"
    elif risk_probability >= 40.0:
        tier = "Moderate Risk"
    else:
        tier = "Safe"

    return {
        "risk_score_percentage": round(risk_probability, 1),
        "classification": tier,
        "telemetry_used": features.to_dict(orient="records")[0]
    }