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

@router.post("/predict/risk/{user_id}")
async def predict_student_risk(user_id: str, current_user: dict = Depends(require_role([RoleEnum.faculty, RoleEnum.admin]))):
    """
    Returns XGBoost risk prediction alongside SHAP human-readable explanations.
    """
    if not model or not explainer:
        raise HTTPException(status_code=503, detail="Prediction engine unavailable. Please train the model first.")

    # In production, dynamically query MongoDB to build this feature vector.
    # We are simulating the extracted features for this specific user.
    features = pd.DataFrame([{
        "attendance_rate": 0.65,
        "late_submissions": 4,
        "avg_score": 58.5,
        "active_ws_sessions": 12
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