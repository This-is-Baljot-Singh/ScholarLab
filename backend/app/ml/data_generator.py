# ScholarLab/backend/app/ml/data_generator.py
import pandas as pd
import numpy as np
import os
import logging

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

def generate_synthetic_student_data(num_samples=5000, output_path="app/ml/data/synthetic_students.csv"):
    """
    Generates realistic, imbalanced synthetic data for student academic risk profiling.
    """
    np.random.seed(42)
    
    # 1. Generate Base Features
    # Assume 85% of students are "Safe" (Class 0) and 15% are "At Risk/Dropout" (Class 1)
    labels = np.random.choice([0, 1], size=num_samples, p=[0.85, 0.15])
    
    data = []
    for label in labels:
        if label == 0:  # Safe Student
            attendance_rate = np.random.normal(loc=0.88, scale=0.08)
            avg_arrival_delay_mins = np.random.exponential(scale=3.0)
            curriculum_engagement_score = np.random.normal(loc=85, scale=10)
            spatial_anomalies = np.random.poisson(lam=0.5) # Rare spoofing attempts
            biometric_failures = np.random.poisson(lam=0.2)
        else:           # At-Risk Student
            attendance_rate = np.random.normal(loc=0.55, scale=0.15)
            avg_arrival_delay_mins = np.random.exponential(scale=12.0)
            curriculum_engagement_score = np.random.normal(loc=45, scale=15)
            spatial_anomalies = np.random.poisson(lam=3.5) # Frequent spoofing attempts
            biometric_failures = np.random.poisson(lam=2.1)

        # Clip values to realistic bounds
        data.append({
            "attendance_rate": np.clip(attendance_rate, 0.0, 1.0),
            "avg_arrival_delay_mins": np.clip(avg_arrival_delay_mins, 0.0, 60.0),
            "curriculum_engagement_score": np.clip(curriculum_engagement_score, 0.0, 100.0),
            "spatial_anomalies": spatial_anomalies,
            "biometric_failures": biometric_failures,
            "risk_label": label
        })

    df = pd.DataFrame(data)
    
    # Ensure directory exists
    os.makedirs(os.path.dirname(output_path), exist_ok=True)
    df.to_csv(output_path, index=False)
    
    logger.info(f"Successfully generated {num_samples} synthetic student records at {output_path}")
    logger.info(f"Class Distribution:\n{df['risk_label'].value_counts(normalize=True)}")
    
    return df

if __name__ == "__main__":
    generate_synthetic_student_data()