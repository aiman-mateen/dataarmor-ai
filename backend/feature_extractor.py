import pandas as pd
import numpy as np
import re
import warnings
warnings.filterwarnings("ignore")


# ─────────────────────────────────────────────────────


PATTERN_MAP = {
    "Numeric":      0,
    "Alphabetic":   1,
    "Alphanumeric": 2,
    "Text":         3,
    "Date":         4,
    "Boolean":      5,
    "Phone":        6,
    "Email":        7,
    "Code":         8,
}

# -------------------------
# HELPER: Standardize column names
# -------------------------
def standardize_column_name(name):
    name = str(name).strip().lower()
    name = re.sub(r'\s+', '_', name)
    name = re.sub(r'[^\w_]', '', name)
    return name


# -------------------------
# HELPER: Make column names unique within a dataset
# -------------------------
def make_unique_names(names):
    seen = {}
    result = []
    for name in names:
        if name not in seen:
            seen[name] = 1
            result.append(name)
        else:
            seen[name] += 1
            result.append(f"{name}_{seen[name]}")
    return result


# -------------------------
# HELPER: Entropy (unchanged — already correct)
# -------------------------
def calculate_entropy(series):
    if series.empty:
        return 0.0
    vc = series.value_counts(normalize=True, dropna=True)
    return float(-(vc * np.log2(vc + 1e-9)).sum())


# -------------------------
# HELPER: Character-level numeric ratio (FIX for Bug 1 + Bug 4)
#
# For each non-null value, count how many characters are digits (0-9),
# divide by total number of characters in that value (excluding separators
# like dash, slash, dot, space which are structural not meaningful).
# Then average across all non-null rows.
#
# Examples:
#   "ABC-123"          → 3 digits / 6 total (excl dash) = 0.500
#   UUID "3a4f2c91-..."→ ~8 digits / 32 hex chars       = 0.250
#   "120/80 mmHg"      → 5 digits / 10 alpha+digit      = 0.500
#   "E11.9" (ICD-10)   → 3 digits / 5 total (excl dot)  = 0.600
#   "COMPLETED"        → 0 digits / 9 letters            = 0.000
#   "12345"            → 5 digits / 5 total              = 1.000
#   "john@email.com"   → 0 digits / 13 alpha+at+dot      = 0.000
#   "user123@mail.com" → 3 digits / 16 total             = 0.188
# -------------------------
def compute_numeric_ratio(series):
    """
    Character-level digit proportion.
    Computed on non-null values only.
    Returns float in [0.0, 1.0].
    """
    non_null = series.dropna().astype(str)
    non_null = non_null[non_null.str.strip() != ""]

    if len(non_null) == 0:
        return 0.0

    def char_digit_ratio(s):
        # Count only letters and digits — structural separators don't count
        meaningful_chars = re.sub(r'[\s\-_/.,@:#\+\(\)\[\]]', '', s)
        if len(meaningful_chars) == 0:
            return 0.0
        digit_count = sum(1 for c in meaningful_chars if c.isdigit())
        return digit_count / len(meaningful_chars)

    ratios = non_null.apply(char_digit_ratio)
    return round(float(ratios.mean()), 4)


# -------------------------
# HELPER: Outlier ratio using IQR or Z-score (FIX for Bug 2 + Bug 3)
#
# - Always excludes null values first
# - Uses IQR method by default
# - Switches to Z-score (threshold 3.5) when variance > 10,000
#   because IQR breaks on wide-range distributions (e.g. dosage 0.5mg–1000mg,
#   billing amounts $10–$500,000)
# - Returns 0.0 for columns with fewer than 4 non-null numeric values
# -------------------------
def compute_outlier_ratio(numeric_series_non_null):
    """
    numeric_series_non_null: pd.Series of numeric values with nulls already dropped.
    Returns float in [0.0, 1.0].
    """
    n = len(numeric_series_non_null)
    if n < 4:
        return 0.0

    variance = numeric_series_non_null.var()

    if variance > 10000:
        # Z-score method for wide-range distributions
        mean = numeric_series_non_null.mean()
        std  = numeric_series_non_null.std()
        if std == 0:
            return 0.0
        z_scores = ((numeric_series_non_null - mean) / std).abs()
        outlier_count = (z_scores > 3.5).sum()
    else:
        # IQR method for normal-range distributions
        q1 = numeric_series_non_null.quantile(0.25)
        q3 = numeric_series_non_null.quantile(0.75)
        iqr = q3 - q1
        if iqr == 0:
            return 0.0
        lower = q1 - 1.5 * iqr
        upper = q3 + 1.5 * iqr
        outlier_count = ((numeric_series_non_null < lower) |
                         (numeric_series_non_null > upper)).sum()

    return round(float(outlier_count / n), 4)


