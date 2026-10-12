# =============================================================================
# DataArmor AI — Phase 8
# Module C: Differential Privacy
# Assigned to: Zulqarnain
# Deadline: Sunday 12 July (submitted Tuesday 14 July)
# =============================================================================
# This module applies Differential Privacy to all columns classified as
# Sensitive Attribute by the Phase 7 ML model.
#
# Numeric columns  → Laplace Mechanism (add calibrated random noise)
# Text columns     → Left unchanged (original values preserved)
# =============================================================================

import pandas as pd
import numpy as np


def _apply_laplace_noise(value: float, sensitivity: float, epsilon: float,
                         col_min: float, col_max: float) -> float:
    """
    Apply the Laplace Mechanism to a single numeric value.

    Formula: noisy_value = value + Laplace(0, sensitivity / epsilon)

    The noisy value is clipped to [col_min, col_max] to prevent nonsensical
    outputs (e.g. negative blood pressure). Rounding is applied to match
    the original value's precision (integer columns stay integer-like).

    Args:
        value: original numeric value
        sensitivity: max - min of the column (global sensitivity)
        epsilon: privacy budget (smaller = more private = more noise)
        col_min: column minimum (for clipping)
        col_max: column maximum (for clipping)

    Returns:
        noisy float value, clipped and rounded
    """
    if pd.isna(value):
        return value

    scale = sensitivity / epsilon  # Laplace scale parameter (b = Δf / ε)
    noise = np.random.laplace(loc=0.0, scale=scale)
    noisy = float(value) + noise

    # Clip to valid range — noise can occasionally push values out of range
    noisy = np.clip(noisy, col_min, col_max)

    # Round to 2 decimal places for clean output
    return round(noisy, 2)


def apply_differential_privacy(
    df: pd.DataFrame,
    sensitive_columns: list,
    epsilon: float = 1.0,
    random_seed: int = None
) -> tuple:
    """
    Apply Differential Privacy to all Sensitive Attribute columns.

    Per the DataArmor AI Phase 8 spec:
    - Numeric columns: Laplace Mechanism with sensitivity = (max - min)
    - Text columns: left unchanged (original values preserved)
    - Non-Sensitive columns are NOT touched

    Args:
        df: original DataFrame (unmodified — a copy is returned)
        sensitive_columns: list of column names classified as Sensitive Attribute
        epsilon: privacy budget (default 1.0 — balanced privacy/utility)
        random_seed: optional seed for reproducibility during testing

    Returns:
        (protected_df, transformation_log)
        protected_df: DataFrame with DP applied to sensitive columns
        transformation_log: list of dicts describing what was done to each column
    """
    if random_seed is not None:
        np.random.seed(random_seed)

    protected_df = df.copy()
    transformation_log = []

    for col in sensitive_columns:
        if col not in df.columns:
            # Column listed in predictions but not present in dataset — skip
            transformation_log.append({
                "column": col,
                "type": "SKIPPED",
                "reason": "Column not found in dataset",
                "epsilon": epsilon,
                "sensitivity": None,
                "noise_scale": None,
            })
            continue

        col_data = df[col]
        non_null = col_data.dropna()

        # ── Determine column type ────────────────────────────────────────────
        # Try to coerce to numeric. If it works for the majority → numeric.
        try:
            pd.to_numeric(non_null, errors="raise")
            is_numeric = True
        except (ValueError, TypeError):
            # Some values couldn't be converted — treat as text
            is_numeric = False

        # ── Numeric column → Laplace Mechanism ──────────────────────────────
        if is_numeric:
            numeric_full = pd.to_numeric(col_data, errors="coerce")
            col_min = float(numeric_full.min())
            col_max = float(numeric_full.max())

            # Sensitivity = max possible change from adding/removing one record
            sensitivity = col_max - col_min

            # Edge case: all values identical → sensitivity = 0, no noise needed
            if sensitivity == 0:
                sensitivity = 1.0  # default minimum to avoid division by zero

            noise_scale = sensitivity / epsilon

            protected_df[col] = numeric_full.apply(
                lambda v: _apply_laplace_noise(v, sensitivity, epsilon, col_min, col_max)
            )

            transformation_log.append({
                "column": col,
                "type": "NUMERIC",
                "technique": "Laplace Mechanism",
                "sensitivity": sensitivity,
                "epsilon": epsilon,
                "noise_scale": round(noise_scale, 4),
                "col_min": col_min,
                "col_max": col_max,
                "original_sample": col_data.iloc[0] if len(col_data) > 0 else None,
                "protected_sample": protected_df[col].iloc[0] if len(protected_df[col]) > 0 else None,
            })

        # ── Text column → Unchanged ──────────────────────────────────────────
        else:
            # Text Sensitive Attributes are left as-is.
            # Modules A and B already remove Direct Identifiers and generalise
            # Quasi-Identifiers, so the diagnosis can no longer be linked to a
            # specific individual. Generalising diagnoses further (e.g. "Flu"
            # → "Respiratory Condition") would reduce research utility without
            # meaningful additional privacy benefit at this stage.
            transformation_log.append({
                "column": col,
                "type": "TEXT",
                "technique": "Unchanged (original values preserved)",
                "sensitivity": "N/A (text column)",
                "epsilon": epsilon,
                "noise_scale": "N/A (text column)",
                "original_sample": col_data.iloc[0] if len(col_data) > 0 else None,
                "protected_sample": protected_df[col].iloc[0] if len(protected_df[col]) > 0 else None,
            })

    return protected_df, transformation_log


