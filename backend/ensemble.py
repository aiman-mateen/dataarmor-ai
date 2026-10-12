import os

import joblib
import numpy as np
import pandas as pd
from scipy import stats
from feature_extractor import extract_features_for_inference, preprocess_for_model

# =============================================================================
# MODEL PATHS
# =============================================================================

MODEL_DIR = os.path.join(os.path.dirname(os.path.abspath(__file__)), "models")

MODELS = {
    "CatBoost":           f"{MODEL_DIR}\\catboost_model.pkl",
    "XGBoost":            f"{MODEL_DIR}\\xgboost_model.pkl",
    "LightGBM":           f"{MODEL_DIR}\\lightgbm_model.pkl",
    "MLP":                f"{MODEL_DIR}\\mlp_model.pkl",
    "RandomForest":       f"{MODEL_DIR}\\rf_model.pkl",
    "LogisticRegression": f"{MODEL_DIR}\\logistic_model.pkl",
}

ENCODERS = {
    "CatBoost":           f"{MODEL_DIR}\\catboost_encoder.pkl",
    "XGBoost":            f"{MODEL_DIR}\\xgboost_encoder.pkl",
    "LightGBM":           f"{MODEL_DIR}\\lightgbm_encoder.pkl",
    "MLP":                f"{MODEL_DIR}\\mlp_encoder.pkl",
    "RandomForest":       f"{MODEL_DIR}\\rf_encoder.pkl",
    "LogisticRegression": f"{MODEL_DIR}\\logistic_encoder.pkl",
}

SCALERS = {
    "MLP":                f"{MODEL_DIR}\\mlp_scaler.pkl",
    "LogisticRegression": f"{MODEL_DIR}\\logistic_scaler.pkl",
}

# =============================================================================
# LOAD ALL MODELS
# =============================================================================

def load_all_models():
    print("Loading models...")
    
    loaded_models   = {}
    loaded_encoders = {}
    loaded_scalers  = {}
    
    for name, path in MODELS.items():
        try:
            loaded_models[name] = joblib.load(path)
            print(f"  ✓ {name} model loaded")
        except Exception as e:
            print(f"  ✗ {name} model FAILED: {e}")
    
    for name, path in ENCODERS.items():
        try:
            loaded_encoders[name] = joblib.load(path)
            print(f"  ✓ {name} encoder loaded")
        except Exception as e:
            print(f"  ✗ {name} encoder FAILED: {e}")
    
    for name, path in SCALERS.items():
        try:
            loaded_scalers[name] = joblib.load(path)
            print(f"  ✓ {name} scaler loaded")
        except Exception as e:
            print(f"  ✗ {name} scaler FAILED: {e}")
    
    return loaded_models, loaded_encoders, loaded_scalers


# =============================================================================
# PREDICT WITH ONE MODEL
# =============================================================================

def predict_single_model(name, model, encoder, X, scaler=None):
    try:
        X_input = X.copy()
        
        # MLP and Logistic Regression need scaling
        if scaler is not None:
            X_input = scaler.transform(X_input)
        
        raw_preds = model.predict(X_input)
        
        # Convert numeric predictions back to label strings
        labels = encoder.inverse_transform(raw_preds)
        
        return labels
    
    except Exception as e:
        print(f"  WARNING: {name} prediction failed: {e}")
        return None


# =============================================================================
# ENSEMBLE PREDICT
# =============================================================================

def ensemble_predict(csv_path: str,
                     loaded_models: dict,
                     loaded_encoders: dict,
                     loaded_scalers: dict):
    """
    Full pipeline:
    CSV → feature extraction → preprocessing → 6 models → majority vote
    
    Returns:
        predictions: dict of {column_name: label}
        column_names: list of column names in order
        individual_predictions: dict of {model_name: [labels]}
    """
    
    print(f"\nExtracting features from: {csv_path}")
    features_df, column_names = extract_features_for_inference(csv_path)
    
    if features_df.empty:
        raise ValueError("No features extracted. Check the CSV file.")
    
    print(f"Columns extracted: {len(column_names)}")
    
    print("\nPreprocessing features...")
    X = preprocess_for_model(features_df)
    print(f"Feature matrix shape: {X.shape}")
    
    # Collect predictions from all models
    all_label_predictions = []
    individual_predictions = {}
    
    print("\nRunning predictions...")
    
    for name, model in loaded_models.items():
        encoder = loaded_encoders.get(name)
        scaler  = loaded_scalers.get(name)
        
        if encoder is None:
            print(f"  WARNING: No encoder for {name} — skipping")
            continue
        
        labels = predict_single_model(name, model, encoder, X, scaler)
        
        if labels is not None:
            all_label_predictions.append(labels)
            individual_predictions[name] = list(labels)
            print(f"  ✓ {name}: {list(labels)}")
    
    if not all_label_predictions:
        raise RuntimeError("All models failed to predict.")
    
    # Majority vote across all models
    print("\nComputing majority vote...")
    
    all_preds_array = np.array(all_label_predictions)
    
    final_labels = []
    confidence_scores = {}

    for col_idx in range(all_preds_array.shape[1]):
        col_votes = all_preds_array[:, col_idx]
        unique_labels, counts = np.unique(col_votes, return_counts=True)
        winner = unique_labels[np.argmax(counts)]
        final_labels.append(winner)

        # Confidence = percentage of models that agreed on the winner
        agreement = int(np.max(counts)) / len(all_label_predictions)
        confidence_scores[column_names[col_idx]] = round(agreement * 100, 1)

    predictions = dict(zip(column_names, final_labels))

    return predictions, column_names, individual_predictions, confidence_scores


# =============================================================================
# TEST — run directly to verify
# =============================================================================

if __name__ == "__main__":
    
    TEST_CSV = r"D:\FYP\mimic_fhir_csvs\mimic_patient.csv"
    
    print("=" * 60)
    print("DataArmor AI — Ensemble Test")
    print("=" * 60)
    
    models, encoders, scalers = load_all_models()
    
    predictions, columns, individual = ensemble_predict(
        TEST_CSV, models, encoders, scalers
    )
    
    print("\n" + "=" * 60)
    print("FINAL ENSEMBLE PREDICTIONS")
    print("=" * 60)
    
    print(f"\n{'Column':<35} {'Prediction':<25}")
    print("-" * 60)
    for col, label in predictions.items():
        print(f"{col:<35} {label:<25}")
    
    print("\n" + "=" * 60)
    print("INDIVIDUAL MODEL PREDICTIONS")
    print("=" * 60)
    
    for model_name, preds in individual.items():
        print(f"\n{model_name}:")
        for col, pred in zip(columns, preds):
            print(f"  {col:<35} {pred}")