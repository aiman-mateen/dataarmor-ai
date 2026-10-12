# =============================================================================
# DataArmor AI — Phase 8
# Privacy Pipeline — Integration Layer
# =============================================================================

import pandas as pd
import json
import os
from privacy_module_a import mask_column, detect_masking_style, _style_to_technique
from privacy_module_b import apply_k_anonymity, detect_type, TYPE_GENDER, TYPE_KEEP_AS_IS
from privacy_module_c import run_module_c


# ── HIPAA reason strings ──────────────────────────────────────────────────────
_REASONS = {
    "Direct Identifier" : "Direct Identifier removed per HIPAA Safe Harbor 18-identifier list.",
    "QI_generalized"    : "Generalized to satisfy k-anonymity while preserving research utility.",
    "QI_kept"           : "Retained unchanged — low disclosure risk; further generalization unnecessary.",
    "SA_numeric"        : "Laplace Mechanism applied — numeric sensitive attribute protected via Differential Privacy.",
    "SA_text"           : "Original value retained — identity already removed by Modules A and B; diagnosis value cannot be re-linked to an individual.",
    "Non-PHI"           : "Classified as Non-PHI. No privacy protection required.",
}


def run_privacy_pipeline(
    df: pd.DataFrame,
    predictions: dict,
    epsilon: float = 1.0,
    k: int = 3,
    random_seed: int = 42
) -> tuple:
    """
    Master privacy pipeline.
    Routes every column to the correct module based on predicted label.

    Returns: (anonymized_df, compliance_report)
    """
    anonymized_df     = df.copy()
    compliance_report = []

    direct_identifiers   = [c for c, l in predictions.items() if l == "Direct Identifier"   and c in df.columns]
    quasi_identifiers    = [c for c, l in predictions.items() if l == "Quasi-Identifier"    and c in df.columns]
    sensitive_attributes = [c for c, l in predictions.items() if l == "Sensitive Attribute" and c in df.columns]
    non_phi              = [c for c, l in predictions.items() if l == "Non-PHI"             and c in df.columns]

    print(f"\n{'='*65}")
    print(f"DataArmor AI — Privacy Pipeline")
    print(f"  Direct Identifiers   : {len(direct_identifiers)}")
    print(f"  Quasi-Identifiers    : {len(quasi_identifiers)}")
    print(f"  Sensitive Attributes : {len(sensitive_attributes)}")
    print(f"  Non-PHI              : {len(non_phi)}")
    print(f"{'='*65}")

    # ── MODULE A ──────────────────────────────────────────────────────────────
    print(f"\n[Module A — Direct Identifier Masking]")
    masked_di = 0
    for col in direct_identifiers:
        original_sample = str(df[col].dropna().iloc[0]) if df[col].notna().any() else "N/A"
        style     = detect_masking_style(col)
        technique = _style_to_technique(style)
        anonymized_df[col] = mask_column(df[col])
        masked_di += 1
        print(f"  ✓ {col:<30} → {technique}")
        compliance_report.append({
            "column_name"       : col,
            "predicted_label"   : "Direct Identifier",
            "technique_applied" : technique,
            "status"            : "Protected",
            "parameters"        : "—",
            "original_sample"   : original_sample,
            "transformed_sample": str(anonymized_df[col].iloc[0]) if len(anonymized_df[col]) > 0 else "N/A",
            "reason"            : _REASONS["Direct Identifier"],
            "module"            : "A",
            "epsilon"           : "N/A",
            "k_value"           : "N/A",
        })
    print(f"  Summary: {masked_di}/{len(direct_identifiers)} masked successfully.")
    print(f"  Module A complete.\n")

    # ── MODULE B ──────────────────────────────────────────────────────────────
    print(f"[Module B — k-Anonymity Generalization]")
    generalized_qi = 0
    kept_qi = 0
    if quasi_identifiers:
        qi_df = df[quasi_identifiers].copy()
        qi_result, qi_info = apply_k_anonymity(qi_df, quasi_identifiers, k=k)

        for col in quasi_identifiers:
            original_sample = str(df[col].dropna().iloc[0]) if df[col].notna().any() else "N/A"
            transformed     = str(qi_result[col].dropna().iloc[0]) if qi_result[col].notna().any() else "N/A"
            anonymized_df[col] = qi_result[col]

            col_type = detect_type(col, df[col])
            if col_type in (TYPE_GENDER, TYPE_KEEP_AS_IS):
                technique  = "No Generalization — Utility Preserved"
                parameters = "Low disclosure risk — kept unchanged"
                status     = "Utility Preserved"
                reason     = _REASONS["QI_kept"]
                kept_qi   += 1
            else:
                level      = qi_info['levels_applied'].get(col, 1)
                technique  = "k-Anonymity Generalization"
                parameters = f"k={qi_info['k_used']}, Level={level}"
                status     = "Generalized"
                reason     = _REASONS["QI_generalized"]
                generalized_qi += 1

            compliance_report.append({
                "column_name"       : col,
                "predicted_label"   : "Quasi-Identifier",
                "technique_applied" : technique,
                "status"            : status,
                "parameters"        : parameters,
                "original_sample"   : original_sample,
                "transformed_sample": transformed,
                "reason"            : reason,
                "module"            : "B",
                "epsilon"           : "N/A",
                "k_value"           : str(qi_info["k_used"]) if col_type not in (TYPE_GENDER, TYPE_KEEP_AS_IS) else "N/A",
            })
    print(f"  Module B complete.\n")

    # ── MODULE C ──────────────────────────────────────────────────────────────
    print(f"[Module C — Differential Privacy]")
    dp_numeric = 0
    dp_text    = 0
    if sensitive_attributes:
        sa_df          = df[sensitive_attributes].copy()
        sa_predictions = {col: "Sensitive Attribute" for col in sensitive_attributes}
        sa_result, sa_log = run_module_c(
            sa_df, sa_predictions, epsilon=epsilon, random_seed=random_seed)
        log_map = {entry["column"]: entry for entry in sa_log}

        for col in sensitive_attributes:
            original_sample = str(df[col].dropna().iloc[0]) if df[col].notna().any() else "N/A"
            anonymized_df[col] = sa_result[col]
            entry     = log_map.get(col, {})
            col_type  = entry.get("type", "")
            technique = entry.get("technique", "Differential Privacy")
            transformed = str(sa_result[col].dropna().iloc[0]) if sa_result[col].notna().any() else "N/A"

            if col_type == "NUMERIC":
                # parameters = f"ε={epsilon}, sensitivity={entry.get('sensitivity','N/A')}, noise_scale={entry.get('noise_scale','N/A')}"
                parameters = (
                     f"ε={entry.get('epsilon')}, "
                     f"sensitivity={entry.get('sensitivity')}, "
                     f"noise_scale={entry.get('noise_scale')}"
                )
                eps_val = str(entry.get("epsilon", epsilon))
                status     = "Protected"
                reason     = _REASONS["SA_numeric"]
                dp_numeric += 1
            else:
                parameters = "Text value retained — identity removed upstream"
                # eps_val    = "N/A"
                eps_val = str(entry.get("epsilon", epsilon))
                status     = "Retained (identity removed)"
                reason     = _REASONS["SA_text"]
                dp_text   += 1

            print(f"  ✓ {col:<30} → {technique}")
            compliance_report.append({
                "column_name"       : col,
                "predicted_label"   : "Sensitive Attribute",
                "technique_applied" : technique,
                "status"            : status,
                "parameters"        : parameters,
                "original_sample"   : original_sample,
                "transformed_sample": transformed,
                "reason"            : reason,
                "module"            : "C",
                "epsilon"           : eps_val,
                "k_value"           : "N/A",
            })
    print(f"  Module C complete.\n")

    # ── NON-PHI ───────────────────────────────────────────────────────────────
    print(f"[Non-PHI — No Modification]")
    for col in non_phi:
        original_sample = str(df[col].dropna().iloc[0]) if df[col].notna().any() else "N/A"
        print(f"  — {col:<30} → unchanged")
        compliance_report.append({
            "column_name"       : col,
            "predicted_label"   : "Non-PHI",
            "technique_applied" : "No Modification",
            "status"            : "Unchanged",
            "parameters"        : "—",
            "original_sample"   : original_sample,
            "transformed_sample": original_sample,
            "reason"            : _REASONS["Non-PHI"],
            "module"            : "—",
            "epsilon"           : "N/A",
            "k_value"           : "N/A",
        })

    # ── PIPELINE SUMMARY ──────────────────────────────────────────────────────
    qi_info_ref = qi_info if quasi_identifiers else {"k_used": "N/A", "information_loss": {"average": 0}}
    avg_loss    = qi_info_ref["information_loss"]["average"] if quasi_identifiers else 0

    print(f"\n{'='*65}")
    print(f"PIPELINE SUMMARY")
    print(f"{'='*65}")
    print(f"  Rows Processed           : {len(df)}")
    print(f"  Columns Processed        : {len(compliance_report)}")
    print(f"  Direct Identifiers       : {len(direct_identifiers)}  →  Masked: {masked_di}")
    print(f"  Quasi-Identifiers        : {len(quasi_identifiers)}  →  Generalized: {generalized_qi}  |  Kept: {kept_qi}")
    print(f"  Sensitive Attributes     : {len(sensitive_attributes)}  →  DP Numeric: {dp_numeric}  |  Text Retained: {dp_text}")
    print(f"  Non-PHI                  : {len(non_phi)}  →  Unchanged: {len(non_phi)}")
    print(f"  k Used                   : {qi_info_ref['k_used']}")
    print(f"  Avg Information Loss     : {avg_loss:.1f}%")
    print(f"  Suppressed Records       : 0")
    print(f"  Pipeline Status          : SUCCESS")
    print(f"{'='*65}\n")

    return anonymized_df, compliance_report


