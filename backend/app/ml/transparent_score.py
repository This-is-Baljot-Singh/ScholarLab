"""
Transparent Score: Human-readable companion formula to XGBoost model.

Formula: r_i_t = sigmoid(beta_0 + beta_1 * a_t + beta_2 * delta_a_t + beta_3 * c_t)

This provides explainability alongside the ML model.

Components:
- a_t = cumulative attendance rate (0-1)
- delta_a_t = change in attendance (trend, -1 to 1)
- c_t = curriculum coverage (0-1)
- Sigmoid transforms linear combination to [0, 1]

Advantages:
- Fully interpretable (each term has clear meaning)
- No black-box
- Can be audited and explained to students/faculty
- Serves as sanity check for XGBoost
"""

import logging
from typing import Dict, Tuple, List, Any
from datetime import datetime, timezone
from pydantic import BaseModel, Field
import numpy as np

logger = logging.getLogger(__name__)


# ============================================================================
# DOMAIN MODELS
# ============================================================================

class TransparentScoreCoefficients(BaseModel):
    """Coefficients for transparent score formula."""
    beta_0: float = -1.5  # Intercept (baseline risk when attendance/coverage average)
    beta_1: float = -3.0  # Attendance rate: higher attendance → lower risk
    beta_2: float = -2.0  # Attendance change: improving attendance → lower risk
    beta_3: float = -2.5  # Curriculum coverage: higher coverage → lower risk
    
    formula_version: str = "1.0"
    description: str = "r_i_t = sigmoid(beta_0 + beta_1*a_t + beta_2*delta_a_t + beta_3*c_t)"


class TransparentScore(BaseModel):
    """Transparent risk score with full breakdown."""
    student_id: str
    course_id: str
    prediction_id: str
    # Score components
    cumulative_attendance_rate: float  # a_t
    attendance_change: float  # delta_a_t
    curriculum_coverage: float  # c_t
    # Computation
    linear_combination: float  # beta_0 + beta_1*a_t + beta_2*delta_a_t + beta_3*c_t
    risk_score: float = Field(ge=0.0, le=1.0)  # r_i_t (sigmoid output)
    risk_level: str  # "low", "medium", "high", "critical"
    # Component contributions
    beta_0_contribution: float
    beta_1_contribution: float  # beta_1 * a_t
    beta_2_contribution: float  # beta_2 * delta_a_t
    beta_3_contribution: float  # beta_3 * c_t
    # Coefficients used
    coefficients: TransparentScoreCoefficients
    # Computed at
    computed_at: datetime = Field(default_factory=lambda: datetime.now(timezone.utc))


# ============================================================================
# TRANSPARENT SCORE CALCULATOR
# ============================================================================

