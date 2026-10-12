import sys
import os
import pandas as pd

# Add privacy folder to path so imports work
sys.path.insert(0, os.path.join(os.path.dirname(__file__), 'privacy'))

from privacy_pipeline import run_privacy_pipeline, save_outputs
from ensemble import load_all_models, ensemble_predict

# =============================================================================
# MAIN RUNNER
# =============================================================================

def run_full_pipeline(csv_path: str,
                      epsilon: float = 1.0,
                      k: int = 3,
                      output_folder: str = None):
    """
    Full end-to-end pipeline.
    CSV → features → ensemble → privacy → anonymized output

    Returns:
        anonymized_df      — anonymized pandas DataFrame
        compliance_report  — list of dicts
        predictions        — dict of {column: label}
        output_paths       — dict of saved file paths
    """

    print("\n" + "=" * 65)
    print("DataArmor AI — Full Pipeline")
    print("=" * 65)

    # Step 1 — Load models once
    print("\n[Step 1] Loading models...")
    models, encoders, scalers = load_all_models()

    # Step 2 — Ensemble prediction
    print("\n[Step 2] Running ensemble prediction...")
    predictions, column_names, individual_preds = ensemble_predict(
        csv_path, models, encoders, scalers
    )

    print("\nEnsemble predictions:")
    for col, label in predictions.items():
        print(f"  {col:<35} → {label}")

    # Step 3 — Load original CSV for privacy pipeline
    print("\n[Step 3] Applying privacy transformations...")
    original_df = pd.read_csv(csv_path)

    # Step 4 — Run privacy pipeline
    anonymized_df, compliance_report = run_privacy_pipeline(
        original_df,
        predictions,
        epsilon=epsilon,
        k=k,
        random_seed=42
    )

    # Step 5 — Save outputs
    print("\n[Step 4] Saving outputs...")
    if output_folder is None:
        output_folder = os.path.join(
            os.path.dirname(__file__), 'outputs'
        )

    output_paths = save_outputs(
        anonymized_df,
        compliance_report,
        output_folder=output_folder
    )

    print("\n" + "=" * 65)
    print("PIPELINE COMPLETE")
    print("=" * 65)
    print(f"  Rows processed    : {len(original_df)}")
    print(f"  Columns processed : {len(predictions)}")
    print(f"  Output folder     : {output_folder}")

    return anonymized_df, compliance_report, predictions, output_paths


# =============================================================================
# TEST — run directly
# =============================================================================

if __name__ == "__main__":

    TEST_CSV = r"D:\FYP\DataArmor_Backend\test_sample.csv"

    anonymized_df, report, predictions, paths = run_full_pipeline(
        csv_path=TEST_CSV,
        epsilon=1.0,
        k=3
    )

    print("\nANONYMIZED OUTPUT:")
    print(anonymized_df.to_string(index=False))

    print("\nCOMPLIANCE REPORT SUMMARY:")
    for row in report:
        print(
            f"  {row['column_name']:<20} "
            f"{row['predicted_label']:<22} "
            f"{row['technique_applied']:<35} "
            f"{row['original_sample']:<20} → "
            f"{row['transformed_sample']}"
        )

    print(f"\nFiles saved: {list(paths.values())}")