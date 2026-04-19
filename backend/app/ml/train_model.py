# ScholarLab/backend/app/ml/train_model.py
import pandas as pd
import numpy as np
import os
import joblib
import logging
from sklearn.model_selection import train_test_split
from sklearn.ensemble import RandomForestClassifier
from xgboost import XGBClassifier
from sklearn.metrics import classification_report, accuracy_score, precision_recall_curve
from imblearn.over_sampling import SMOTE

logging.basicConfig(level=logging.INFO)
logger = logging.getLogger(__name__)

DATA_PATH = "app/ml/data/synthetic_students.csv"
MODEL_OUTPUT_PATH = "app/ml/models/xgboost_risk_model.joblib"

def train_predictive_model():
    if not os.path.exists(DATA_PATH):
        logger.error(f"Data not found at {DATA_PATH}. Run data_generator.py first.")
        return

    logger.info("Loading synthetic dataset...")
    df = pd.read_csv(DATA_PATH)
    
    X = df.drop(columns=["risk_label"])
    y = df["risk_label"]

    # 1. Train/Test Split
    X_train, X_test, y_train, y_test = train_test_split(X, y, test_size=0.2, random_state=42, stratify=y)
    
    logger.info(f"Original training distribution: {np.bincount(y_train)}")

    # 2. Handle Class Imbalance with SMOTE
    # This synthesizes new examples of the minority class to prevent model bias
    logger.info("Applying Synthetic Minority Over-sampling Technique (SMOTE)...")
    smote = SMOTE(random_state=42)
    X_train_resampled, y_train_resampled = smote.fit_resample(X_train, y_train)
    
    logger.info(f"Resampled training distribution: {np.bincount(y_train_resampled)}")

    # 3. Model 1: Random Forest (Baseline Ensemble)
    logger.info("Training Random Forest Classifier...")
    rf_model = RandomForestClassifier(n_estimators=100, max_depth=10, random_state=42)
    rf_model.fit(X_train_resampled, y_train_resampled)
    rf_preds = rf_model.predict(X_test)
    logger.info(f"Random Forest Accuracy: {accuracy_score(y_test, rf_preds):.4f}")

    # 4. Model 2: XGBoost (Primary Ensemble)
    logger.info("Training Extreme Gradient Boosting (XGBoost) Classifier...")
    xgb_model = XGBClassifier(
        n_estimators=150,
        learning_rate=0.05,
        max_depth=6,
        subsample=0.8,
        colsample_bytree=0.8,
        use_label_encoder=False,
        eval_metric='logloss',
        random_state=42
    )
    xgb_model.fit(X_train_resampled, y_train_resampled)
    xgb_preds = xgb_model.predict(X_test)
    
    logger.info(f"XGBoost Accuracy: {accuracy_score(y_test, xgb_preds):.4f}")
    logger.info("XGBoost Detailed Classification Report:")
    logger.info("\n" + classification_report(y_test, xgb_preds))

    # 5. Export Production Model
    os.makedirs(os.path.dirname(MODEL_OUTPUT_PATH), exist_ok=True)
    
    # We save XGBoost as it typically outperforms RF on tabular data
    joblib.dump(xgb_model, MODEL_OUTPUT_PATH)
    logger.info(f"Production model successfully serialized to {MODEL_OUTPUT_PATH}")

if __name__ == "__main__":
    train_predictive_model()