class TransparentScoreCalculator:
    """
    Calculates human-readable transparent risk score.
    
    Formula: r_i_t = sigmoid(beta_0 + beta_1 * a_t + beta_2 * delta_a_t + beta_3 * c_t)
    
    Where:
    - a_t = cumulative attendance rate [0, 1]
    - delta_a_t = change in attendance [-1, 1]
    - c_t = curriculum coverage [0, 1]
    - r_i_t = risk score [0, 1] (sigmoid output)
    
    Interpretation:
    - r_i_t close to 0: low risk
    - r_i_t close to 1: high risk
    
    Each term shows clear direction:
    - Higher a_t → lower risk (attendance helps)
    - Positive delta_a_t → lower risk (improving trend is good)
    - Higher c_t → lower risk (curriculum progress helps)
    """
    
    def __init__(
        self,
        coefficients: TransparentScoreCoefficients = None,
    ):
        self.coefficients = coefficients or TransparentScoreCoefficients()
    
    # ========================================================================
    # CORE COMPUTATION
    # ========================================================================
    
    @staticmethod
    def sigmoid(z: float) -> float:
        """Sigmoid activation: 1 / (1 + exp(-z))"""
        # Clip to prevent overflow
        z = np.clip(z, -500, 500)
        return float(1.0 / (1.0 + np.exp(-z)))
    
    def compute_transparent_score(
        self,
        student_id: str,
        course_id: str,
        cumulative_attendance_rate: float,
        attendance_change: float,
        curriculum_coverage: float,
    ) -> TransparentScore:
        """
        Compute transparent risk score.
        
        Args:
            student_id: Student ID
            course_id: Course ID
            cumulative_attendance_rate: a_t [0, 1]
            attendance_change: delta_a_t [-1, 1]
            curriculum_coverage: c_t [0, 1]
        
        Returns:
            TransparentScore with full breakdown
        """
        coef = self.coefficients
        
        # Compute component contributions
        beta_0_contrib = coef.beta_0
        beta_1_contrib = coef.beta_1 * cumulative_attendance_rate
        beta_2_contrib = coef.beta_2 * attendance_change
        beta_3_contrib = coef.beta_3 * curriculum_coverage
        
        # Linear combination
        linear_combo = beta_0_contrib + beta_1_contrib + beta_2_contrib + beta_3_contrib
        
        # Apply sigmoid
        risk_score = self.sigmoid(linear_combo)
        
        # Categorize risk level
        risk_level = self._score_to_level(risk_score)
        
        # Create score object
        score = TransparentScore(
            student_id=student_id,
            course_id=course_id,
            prediction_id=f"transparent_{student_id}_{datetime.now(timezone.utc).timestamp()}",
            cumulative_attendance_rate=cumulative_attendance_rate,
            attendance_change=attendance_change,
            curriculum_coverage=curriculum_coverage,
            linear_combination=linear_combo,
            risk_score=risk_score,
            risk_level=risk_level,
            beta_0_contribution=beta_0_contrib,
            beta_1_contribution=beta_1_contrib,
            beta_2_contribution=beta_2_contrib,
            beta_3_contribution=beta_3_contrib,
            coefficients=coef,
        )
        
        return score
    
    # ========================================================================
    # EXPLAINABILITY
    # ========================================================================
    
    def explain_score(self, score: TransparentScore) -> str:
        """
        Generate human-readable explanation of score.
        
        Returns:
            Narrative explanation
        """
        coef = self.coefficients
        
        factors = []
        
        # Attendance contribution
        if score.cumulative_attendance_rate > 0.8:
            factors.append(f"Strong attendance ({score.cumulative_attendance_rate:.1%}) helps reduce risk")
        elif score.cumulative_attendance_rate < 0.5:
            factors.append(f"Low attendance ({score.cumulative_attendance_rate:.1%}) significantly increases risk")
        else:
            factors.append(f"Moderate attendance ({score.cumulative_attendance_rate:.1%}) is a risk factor")
        
        # Attendance trend
        if score.attendance_change > 0.2:
            factors.append(f"Positive attendance trend (Δa_t={score.attendance_change:.2f}) helps reduce risk")
        elif score.attendance_change < -0.2:
            factors.append(f"Declining attendance trend (Δa_t={score.attendance_change:.2f}) worsens risk")
        
        # Curriculum coverage
        if score.curriculum_coverage > 0.7:
            factors.append(f"Good curriculum coverage ({score.curriculum_coverage:.1%}) reduces risk")
        elif score.curriculum_coverage < 0.4:
            factors.append(f"Poor curriculum coverage ({score.curriculum_coverage:.1%}) significantly increases risk")
        else:
            factors.append(f"Moderate curriculum progress ({score.curriculum_coverage:.1%}) is concerning")
        
        explanation = " | ".join(factors)
        
        # Add risk level summary
        if score.risk_level == "critical":
            explanation += " → CRITICAL: Immediate intervention needed"
        elif score.risk_level == "high":
            explanation += " → HIGH RISK: Monitoring and support recommended"
        elif score.risk_level == "medium":
            explanation += " → MEDIUM RISK: Track performance"
        else:
            explanation += " → LOW RISK: On track"
        
        return explanation
    
    # ========================================================================
    # MODEL COMPARISON
    # ========================================================================
    
    def compare_with_ml_model(
        self,
        transparent_score: float,
        ml_score: float,
        threshold: float = 0.15,
    ) -> Dict[str, Any]:
        """
        Compare transparent score with ML model prediction.
        
        Args:
            transparent_score: r_i_t (transparent formula)
            ml_score: y_hat_i_t (XGBoost prediction)
            threshold: Alert if difference > threshold
        
        Returns:
            Comparison dictionary with discrepancy flag
        """
        difference = abs(transparent_score - ml_score)
        
        return {
            "transparent_score": transparent_score,
            "ml_score": ml_score,
            "difference": difference,
            "within_threshold": difference <= threshold,
            "alert": difference > threshold,
            "agreement": "yes" if difference <= threshold else "no",
            "note": (
                f"Scores align well" if difference <= threshold
                else f"Significant discrepancy: investigate feature engineering or model calibration"
            ),
        }
    
    # ========================================================================
    # BATCH COMPUTATION
    # ========================================================================
    
    def compute_batch_scores(
        self,
        course_id: str,
        student_data: List[Dict[str, Any]],
    ) -> List[TransparentScore]:
        """
        Compute transparent scores for entire cohort.
        
        Args:
            course_id: Course ID
            student_data: [{student_id, a_t, delta_a_t, c_t}, ...]
        
        Returns:
            List of TransparentScore objects
        """
        scores = []
        
        for data in student_data:
            score = self.compute_transparent_score(
                student_id=data["student_id"],
                course_id=course_id,
                cumulative_attendance_rate=data["a_t"],
                attendance_change=data["delta_a_t"],
                curriculum_coverage=data["c_t"],
            )
            scores.append(score)
        
        return scores
    
    # ========================================================================
    # UTILITIES
    # ========================================================================
    
    @staticmethod
    def _score_to_level(score: float) -> str:
        """Convert risk score to categorical level."""
        if score < 0.3:
            return "low"
        elif score < 0.6:
            return "medium"
        elif score < 0.8:
            return "high"
        else:
            return "critical"
    
    def get_formula_string(self) -> str:
        """Get human-readable formula string."""
        coef = self.coefficients
        return (
            f"r_i_t = sigmoid({coef.beta_0} + {coef.beta_1}*a_t + {coef.beta_2}*Δa_t + {coef.beta_3}*c_t)\n"
            f"Where:\n"
            f"  a_t = cumulative attendance rate [0, 1]\n"
            f"  Δa_t = change in attendance [-1, 1]\n"
            f"  c_t = curriculum coverage [0, 1]\n"
            f"  r_i_t = risk score [0, 1]"
        )
    
    def sensitivity_analysis(
        self,
        baseline_a_t: float = 0.8,
        baseline_delta_a_t: float = 0.1,
        baseline_c_t: float = 0.6,
    ) -> List[Dict[str, Any]]:
        """
        Sensitivity analysis: how does each variable affect risk?
        
        Returns:
            List of results showing risk score for different input values
        """
        results = []
        
        # Vary attendance rate
        for a_t in [0.3, 0.5, 0.7, 0.9]:
            score = self.sigmoid(
                self.coefficients.beta_0
                + self.coefficients.beta_1 * a_t
                + self.coefficients.beta_2 * baseline_delta_a_t
                + self.coefficients.beta_3 * baseline_c_t
            )
            results.append({"variable": "attendance_rate", "value": a_t, "risk_score": score})
        
        # Vary attendance trend
        for delta_a_t in [-0.5, -0.2, 0.0, 0.3, 0.5]:
            score = self.sigmoid(
                self.coefficients.beta_0
                + self.coefficients.beta_1 * baseline_a_t
                + self.coefficients.beta_2 * delta_a_t
                + self.coefficients.beta_3 * baseline_c_t
            )
            results.append({"variable": "attendance_change", "value": delta_a_t, "risk_score": score})
        
        # Vary curriculum coverage
        for c_t in [0.2, 0.4, 0.6, 0.8, 1.0]:
            score = self.sigmoid(
                self.coefficients.beta_0
                + self.coefficients.beta_1 * baseline_a_t
                + self.coefficients.beta_2 * baseline_delta_a_t
                + self.coefficients.beta_3 * c_t
            )
            results.append({"variable": "curriculum_coverage", "value": c_t, "risk_score": score})
        
        return results