# =============================================================================
# CONVENIENCE WRAPPER
# Called by privacy_pipeline.py during full integration.
# Matches the integration interface specified in Section 6 of the manual.
# =============================================================================
def run_module_c(df: pd.DataFrame, predictions: dict, epsilon: float = 1.0,
                 random_seed: int = None) -> tuple:
    """
    Integration-ready entry point for Module C.
    Called by privacy_pipeline.py.

    Args:
        df: original dataset as DataFrame
        predictions: dict of {column_name: label} from ML model
        epsilon: privacy budget (default 1.0)
        random_seed: optional seed for reproducibility (pass same seed to get
                     identical protected output on every run — required for
                     thesis results and integration testing)

    Returns:
        (protected_df, transformation_log)
    """
    sensitive_columns = [
        col for col, label in predictions.items()
        if label == "Sensitive Attribute"
    ]
    return apply_differential_privacy(df, sensitive_columns, epsilon=epsilon,
                                      random_seed=random_seed)


# =============================================================================
# TEST SCRIPT
# Run directly: python privacy_module_c.py
# Tests three epsilon values (0.1, 1.0, 5.0) per manual Section 11.1
# =============================================================================
if __name__ == "__main__":
    import io

    print("=" * 65)
    print("DataArmor AI — Module C: Differential Privacy — Test Run")
    print("=" * 65)

    # Sample dataset from manual Section 9.1
    test_csv = """patient_name,age,zip_code,gender,diagnosis,blood_pressure,hospital_id
Aiman Ansari,21,71000,Female,Flu,120,H-001
Zoya Khan,28,71500,Female,Diabetes,140,H-002
Ahmed Ali,35,75000,Male,Hypertension,160,H-001
Sara Malik,45,71200,Female,Asthma,110,H-003
Bilal Raza,52,75100,Male,Flu,130,H-002"""

    df = pd.read_csv(io.StringIO(test_csv))

    # Predictions from manual Section 9.2
    test_predictions = {
        "patient_name": "Direct Identifier",
        "age": "Quasi-Identifier",
        "zip_code": "Quasi-Identifier",
        "gender": "Quasi-Identifier",
        "diagnosis": "Sensitive Attribute",
        "blood_pressure": "Sensitive Attribute",
        "hospital_id": "Non-PHI",
    }

    print("\nOriginal dataset:")
    print(df[["diagnosis", "blood_pressure"]].to_string())

    # ── Test three epsilon values ────────────────────────────────────────────
    for eps in [0.1, 1.0, 5.0]:
        print(f"\n{'─' * 65}")
        print(f"Epsilon = {eps}  "
              f"({'Very high privacy, high noise' if eps == 0.1 else 'Balanced' if eps == 1.0 else 'Lower privacy, low noise'})")
        print(f"{'─' * 65}")

        result_df, log = run_module_c(df.copy(), test_predictions, epsilon=eps)

        # Show before/after for sensitive columns only
        print(f"\n{'Column':<20} {'Original':<20} {'Protected':<20}")
        print(f"{'─'*20} {'─'*20} {'─'*20}")
        for entry in log:
            col = entry["column"]
            orig = entry.get("original_sample", "N/A")
            prot = entry.get("protected_sample", "N/A")
            print(f"{col:<20} {str(orig):<20} {str(prot):<20}")

        # Verify non-sensitive columns untouched
        for col, label in test_predictions.items():
            if label != "Sensitive Attribute" and col in df.columns:
                if not df[col].equals(result_df[col]):
                    print(f"  ERROR: {col} was modified but should be untouched!")

    # ── Verify diagnosis values are NOT modified ─────────────────────────────
    print(f"\n{'─' * 65}")
    print("Diagnosis integrity check — values must be UNCHANGED:")
    print(f"{'─' * 65}")
    result_df_diag, _ = run_module_c(df.copy(), test_predictions, epsilon=1.0)
    for i, (orig, prot) in enumerate(zip(df["diagnosis"], result_df_diag["diagnosis"])):
        match = "✓" if orig == prot else "✗ MISMATCH (ERROR)"
        print(f"  Row {i}: {orig:<20} → {prot:<20} {match}")

    # ── Verify non-sensitive columns were NOT modified ───────────────────────
    print(f"\n{'─' * 65}")
    print("Integrity check — non-sensitive columns must be UNCHANGED:")
    print(f"{'─' * 65}")
    result_df_final, _ = run_module_c(df.copy(), test_predictions, epsilon=1.0)
    untouched = ["patient_name", "age", "zip_code", "gender", "hospital_id"]
    for col in untouched:
        if col in df.columns:
            unchanged = df[col].equals(result_df_final[col])
            status = "✓ UNCHANGED" if unchanged else "✗ MODIFIED (ERROR)"
            print(f"  {col:<25} {status}")

    print(f"\n{'=' * 65}")
    print("Module C test complete. Ready for integration.")
    print("Files to submit:")
    print("  privacy_module_c.py   ← this file")
    print("  module_c_documentation.docx")
    print(f"{'=' * 65}")