# -------------------------
# PATTERN DETECTION (unchanged from working version)
# Returns: (pattern_type_str, pattern_code_int, data_type_str)
# -------------------------
def detect_pattern_and_type(series, col_name):
    sample = series.dropna().astype(str)
    if sample.empty:
        return "Text", PATTERN_MAP["Text"], "String"

    test_data = sample.sample(min(len(sample), 500), random_state=42)
    col = col_name.lower()

    # STEP 1 — Column name hints (highest priority)

    if col in ["start", "stop", "startdate", "stopdate", "start_date", "stop_date"]:
        return "Date", PATTERN_MAP["Date"], "Date"

    if col == "code" or col.endswith("_code"):
        return "Code", PATTERN_MAP["Code"], "Alphanumeric"

    if col in ["npi", "ssn", "reasoncode", "reason_code", "bodysite_code"]:
        return "Code", PATTERN_MAP["Code"], "Alphanumeric"

    if col.endswith("_id") or col in ["id", "mrn", "claim_id", "member_id", "patient_id"]:
        return "Code", PATTERN_MAP["Code"], "Alphanumeric"

    if "county" in col:
        return "Alphabetic", PATTERN_MAP["Alphabetic"], "String"

    if any(x in col for x in ["healthcare_expenses", "expense", "expenses",
                               "revenue", "start_year", "end_year", "year"]):
        return "Numeric", PATTERN_MAP["Numeric"], "Numeric"

    if "birthplace" in col:
        return "Text", PATTERN_MAP["Text"], "String"

    if "admission_type" in col or ("type" in col and "admission" in col):
        return "Alphabetic", PATTERN_MAP["Alphabetic"], "String"

    # FIX 2A: language is always a spoken/written language string
    if col == "language":
        return "Alphabetic", PATTERN_MAP["Alphabetic"], "String"

    # FIX 2E+2F: specific encounter field names — MUST come BEFORE generic encounter rule
    if col in ["encounter_status", "encounter_class", "clinical_status",
               "verification_status", "marital_status"]:
        return "Alphabetic", PATTERN_MAP["Alphabetic"], "String"

    # FIX: all _status suffix columns are alphabetic — MUST come before generic encounter rule
    if col == "status" or col.endswith("_status"):
        return "Alphabetic", PATTERN_MAP["Alphabetic"], "String"

    # FIX 2G: _display columns are always text — MUST come before generic encounter rule
    if col.endswith("_display"):
        return "Text", PATTERN_MAP["Text"], "String"

    # FIX 2K: _text columns are free-text strings
    if col.endswith("_text") or "_text_" in col:
        return "Text", PATTERN_MAP["Text"], "String"

    # Generic encounter rule — placed AFTER all specific encounter field fixes above
    if "encounter" in col and not col.endswith("_id"):
        return "Alphanumeric", PATTERN_MAP["Alphanumeric"], "Alphanumeric"

    if col in ["patient_number", "patient_mrn"] or col.endswith("patient_id"):
        return "Code", PATTERN_MAP["Code"], "Alphanumeric"
    elif "patient" in col and not col.endswith("name"):
        return "Alphanumeric", PATTERN_MAP["Alphanumeric"], "Alphanumeric"

    date_col_hits = ["date", "dob", "birth", "registration",
                     "admit_date", "discharge_date", "datetime"]
    if any(x in col for x in date_col_hits):
        return "Date", PATTERN_MAP["Date"], "Date"

    if "email" in col:
        return "Email", PATTERN_MAP["Email"], "Email"

    if any(x in col for x in ["phone", "contact", "mobile", "fax"]):
        return "Phone", PATTERN_MAP["Phone"], "Phone"

    if any(x in col for x in ["zip", "postal", "postcode"]):
        return "Code", PATTERN_MAP["Code"], "Code"

    if any(x in col for x in ["amount", "cost", "price", "age", "salary",
                               "count", "rate", "score", "length_of_stay",
                               "dose_value", "days_supply", "number_of_repeats",
                               "value_numeric", "reference_range"]):
        return "Numeric", PATTERN_MAP["Numeric"], "Numeric"

    # STEP 2 — Content-based detection

    unique_vals = set(test_data.str.strip().str.lower().unique())
    bool_vals = {'0', '1', 'true', 'false', 'yes', 'no', 'y', 'n'}
    if unique_vals.issubset(bool_vals) and len(unique_vals) <= 4:
        return "Boolean", PATTERN_MAP["Boolean"], "Boolean"

    if test_data.str.match(r'^[^@\s]+@[^@\s]+\.[^@\s]+$').mean() > 0.8:
        return "Email", PATTERN_MAP["Email"], "Email"

    cleaned_phone = test_data.str.replace(r'[^\d]', '', regex=True)
    phone_digits  = cleaned_phone.str.len().between(7, 15).mean()
    has_letters   = test_data.str.contains(r'[A-Za-z]', regex=True).mean()
    if phone_digits > 0.85 and has_letters < 0.05:
        return "Phone", PATTERN_MAP["Phone"], "Phone"

    date_patterns = [
        r'\d{4}-\d{2}-\d{2}',
        r'\d{2}/\d{2}/\d{4}',
        r'\d{4}-\d{2}-\d{2}T\d{2}:\d{2}',   # ISO datetime
    ]
    date_hit = any(test_data.str.contains(p, regex=True).mean() > 0.6
                   for p in date_patterns)
    if date_hit:
        return "Date", PATTERN_MAP["Date"], "Date"

    numeric_conv  = pd.to_numeric(test_data, errors='coerce')
    numeric_ratio = numeric_conv.notna().mean()
    has_units     = test_data.str.contains(r'\d+\s*[A-Za-z]', regex=True).mean()
    if numeric_ratio > 0.9 and has_units < 0.1:
        return "Numeric", PATTERN_MAP["Numeric"], "Numeric"

    if test_data.str.contains(r'^[A-Z0-9]+\.[A-Z0-9]+$', regex=True).mean() > 0.7:
        return "Code", PATTERN_MAP["Code"], "Alphanumeric"

    alpha_ratio = test_data.str.match(r'^[A-Za-z\s/]+$').mean()
    if alpha_ratio > 0.8:
        return "Alphabetic", PATTERN_MAP["Alphabetic"], "String"

    def has_both(s):
        s_clean = re.sub(r'[\-_\s]', '', s)
        return bool(re.search(r'[A-Za-z]', s_clean) and re.search(r'\d', s_clean))

    alnum_ratio = test_data.apply(has_both).mean()
    if alnum_ratio > 0.6:
        return "Alphanumeric", PATTERN_MAP["Alphanumeric"], "Alphanumeric"

    return "Text", PATTERN_MAP["Text"], "String"


