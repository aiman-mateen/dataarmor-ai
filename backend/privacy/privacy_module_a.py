# =============================================================================
# DataArmor AI — Phase 8
# Module A: Direct Identifier Masking
# Assigned to: Aiman
#
# CHANGES FROM v1:
#   - Email masking now preserves the domain (****@gmail.com not ****@****.com)
#   - ID masking uses [ID REDACTED] instead of ID-XXXXX (more professional)
#   - mask_column() returns a tuple (masked_series, log_entry) for pipeline
#   - Masking style labels match compliance report Module/Parameters columns
# =============================================================================

import pandas as pd
import re


def detect_masking_style(col_name: str) -> str:
    """
    Determines masking style from column name.
    Returns a style string used by apply_mask().
    Falls back to REDACTED for anything not specifically recognized.
    """
    col = col_name.lower().replace(' ', '_').replace('.', '_').replace('-', '_')

    if any(p in col for p in ['phone', 'mobile', 'tel', 'telephone', 'fax',
                               'contact_no', 'contact_number', 'ph_no', 'cell']):
        return 'PHONE'

    if any(p in col for p in ['cnic', 'nic', 'national_id', 'national_identity',
                               'id_card', 'idcard', 'identity_number']):
        return 'CNIC'

    if any(p in col for p in ['ssn', 'social_security', 'social_sec']):
        return 'SSN'

    if any(p in col for p in ['email', 'e_mail', 'mail', 'email_address']):
        return 'EMAIL'

    if any(p in col for p in ['_id', 'id_', 'pid', 'mrn', 'medical_record',
                               'record_no', 'record_number', 'case_id',
                               'account_no', 'member_id', 'patient_no']):
        return 'ID'

    if any(p in col for p in ['address', 'addr', 'street', 'residence',
                               'home_address', 'current_address']):
        return 'ADDRESS'

    # Covers: name, first_name, last_name, dob, passport, license, etc.
    return 'REDACTED'


def apply_mask(value, style: str) -> str:
    """
    Applies masking to a single value based on style.
    Preserves nulls and empty strings.
    For EMAIL: preserves the domain portion (****@gmail.com).
    """
    if pd.isna(value) or str(value).strip() == "":
        return value

    val_str = str(value).strip()

    if style == 'PHONE':
        return "***-***-****"

    elif style == 'CNIC':
        return "***-*****-*"

    elif style == 'SSN':
        return "***-**-****"

    elif style == 'EMAIL':
        # Preserve domain for research utility
        # aiman@gmail.com → ****@gmail.com
        if '@' in val_str:
            domain = val_str.split('@', 1)[1]
            return f"****@{domain}"
        return "****@****.***"

    elif style == 'ID':
        return "[ID REDACTED]"

    elif style == 'ADDRESS':
        return "[ADDRESS REDACTED]"

    else:
        # REDACTED — covers names, DOB, passport, license, any other DI
        return "[REDACTED]"


def _style_to_technique(style: str) -> str:
    """Returns human-readable technique label for compliance report."""
    return {
        'PHONE':   'Pattern Masking (Phone)',
        'CNIC':    'Pattern Masking (CNIC)',
        'SSN':     'Pattern Masking (SSN)',
        'EMAIL':   'Email Masking (domain preserved)',
        'ID':      'ID Redaction',
        'ADDRESS': 'Address Redaction',
        'REDACTED':'Full Redaction',
    }.get(style, 'Full Redaction')


def mask_column(series: pd.Series) -> pd.Series:
    """
    Pipeline entry point — called by privacy_pipeline.py.
    Receives a Series, returns a masked Series.
    Column name is used to detect masking style.
    """
    style = detect_masking_style(series.name)
    return series.apply(lambda x: apply_mask(x, style))


def mask_column_with_log(series: pd.Series) -> tuple:
    """
    Extended version that also returns log info for the compliance report.
    Returns: (masked_series, log_dict)
    """
    style  = detect_masking_style(series.name)
    masked = series.apply(lambda x: apply_mask(x, style))
    log = {
        "style":     style,
        "technique": _style_to_technique(style),
        "module":    "A",
        "parameters": "—",
    }
    return masked, log


def mask_direct_identifiers(df: pd.DataFrame,
                             direct_columns: list) -> tuple:
    """
    Masks all Direct Identifier columns in the DataFrame.
    Prints a summary of what was applied to each column.

    Returns:
        (masked_df, module_log)
        module_log: list of dicts, one per column
    """
    df_masked  = df.copy()
    module_log = []

    print(f"\n[Module A — Direct Identifier Masking]")
    print(f"  Columns to mask: {len(direct_columns)}")

    for col in direct_columns:
        if col not in df_masked.columns:
            print(f"  WARNING: '{col}' not found — skipping")
            continue
        style     = detect_masking_style(col)
        technique = _style_to_technique(style)
        df_masked[col] = df_masked[col].apply(lambda x: apply_mask(x, style))
        module_log.append({
            "column":     col,
            "style":      style,
            "technique":  technique,
            "module":     "A",
            "parameters": "—",
        })
        print(f"  ✓ {col:<30} Technique: {technique}")

    print(f"  Module A complete.\n")
    return df_masked, module_log


# =============================================================================
# TEST
# =============================================================================
if __name__ == "__main__":
    import io

    test_data = {
        "patient_name":  ["Aiman Ansari", "Zoya Khan", "Ahmed Ali"],
        "email":         ["aiman@gmail.com", "zoya@hotmail.com", "ahmed@yahoo.com"],
        "phone":         ["0300-1234567", "0321-9876543", "0311-5555555"],
        "cnic":          ["42201-1234567-1", "42201-9876543-2", "42201-5555555-3"],
        "patient_id":    ["P-001", "P-002", "P-003"],
        "address":       ["House 12, Street 5", "Flat 3B, Block C", "Bungalow 7"],
        "diagnosis":     ["Flu", "Diabetes", "Hypertension"],
    }
    df = pd.DataFrame(test_data)

    print("Original:")
    print(df.drop(columns=["diagnosis"]).to_string(index=False))

    di_cols = ["patient_name", "email", "phone", "cnic", "patient_id", "address"]
    masked_df, log = mask_direct_identifiers(df, di_cols)

    print("\nAfter Masking:")
    print(masked_df.drop(columns=["diagnosis"]).to_string(index=False))

    print("\nDiagnosis unchanged:")
    print(f"  {list(masked_df['diagnosis']) == list(df['diagnosis'])}")