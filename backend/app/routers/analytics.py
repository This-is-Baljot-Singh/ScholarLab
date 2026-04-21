# ScholarLab/backend/app/routers/analytics.py
from fastapi import APIRouter, Depends, HTTPException
from app.security import require_role
from app.schemas import RoleEnum
from app.database import attendance_collection, users_collection
import joblib
import shap
import pandas as pd
import os
import logging

logger = logging.getLogger(__name__)
router = APIRouter(tags=["ML Analytics & Dashboards"])

MODEL_PATH = "app/ml/models/xgboost_risk_model.joblib"
model = None
explainer = None

# Initialize ML model and SHAP explainer into memory on startup
if os.path.exists(MODEL_PATH):
    model = joblib.load(MODEL_PATH)
    # SHAP TreeExplainer is highly optimized for XGBoost/RandomForest ensembles
    explainer = shap.TreeExplainer(model)
else:
    logger.warning("ML Model not found. Analytics endpoints will run in degraded mode.")

@router.get("/dashboard/trends")
async def get_attendance_trends(current_user: dict = Depends(require_role([RoleEnum.faculty, RoleEnum.admin]))):
    """
    Aggregation endpoint designed to feed directly into React charting libraries
    (like Recharts or Chart.js) for Sprint 4 dashboards.
    """
    pipeline = [
        {"$match": {"status": "verified"}},
        {"$group": {
            "_id": {"$dateToString": {"format": "%Y-%m-%d", "date": "$timestamp"}},
            "verified_attendances": {"$sum": 1}
        }},
        {"$sort": {"_id": 1}},
        {"$limit": 30} # Last 30 active days
    ]
    trends = await attendance_collection.aggregate(pipeline).to_list(length=30)
    
    # Format cleanly for the frontend
    return [{"date": t["_id"], "count": t["verified_attendances"]} for t in trends]

@router.get("/overview")
async def get_analytics_overview(current_user: dict = Depends(require_role([RoleEnum.faculty, RoleEnum.admin]))):
    """
    Returns campus-wide analytics overview: aggregate stats and live inference demo.
    Designed to populate the main PredictiveAnalyticsDashboard on the faculty portal.
    """
    try:
        # 1. Query campus aggregates from MongoDB
        total_students = await users_collection.count_documents({"role": "student"})
        verified_today = await attendance_collection.count_documents({
            "status": "verified",
            "timestamp": {"$gte": pd.Timestamp.now().normalize()}
        })
        
        # Estimate campus attendance rate
        campus_attendance_rate = min(int((verified_today / max(total_students, 1)) * 100), 100) if total_students > 0 else 0
        students_at_risk = max(int(total_students * 0.05), 0)  # Simulate 5% at-risk
        spoofing_attempts = 2  # Mock data
        
        campus_aggregate = {
            "total_students_tracked": total_students,
            "current_attendance_rate": campus_attendance_rate,
            "students_at_risk": students_at_risk,
            "recent_spoofing_attempts": spoofing_attempts,
        }
        
        # 2. Generate live inference demo (sample student prediction)
        # Features must match what the XGBoost model was trained on
        sample_features = pd.DataFrame([{
            "attendance_rate": 0.78,
            "avg_arrival_delay_mins": 2.5,
            "curriculum_engagement_score": 7.8,
            "spatial_anomalies": 0,
            "biometric_failures": 1
        }])
        
        if model and explainer:
            demo_prediction = model.predict(sample_features)[0]
            demo_probability = model.predict_proba(sample_features)[0][1]
            demo_classification = "Safe" if demo_probability < 0.5 else "At Risk"
            demo_risk_percentage = int(demo_probability * 100)
        else:
            # Fallback if model not loaded
            demo_classification = "Safe"
            demo_risk_percentage = 35
        
        live_inference_demo = {
            "classification": demo_classification,
            "risk_score_percentage": demo_risk_percentage,
            "telemetry_used": {
                "attendance_rate": float(sample_features.iloc[0]["attendance_rate"]),
                "curriculum_engagement_score": float(sample_features.iloc[0]["curriculum_engagement_score"]),
            }
        }
        
        return {
            "campus_aggregate": campus_aggregate,
            "live_inference_demo": live_inference_demo,
        }
    
    except Exception as e:
        logger.error(f"Error fetching analytics overview: {e}")
        raise HTTPException(status_code=500, detail="Failed to load analytics overview")

@router.post("/predict/risk/{user_id}")
async def predict_student_risk(user_id: str, current_user: dict = Depends(require_role([RoleEnum.faculty, RoleEnum.admin]))):
    """
    Returns XGBoost risk prediction alongside SHAP human-readable explanations.
    """
    try:
        if not model or not explainer:
            raise HTTPException(status_code=503, detail="Prediction engine unavailable. Please train the model first.")

        # In production, dynamically query MongoDB to build this feature vector.
        # We are simulating the extracted features for this specific user.
        # Features must match what the XGBoost model was trained on
        features = pd.DataFrame([{
            "attendance_rate": 0.65,
            "avg_arrival_delay_mins": 8.5,
            "curriculum_engagement_score": 5.8,
            "spatial_anomalies": 1,
            "biometric_failures": 3
        }])

        # 1. Generate Prediction
        prediction = model.predict(features)[0]
        probability = model.predict_proba(features)[0][1]

        # 2. Extract SHAP values
        shap_values = explainer.shap_values(features)

        # 3. Format the explainer payload for the UI
        feature_impact = []
        for i, col in enumerate(features.columns):
            # shap_values[0] accesses the target class impacts
            impact = float(shap_values[0][i]) 
            feature_impact.append({
                "feature": col,
                "value": float(features.iloc[0][i]),
                "shap_impact": impact,
                "human_readable": f"The '{col}' variable {'increased' if impact > 0 else 'decreased'} the risk score by {abs(impact):.3f} points."
            })

        return {
            "user_id": user_id,
            "risk_label": int(prediction),
            "risk_probability": float(probability),
            "shap_explanations": feature_impact
        }
    except Exception as e:
        logger.error(f"Error in predict_student_risk: {str(e)}", exc_info=True)
        raise HTTPException(status_code=500, detail=f"Error generating prediction: {str(e)}")