# -------------------------
# FEATURE EXTRACTION — all bugs fixed
# -------------------------
def extract_features(series, col_name, dataset_name):
    total_rows = len(series)
    if total_rows == 0:
        return None

    col_name_clean = standardize_column_name(col_name)
    pattern_type, pattern_code, data_type = detect_pattern_and_type(series, col_name)

    # ── NULL RATIO (computed first — used as base for all other fixes) ────────
    null_ratio = round(float(series.isna().mean()), 4)

    # ── NON-NULL SERIES (used for all feature computations below) ────────────
    # FIX Bug 3+4+6+7: all features computed on non-null values only
    non_null_series = series.dropna()
    non_null_str    = non_null_series.astype(str)
    non_null_str    = non_null_str[non_null_str.str.strip() != ""]

    # ── UNIQUENESS (denominator = total rows, consistent with existing table) ─
    unique_count         = series.nunique()
    uniqueness_ratio     = round(unique_count / total_rows, 4)
    distinct_to_row_ratio = round(unique_count / total_rows, 4)  # same formula, kept for schema compat

    # ── ENTROPY (already correct — dropna handled inside) ────────────────────
    entropy = round(calculate_entropy(series), 4)

    # ── LENGTH FEATURES (FIX Bug 6: non-null non-empty only) ─────────────────
    if len(non_null_str) > 0:
        lengths     = non_null_str.str.len()
        mean_len    = round(float(lengths.mean()), 2)
        std_dev_len = round(float(lengths.std()), 2) if len(non_null_str) > 1 else 0.0
    else:
        mean_len    = 0.0
        std_dev_len = 0.0

    # ── SPECIAL CHARS (FIX Bug 7: non-null values only) ──────────────────────
    if len(non_null_str) > 0:
        has_spec = int(
            non_null_str.str.contains(r'[@\-/#\+\(\)]', regex=True).mean() > 0.1
        )
    else:
        has_spec = 0

    # ── IS ALL CAPS (already correct in original — kept as-is) ───────────────
    is_caps = int(non_null_str.str.isupper().mean() > 0.5) if len(non_null_str) > 0 else 0

    # ── NUMERIC RATIO (FIX Bug 1+4: character-level, non-null denominator) ───
    numeric_ratio = compute_numeric_ratio(series)

    # ── OUTLIER RATIO & VARIANCE (FIX Bug 2+3+5) ─────────────────────────────
    if data_type == "Numeric":
        # Convert non-null values to numeric, drop any that fail conversion
        numeric_vals = pd.to_numeric(non_null_series, errors='coerce').dropna()

        if len(numeric_vals) > 1:
            variance      = round(float(numeric_vals.var()), 4)
            outlier_ratio = compute_outlier_ratio(numeric_vals)
        else:
            variance      = 0.0
            outlier_ratio = 0.0
    else:
        # FIX Bug 12: use -1 not "-" for non-numeric columns
        outlier_ratio = 0.0
        variance      = -1

    # exclude_from_training:
    # 1 if null_ratio=1.0 (completely empty)
    # 1 if entropy=0 AND uniqueness<0.005 (effectively constant — catches near-zero uniqueness)
    # 1 if null_ratio > 0.80 (too sparse to be informative)
    exclude = 1 if (
        null_ratio == 1.0 or
        (entropy == 0.0 and uniqueness_ratio < 0.005) or
        null_ratio > 0.80
    ) else 0

    return {
        "column_name":            col_name_clean,
        "dataset_name":           dataset_name,
        "pattern_type":           pattern_type,
        "pattern_code":           pattern_code,
        "data_type":              data_type,
        "uniqueness_ratio":       uniqueness_ratio,
        "distinct_to_row_ratio":  distinct_to_row_ratio,
        "entropy":                entropy,
        "mean_length":            mean_len,
        "std_dev_length":         std_dev_len,
        "has_special_chars":      has_spec,
        "is_all_caps":            is_caps,
        "numeric_ratio":          numeric_ratio,
        "null_ratio":             null_ratio,
        "outlier_ratio":          outlier_ratio,
        "variance":               variance,
        "exclude_from_training":  exclude,
    }


