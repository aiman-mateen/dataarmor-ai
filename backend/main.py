import sys
import os
import shutil
import uuid
import math

from fastapi import FastAPI, UploadFile, File, HTTPException, Body
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, JSONResponse
from typing import Optional

sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'privacy'))

from ensemble import load_all_models

app = FastAPI(title="DataArmor AI API")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

UPLOAD_FOLDER = os.path.join(os.path.dirname(__file__), "uploads")
OUTPUT_FOLDER = os.path.join(os.path.dirname(__file__), "outputs")
os.makedirs(UPLOAD_FOLDER, exist_ok=True)
os.makedirs(OUTPUT_FOLDER, exist_ok=True)

print("Loading models on startup...")
MODELS, ENCODERS, SCALERS = load_all_models()
print("Models ready.")


def clean_value(v):
    if isinstance(v, float) and (math.isnan(v) or math.isinf(v)):
        return None
    return v


@app.get("/")
def root():
    return {"status": "DataArmor AI API is running"}


@app.post("/detect")
async def detect_phi(file: UploadFile = File(...)):
    """
    Step 1 — Upload CSV and run PHI detection only.
    Returns predictions and a session_file token for step 2.
    Does NOT apply privacy transformations yet.
    """
    if not file.filename.endswith(".csv"):
        raise HTTPException(
            status_code=400,
            detail="Only CSV files are accepted."
        )

    unique_id = str(uuid.uuid4())[:8]
    upload_path = os.path.join(
        UPLOAD_FOLDER, f"{unique_id}_{file.filename}"
    )

    with open(upload_path, "wb") as f:
        shutil.copyfileobj(file.file, f)

    print(f"\nFile received: {upload_path}")

    try:
        from ensemble import ensemble_predict
        import pandas as pd

        predictions, column_names, individual_preds, confidence_scores = ensemble_predict(
            upload_path, MODELS, ENCODERS, SCALERS
        )

        original_df = pd.read_csv(upload_path)

        return JSONResponse(content={
            "status": "success",
            "filename": file.filename,
            "rows": len(original_df),
            "columns": len(predictions),
            "predictions": predictions,
            "individual_model_predictions": individual_preds,
            "confidence_scores": confidence_scores,
            "session_file": os.path.basename(upload_path),
        })

    except Exception as e:
        if os.path.exists(upload_path):
            os.remove(upload_path)
        raise HTTPException(
            status_code=500,
            detail=f"Detection error: {str(e)}"
        )


@app.post("/anonymize")
async def anonymize_dataset(
    session_file: str,
    epsilon: float = 1.0,
    k: int = 3,
    body: dict = Body(default={})
):
    """
    Step 2 — Apply privacy transformations with user-chosen epsilon and k.
    Accepts optional user-overridden predictions in request body.
    """
    upload_path = os.path.join(UPLOAD_FOLDER, session_file)

    if not os.path.exists(upload_path):
        raise HTTPException(
            status_code=404,
            detail="Session file not found. Please upload your dataset again."
        )

    try:
        from ensemble import ensemble_predict
        import pandas as pd
        from privacy_pipeline import run_privacy_pipeline, save_outputs

        user_predictions = body.get("predictions")
        if user_predictions:
            predictions = user_predictions
            confidence_scores = {}
            print("Using user-provided predictions with overrides")
        else:
            predictions, column_names, individual_preds, confidence_scores = ensemble_predict(
             upload_path, MODELS, ENCODERS, SCALERS
        )
            print("Re-running ensemble prediction")

        original_df = pd.read_csv(upload_path)

        anonymized_df, compliance_report = run_privacy_pipeline(
            original_df,
            predictions,
            epsilon=epsilon,
            k=k,
            random_seed=42
        )

        save_outputs(
            anonymized_df,
            compliance_report,
            output_folder=OUTPUT_FOLDER
        )

        cleaned_anonymized = [
            {col: clean_value(val) for col, val in row.items()}
            for row in anonymized_df.to_dict(orient="records")
        ]

        return JSONResponse(content={
            "status": "success",
            "filename": os.path.basename(upload_path),
            "rows": len(original_df),
            "columns": len(predictions),
            "predictions": predictions,
            "confidence_scores": confidence_scores,
            "anonymized_data": cleaned_anonymized,
            "compliance_report": compliance_report,
            "epsilon_used": epsilon,
            "k_used": k,
            "download_links": {
                "anonymized_csv": "/download/anonymized",
                "compliance_csv": "/download/compliance_csv",
                "compliance_json": "/download/compliance_json",
            }
        })

    except Exception as e:
        raise HTTPException(
            status_code=500,
            detail=f"Anonymization error: {str(e)}"
        )

    finally:
        if os.path.exists(upload_path):
            os.remove(upload_path)


# @app.get("/download/anonymized")
# def download_anonymized():
#     path = os.path.join(OUTPUT_FOLDER, "anonymized_dataset.csv")
#     if not os.path.exists(path):
#         raise HTTPException(status_code=404, detail="File not found.")

@app.get("/download/anonymized")
def download_anonymized():
    path = os.path.join(OUTPUT_FOLDER, "anonymized_dataset.csv")
    print(f"Looking for file at: {path}")
    print(f"File exists: {os.path.exists(path)}")
    print(f"OUTPUT_FOLDER is: {OUTPUT_FOLDER}")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail=f"File not found at {path}")
    return FileResponse(
        path,
        media_type="text/csv",
        filename="anonymized_dataset.csv"
    )


@app.get("/download/compliance_csv")
def download_compliance_csv():
    path = os.path.join(OUTPUT_FOLDER, "compliance_report.csv")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(
        path,
        media_type="text/csv",
        filename="compliance_report.csv"
    )


@app.get("/download/compliance_json")
def download_compliance_json():
    path = os.path.join(OUTPUT_FOLDER, "compliance_report.json")
    if not os.path.exists(path):
        raise HTTPException(status_code=404, detail="File not found.")
    return FileResponse(
        path,
        media_type="application/json",
        filename="compliance_report.json"
    )