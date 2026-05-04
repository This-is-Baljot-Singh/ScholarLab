"""
Risk Model: XGBoost-based predictive risk scoring with SHAP explainability.

Formula: y_hat_i_t = f_theta(x_i_t)

Predicts probability of student at risk of poor academic outcomes.

Features:
  x_i_t = [a_t, delta_a_t, c_t, f_late, days_since_start, ...]

Explainability:
  SHAP values show which features drive risk prediction
  Base value + feature contributions = final prediction
"""

import logging
from typing import Dict, List, Optional, Tuple, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import numpy as np
import joblib
import os

logger = logging.getLogger(__name__)

# Try to import optional dependencies
try:
    import xgboost as xgb
    XGBOOST_AVAILABLE = True
except ImportError:
    XGBOOST_AVAILABLE = False
    logger.warning("XGBoost not installed. Install with: pip install xgboost")

try:
    import shap
    SHAP_AVAILABLE = True
except ImportError:
    SHAP_AVAILABLE = False
    logger.warning("SHAP not installed. Install with: pip install shap")


# ============================================================================
# DOMAIN MODELS
# ============================================================================

class RiskPrediction(BaseModel):
    """Individual student risk prediction."""
    student_id: str
    course_id: str
    prediction_id: str
    risk_score: float = Field(ge=0.0, le=1.0)  # y_hat_i_t
    risk_level: str  # "low", "medium", "high", "critical"
    # Contributing factors (top 3 SHAP)
    top_factors: List[Dict[str, Any]] = []  # [{feature, shap_value, direction}]
    # Input features
    input_features: Dict[str, float]
    # Metadata
    model_version: str
    formula_version: str = "1.0"
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class RiskPredictionBatch(BaseModel):
    """Batch risk predictions."""
    course_id: str
    prediction_batch_id: str
    predictions: List[RiskPrediction]
    cohort_size: int
    high_risk_count: int
    critical_risk_count: int
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


class FeatureImportance(BaseModel):
    """Feature importance from SHAP."""
    feature_name: str
    mean_abs_shap: float  # Mean absolute SHAP value (importance)
    rank: int


# ============================================================================
# XGBOOST RISK MODEL
# ============================================================================