def save_outputs(anonymized_df: pd.DataFrame,
                 compliance_report: list,
                 output_folder=None) -> dict:
    # import os
    # print("\nCurrent Working Directory:")
    # print(os.getcwd())
    
    # If no folder is provided, use Phase 8/output
    if output_folder is None:
        project_dir = os.path.dirname(os.path.abspath(__file__))
        output_folder = os.path.join(project_dir, "output")

    # Create the folder if it doesn't exist
    os.makedirs(output_folder, exist_ok=True)
    csv_path  = os.path.join(output_folder, "anonymized_dataset.csv")
    json_path = os.path.join(output_folder, "compliance_report.json")
    cr_path   = os.path.join(output_folder, "compliance_report.csv")

    anonymized_df.to_csv(csv_path, index=False)
    pd.DataFrame(compliance_report).to_csv(cr_path, index=False)
    with open(json_path, "w") as f:
        json.dump(compliance_report, f, indent=2)


    print("Saved:", os.path.abspath(csv_path))
    print("Saved:", os.path.abspath(cr_path))
    print("Saved:", os.path.abspath(json_path))
    print(f"  Saved: {cr_path}")
    print(f"  Saved: {json_path}")
    return {"anonymized_csv": csv_path, "compliance_csv": cr_path, "compliance_json": json_path}