TRAINING_COLUMNS = [
    'uniqueness_ratio', 'distinct_to_row_ratio', 'entropy',
    'mean_length', 'std_dev_length', 'has_special_chars',
    'is_all_caps', 'numeric_ratio', 'null_ratio', 'outlier_ratio',
    'variance',
    'pattern_Alphabetic', 'pattern_Alphanumeric', 'pattern_Boolean',
    'pattern_Code', 'pattern_Date', 'pattern_Email', 'pattern_Numeric',
    'pattern_Phone', 'pattern_Text',
    'dtype_Alphabetic', 'dtype_Alphanumeric', 'dtype_Boolean',
    'dtype_Code', 'dtype_Date', 'dtype_Email', 'dtype_Numeric',
    'dtype_Phone', 'dtype_String'
]


def extract_features_for_inference(csv_path: str):
    """
    Takes a CSV file path.
    Returns:
        features_df  — raw features before preprocessing
        column_names — list of column names in order
    """
    df = pd.read_csv(csv_path, low_memory=False)

    rows = []
    column_names = []

    standardized = [standardize_column_name(c) for c in df.columns]
    unique_names = make_unique_names(standardized)

    for original_col, unique_col in zip(df.columns, unique_names):
        feature_row = extract_features(
            df[original_col], unique_col, "uploaded_dataset"
        )
        if feature_row:
            rows.append(feature_row)
            column_names.append(unique_col)

    features_df = pd.DataFrame(rows)

    # Remove columns flagged for exclusion
    features_df = features_df[
        features_df['exclude_from_training'] == 0
    ].reset_index(drop=True)

    # Update column names list to match filtered rows
    filtered_names = features_df['column_name'].tolist()

    return features_df, filtered_names


def preprocess_for_model(features_df: pd.DataFrame) -> pd.DataFrame:
    """
    Converts raw feature dataframe into the exact format
    the models were trained on.
    One-hot encodes pattern_type and data_type.
    Aligns to TRAINING_COLUMNS exactly.
    Ensures all values are numeric integers or floats.
    """
    df = features_df.copy()

    # Drop columns not used in training
    drop_cols = [
        'column_name', 'dataset_name',
        'exclude_from_training', 'pattern_code'
    ]
    df = df.drop(
        columns=[c for c in drop_cols if c in df.columns]
    )

    # One-hot encode pattern_type — force integer output
    pattern_dummies = pd.get_dummies(
        df['pattern_type'], prefix='pattern'
    ).astype(int)

    # One-hot encode data_type — force integer output
    dtype_dummies = pd.get_dummies(
        df['data_type'], prefix='dtype'
    ).astype(int)

    # Drop original string columns
    df = df.drop(columns=['pattern_type', 'data_type'])

    # Combine numeric features with encoded columns
    df = pd.concat([df, pattern_dummies, dtype_dummies], axis=1)

    # Add any missing training columns as 0
    for col in TRAINING_COLUMNS:
        if col not in df.columns:
            df[col] = 0

    # Keep only training columns in exact order
    df = df[TRAINING_COLUMNS]

    # Force all columns to numeric — convert any remaining booleans
    df = df.apply(pd.to_numeric, errors='coerce').fillna(0)

    return df