class XGBoostRiskModel:
    """
    XGBoost-based predictive risk model with SHAP explainability.
    
    Predicts: y_hat_i_t = f_theta(x_i_t)
    
    Where:
    - y_hat_i_t = predicted risk score for student i at time t
    - f_theta = XGBoost model (trained on historical data)
    - x_i_t = feature vector (attendance, curriculum, engagement, temporal)
    
    SHAP provides feature attribution:
    - Which features most influenced the prediction?
    - In which direction (increasing/decreasing risk)?
    - How much impact did each feature have?
    """
    
    def __init__(
        self,
        model_path: str = "backend/app/ml/models/xgboost_risk_model.joblib",
        model_version: str = "v1.0",
    ):
        self.model_path = model_path
        self.model_version = model_version
        self.model = None
        self.shap_explainer = None
        self.feature_names = [
            "cumulative_attendance_rate",
            "late_arrival_frequency",
            "attendance_volatility",
            "attendance_change",
            "curriculum_coverage",
            "curriculum_coverage_trend",
            "topics_behind",
            "resource_access_count",
            "biometric_success_rate",
            "days_since_start",
            "weeks_into_semester",
            "is_late_in_semester",
        ]
    
    async def initialize(self):
        """Load model and setup SHAP explainer."""
        if not XGBOOST_AVAILABLE:
            raise ImportError("XGBoost required. Install: pip install xgboost")
        
        # Load model if exists, otherwise create dummy
        if os.path.exists(self.model_path):
            try:
                self.model = joblib.load(self.model_path)
                logger.info(f"✓ Loaded XGBoost model from {self.model_path}")
            except Exception as e:
                logger.error(f"Could not load model: {e}. Creating dummy model.")
                self.model = self._create_dummy_model()
        else:
            logger.info(f"Model not found at {self.model_path}. Creating dummy model for development.")
            self.model = self._create_dummy_model()
        
        # Setup SHAP explainer
        if SHAP_AVAILABLE:
            try:
                self.shap_explainer = shap.TreeExplainer(self.model)
                logger.info("✓ SHAP explainer initialized")
            except Exception as e:
                logger.warning(f"Could not initialize SHAP: {e}")
                self.shap_explainer = None
    
    def _create_dummy_model(self):
        """Create a dummy XGBoost model for development (uses feature importance)."""
        if not XGBOOST_AVAILABLE:
            return None
        
        # Create synthetic training data
        np.random.seed(42)
        X_train = np.random.rand(1000, len(self.feature_names))
        # Create synthetic labels (higher attendance/curriculum = lower risk)
        y_train = 1.0 - (X_train[:, 0] + X_train[:, 4]) / 2 + np.random.normal(0, 0.1, 1000)
        y_train = np.clip(y_train, 0, 1)
        
        # Train simple model
        model = xgb.XGBRegressor(
            n_estimators=50,
            max_depth=3,
            learning_rate=0.1,
            random_state=42,
        )
        model.fit(X_train, y_train)
        
        logger.info("Created dummy XGBoost model for development")
        return model
    
    # ========================================================================
    # PREDICTION
    # ========================================================================
    
    def predict(
        self,
        features: Dict[str, float],
    ) -> float:
        """
        Predict risk score for a student.
        
        Args:
            features: Feature vector {feature_name: value}
        
        Returns:
            Risk score [0, 1]
        """
        if self.model is None:
            logger.error("Model not loaded")
            return 0.5
        
        # Convert to feature vector (in correct order)
        X = np.array([[features.get(fname, 0.0) for fname in self.feature_names]])
        
        # Predict (ensure output is [0, 1])
        y_hat = float(self.model.predict(X)[0])
        return np.clip(y_hat, 0.0, 1.0)
    
    def predict_batch(
        self,
        features_list: List[Dict[str, float]],
    ) -> List[float]:
        """Batch prediction for multiple students."""
        if self.model is None:
            return [0.5] * len(features_list)
        
        X = np.array([
            [f.get(fname, 0.0) for fname in self.feature_names]
            for f in features_list
        ])
        
        y_hats = self.model.predict(X)
        return [np.clip(float(y), 0.0, 1.0) for y in y_hats]
    
    # ========================================================================
    # EXPLAINABILITY: SHAP
    # ========================================================================
    
    def explain_prediction(
        self,
        features: Dict[str, float],
    ) -> Tuple[List[Dict[str, Any]], Optional[float]]:
        """
        Explain prediction using SHAP.
        
        Args:
            features: Feature vector
        
        Returns:
            (top_factors, base_value) where top_factors = [{feature, shap_value, direction}]
        """
        if self.model is None or self.shap_explainer is None:
            return [], None
        
        try:
            # Prepare data
            X = np.array([[features.get(fname, 0.0) for fname in self.feature_names]])
            
            # Compute SHAP values
            shap_values = self.shap_explainer.shap_values(X)
            base_value = float(self.shap_explainer.expected_value)
            
            # Get SHAP values for this instance
            if isinstance(shap_values, list):
                # Multi-class: take first class
                instance_shap = shap_values[0][0]
            else:
                instance_shap = shap_values[0]
            
            # Sort by absolute SHAP value
            factor_list = [
                {
                    "feature": self.feature_names[i],
                    "shap_value": float(instance_shap[i]),
                    "direction": "increases_risk" if instance_shap[i] > 0 else "decreases_risk",
                    "magnitude": float(abs(instance_shap[i])),
                }
                for i in range(len(self.feature_names))
            ]
            
            factor_list.sort(key=lambda x: x["magnitude"], reverse=True)
            top_factors = factor_list[:3]  # Top 3 factors
            
            return top_factors, base_value
            
        except Exception as e:
            logger.warning(f"SHAP explanation failed: {e}")
            return [], None
    
    # ========================================================================
    # FEATURE IMPORTANCE
    # ========================================================================
    
    def get_feature_importance(self) -> List[FeatureImportance]:
        """
        Get feature importance from model.
        
        Returns:
            Ranked list of features by importance
        """
        if self.model is None:
            return []
        
        try:
            importances = self.model.feature_importances_
            
            importance_list = [
                FeatureImportance(
                    feature_name=self.feature_names[i],
                    mean_abs_shap=float(importances[i]),
                    rank=i + 1,
                )
                for i in range(len(self.feature_names))
            ]
            
            # Sort by importance
            importance_list.sort(key=lambda x: x.mean_abs_shap, reverse=True)
            
            # Update ranks
            for i, imp in enumerate(importance_list):
                imp.rank = i + 1
            
            return importance_list
            
        except Exception as e:
            logger.warning(f"Could not compute feature importance: {e}")
            return []
    
    # ========================================================================
    # RISK CATEGORIZATION
    # ========================================================================
    
    @staticmethod
    def score_to_level(score: float) -> str:
        """Convert risk score to categorical level."""
        if score < 0.3:
            return "low"
        elif score < 0.6:
            return "medium"
        elif score < 0.8:
            return "high"
        else:
            return "critical"
    
    def generate_prediction(
        self,
        student_id: str,
        course_id: str,
        features: Dict[str, float],
    ) -> RiskPrediction:
        """
        Generate full risk prediction with explanation.
        
        Args:
            student_id: Student ID
            course_id: Course ID
            features: Feature vector
        
        Returns:
            RiskPrediction with score, level, and top factors
        """
        # Predict risk score
        risk_score = self.predict(features)
        
        # Get SHAP explanation
        top_factors, base_value = self.explain_prediction(features)
        
        # Categorize risk level
        risk_level = self.score_to_level(risk_score)
        
        # Create prediction object
        prediction = RiskPrediction(
            student_id=student_id,
            course_id=course_id,
            prediction_id=f"pred_{student_id}_{datetime.now(timezone.utc).timestamp()}",
            risk_score=risk_score,
            risk_level=risk_level,
            top_factors=top_factors,
            input_features=features,
            model_version=self.model_version,
        )
        
        return prediction
    
    def generate_batch_predictions(
        self,
        course_id: str,
        student_features_list: List[Tuple[str, Dict[str, float]]],
    ) -> RiskPredictionBatch:
        """
        Generate predictions for entire cohort.
        
        Args:
            course_id: Course ID
            student_features_list: [(student_id, features_dict), ...]
        
        Returns:
            RiskPredictionBatch with all predictions
        """
        predictions = []
        high_risk = 0
        critical_risk = 0
        
        for student_id, features in student_features_list:
            pred = self.generate_prediction(student_id, course_id, features)
            predictions.append(pred)
            
            if pred.risk_level == "high":
                high_risk += 1
            elif pred.risk_level == "critical":
                critical_risk += 1
        
        batch = RiskPredictionBatch(
            course_id=course_id,
            prediction_batch_id=f"batch_{course_id}_{datetime.now(timezone.utc).timestamp()}",
            predictions=predictions,
            cohort_size=len(predictions),
            high_risk_count=high_risk,
            critical_risk_count=critical_risk,
        )
        
        return batch
