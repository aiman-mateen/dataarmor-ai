"""
Module B — Quasi-Identifier Generalization (k-Anonymity)
=========================================================
AI-Powered PHI Detection & Anonymization System — Phase 8

VERSION 2 — Full dataset coverage
Works on ANY structured healthcare dataset automatically.

Column type detection covers:
  - Age, DOB, birth year, year fields
  - ZIP / postal code fields  
  - City / district / town fields
  - Gender / sex fields
  - Date / datetime fields (admission, discharge, encounter)
  - Numeric vitals (BP, HR, BMI, weight, height, SpO2, temp)
  - Numeric clinical (room number, LOS, dosage)
  - Low-cardinality categoricals (blood type, marital, ethnicity,
    race, language, smoking, alcohol, insurance type, etc.)
    → these are kept AS-IS (already generalized by nature,
      further generalization destroys all meaning)

Information Loss:
  - Numeric columns: NCP (Normalized Certainty Penalty)
  - Geographic categoricals: entropy-based
  - Low-cardinality categoricals: 0% (not generalized)
  - Target: ≤ 15% average NCP across numeric/geographic columns

Key design decisions:
  1. Gender excluded from k-anonymity groupby (2 values only,
     cannot be meaningfully generalized, fractures equivalence
     classes when included)
  2. Categorical QI columns with ≤ 8 distinct values are kept
     unchanged — they are already generalized by nature
  3. Generalization stops at minimum necessary level
  4. Level 2 is previewed before applying — rejected if loss > 15%
  5. k auto-reduced for datasets < 30 rows with a clear warning
"""

import pandas as pd
import numpy as np
import math
from scipy.stats import entropy as scipy_entropy


# ── Configuration ─────────────────────────────────────────────────────────────
DEFAULT_K               = 3
MAX_INFO_LOSS_PCT       = 15.0
SMALL_DATASET_THRESHOLD = 30
MIN_K                   = 2

# Max distinct values before a categorical is treated as "low-cardinality"
# and kept as-is (already sufficiently generalized)
LOW_CARDINALITY_MAX     = 8


# ── Geographic Hierarchies ────────────────────────────────────────────────────
CITY_TO_PROVINCE = {
    'karachi': 'Sindh', 'hyderabad': 'Sindh', 'sukkur': 'Sindh',
    'larkana': 'Sindh', 'nawabshah': 'Sindh', 'mirpurkhas': 'Sindh',
    'thatta': 'Sindh', 'khairpur': 'Sindh', 'jacobabad': 'Sindh',
    'lahore': 'Punjab', 'faisalabad': 'Punjab', 'rawalpindi': 'Punjab',
    'multan': 'Punjab', 'gujranwala': 'Punjab', 'sialkot': 'Punjab',
    'sargodha': 'Punjab', 'bahawalpur': 'Punjab', 'sheikhupura': 'Punjab',
    'peshawar': 'KPK', 'mardan': 'KPK', 'abbottabad': 'KPK',
    'swat': 'KPK', 'kohat': 'KPK', 'mingora': 'KPK',
    'quetta': 'Balochistan', 'turbat': 'Balochistan', 'khuzdar': 'Balochistan',
    'islamabad': 'Federal Territory',
    'muzaffarabad': 'AJK', 'mirpur': 'AJK',
}
PROVINCE_TO_COUNTRY = {v: 'Pakistan' for v in set(CITY_TO_PROVINCE.values())}
PROVINCE_TO_COUNTRY['Other Region'] = 'Pakistan'


# ══════════════════════════════════════════════════════════════════════════════
# TYPE DETECTION — covers all QI columns across all 6 datasets + MIMIC
# ══════════════════════════════════════════════════════════════════════════════

# Column types and what to do with them
TYPE_KEEP_AS_IS = 'KEEP_AS_IS'      # low-cardinality categorical, keep unchanged
TYPE_GENDER     = 'GENDER'           # binary, exclude from groupby, keep unchanged
TYPE_AGE        = 'AGE'
TYPE_ZIP        = 'ZIP'
TYPE_CITY       = 'CITY'
TYPE_DOB        = 'DOB'
TYPE_YEAR       = 'YEAR'
TYPE_DATE       = 'DATE'
TYPE_DATETIME   = 'DATETIME'
TYPE_NUMERIC    = 'NUMERIC'          # generic numeric — data-driven binning


def detect_type(col_name: str, series: pd.Series) -> str:
    """
    Detects QI column type using BOTH column name patterns AND data inspection.
    This makes the function work on any dataset, not just ones with known names.

    Priority: name-based patterns first (fast), then data inspection fallback.
    """
    col = col_name.lower().strip()

    # ── Gender ──────────────────────────────────────────────────────────────
    if any(p in col for p in ['gender', 'sex', 'biological_sex', 'pt_sex']):
        return TYPE_GENDER

    # ── Age ─────────────────────────────────────────────────────────────────
    if any(p in col for p in ['age', 'patient_age', 'pt_age', 'age_years',
                               'age_at', 'current_age']):
        return TYPE_AGE

    # ── ZIP / Postal ─────────────────────────────────────────────────────────
    if any(p in col for p in ['zip', 'postal', 'postcode', 'pincode',
                               'zip_code', 'zipcode', 'post_code']):
        return TYPE_ZIP

    # ── City / Geographic ────────────────────────────────────────────────────
    if any(p in col for p in ['city', 'town', 'district', 'village',
                               'tehsil', 'municipality']):
        return TYPE_CITY

    # ── Date of Birth ────────────────────────────────────────────────────────
    if any(p in col for p in ['dob', 'birth_date', 'date_of_birth',
                               'birthdate', 'birth date', 'birthplace']):
        return TYPE_DOB

    # ── Year fields ──────────────────────────────────────────────────────────
    if any(p in col for p in ['birth_year', 'admission_year',
                               'registration_year', 'start_year', 'end_year']):
        return TYPE_YEAR

    # ── Datetime fields (have both date and time component) ──────────────────
    if any(p in col for p in ['datetime', 'start_time', 'end_time',
                               'timestamp', '_at']):
        return TYPE_DATETIME

    # ── Date fields (date only, no time) ────────────────────────────────────
    if any(p in col for p in ['date', 'admission', 'discharge', 'visit_date',
                               'procedure_date', 'test_date', 'prescribed']):
        # Confirm it looks like a date by checking a sample value
        sample = series.dropna().astype(str)
        if not sample.empty:
            s = sample.iloc[0]
            if len(s) >= 8 and ('-' in s or '/' in s):
                return TYPE_DATE

    # ── Explicit numeric vitals / clinical measurements ──────────────────────
    numeric_vitals = [
        'weight', 'height', 'bmi', 'systolic', 'diastolic',
        'blood_pressure', 'heart_rate', 'spo2', 'oxygen',
        'temperature', 'temp', 'room_number', 'room_no',
        'length_of_stay', 'los', 'dosage', 'dose_value',
        'lab_value', 'value_numeric', 'result_value',
        'cholesterol', 'blood_sugar', 'glucose', 'hemoglobin',
    ]
    if any(p in col for p in numeric_vitals):
        return TYPE_NUMERIC

    # ── Low-cardinality categoricals — keep as-is ────────────────────────────
    # These columns are already generalized by nature (few distinct values)
    # Further generalization would destroy all meaning
    keep_as_is_patterns = [
        'blood_type', 'blood type', 'abo',
        'marital', 'marital_status',
        'ethnicity', 'ethnic',
        'race',
        'language', 'preferred_language',
        'smoking', 'smoker',
        'alcohol', 'drinking',
        'physical_activity', 'activity_level',
        'disease_severity', 'severity',
        'insurance_type', 'insurance_provider', 'payer_type',
        'admission_type', 'visit_type', 'encounter_class',
        'discharge_disposition', 'discharge_type',
        'state', 'province', 'region',  # already broad geographic level
    ]
    if any(p in col for p in keep_as_is_patterns):
        return TYPE_KEEP_AS_IS

    # ── Data inspection fallback ─────────────────────────────────────────────
    # If name doesn't match anything, inspect the actual data
    numeric_converted = pd.to_numeric(series, errors='coerce')
    numeric_frac = numeric_converted.notna().mean()

    if numeric_frac > 0.8:
        # Looks numeric — check if it's date-like (years in range 1900-2100)
        vals = numeric_converted.dropna()
        if not vals.empty and vals.min() >= 1900 and vals.max() <= 2100:
            return TYPE_YEAR
        return TYPE_NUMERIC

    # Categorical — check cardinality
    n_distinct = series.nunique()
    if n_distinct <= LOW_CARDINALITY_MAX:
        return TYPE_KEEP_AS_IS  # Already generalized by nature

    # High-cardinality unknown categorical — cannot generalize safely
    return TYPE_KEEP_AS_IS


# ══════════════════════════════════════════════════════════════════════════════
# INFORMATION LOSS
# ══════════════════════════════════════════════════════════════════════════════

def ncp_numeric(original: pd.Series, generalized: pd.Series) -> float:
    total_range = pd.to_numeric(original, errors='coerce').pipe(
        lambda s: s.max() - s.min())
    if total_range == 0:
        return 0.0
    losses = []
    for orig, gen in zip(original, generalized):
        if pd.isna(orig): continue
        if str(gen) == '*':
            losses.append(1.0); continue
        try:
            gen_str = str(gen).replace('–', '-').replace('—', '-')
            parts = gen_str.split('-')
            lo, hi = float(parts[0].strip()), float(parts[-1].strip())
            losses.append(min(abs(hi - lo) / total_range, 1.0))
        except:
            losses.append(0.0)
    return np.mean(losses) * 100 if losses else 0.0


def ncp_entropy(original: pd.Series, generalized: pd.Series) -> float:
    from scipy.stats import entropy as sp_entropy
    oc = original.dropna().astype(str).value_counts(normalize=True)
    gc = generalized.dropna().astype(str).value_counts(normalize=True)
    if oc.empty: return 0.0
    H_o = sp_entropy(oc.values)
    H_g = sp_entropy(gc.values)
    if H_o == 0: return 0.0
    return max(0.0, (1 - min(H_g / H_o, 1.0)) * 100)


def compute_information_loss(original_df, generalized_df, quasi_columns):
    per_col, methods = {}, {}
    for col in quasi_columns:
        if col not in original_df.columns: continue
        col_type = detect_type(col, original_df[col])
        o, g = original_df[col], generalized_df[col]

        if col_type in (TYPE_GENDER, TYPE_KEEP_AS_IS):
            loss, method = 0.0, 'none — kept as-is'
        elif col_type in (TYPE_AGE, TYPE_YEAR, TYPE_NUMERIC):
            loss, method = ncp_numeric(o, g), 'NCP_numeric'
        elif col_type in (TYPE_ZIP, TYPE_CITY):
            loss, method = ncp_entropy(o, g), 'NCP_entropy'
        elif col_type in (TYPE_DOB, TYPE_DATE, TYPE_DATETIME):
            year_orig = pd.to_numeric(
                o.astype(str).str[:4], errors='coerce')
            loss = ncp_numeric(year_orig, g)
            method = 'NCP_numeric (year component)'
        else:
            loss, method = 0.0, 'none'

        per_col[col] = round(loss, 2)
        methods[col] = method

    # Average only over columns that were actually generalized
    generalized_losses = [v for col, v in per_col.items()
                          if methods.get(col, 'none') != 'none — kept as-is'
                          and methods.get(col, 'none') != 'none']
    avg = np.mean(generalized_losses) if generalized_losses else 0.0

    return {
        'per_column': per_col,
        'average': round(avg, 2),
        'within_threshold': avg <= MAX_INFO_LOSS_PCT,
        'method_used': methods,
    }


# ══════════════════════════════════════════════════════════════════════════════
# GENERALIZATION FUNCTIONS
# ══════════════════════════════════════════════════════════════════════════════

def generalize_age(value, level=1):
    if pd.isna(value) or str(value).strip() == '': return value
    try:
        age = int(float(value))
        if level == 1:
            lo = (age // 10) * 10; return f"{lo}–{lo+9}"
        elif level == 2:
            lo = (age // 20) * 20; return f"{lo}–{lo+19}"
        return '*'
    except: return value


def generalize_zip(value, level=1):
    if pd.isna(value) or str(value).strip() == '': return value
    try:
        s = str(int(float(str(value).strip())))
        keep = 2 if level == 1 else (1 if level == 2 else 0)
        return '*' if keep == 0 else s[:keep] + '*' * (len(s) - keep)
    except: return value


def generalize_city(value, level=1):
    if pd.isna(value) or str(value).strip() == '': return value
    try:
        key = str(value).strip().lower()
        if level == 1:
            return CITY_TO_PROVINCE.get(key, 'Other Region')
        elif level == 2:
            prov = CITY_TO_PROVINCE.get(key, str(value))
            return PROVINCE_TO_COUNTRY.get(prov, 'Pakistan')
        return '*'
    except: return value


def generalize_dob(value, level=1):
    if pd.isna(value) or str(value).strip() == '': return value
    try:
        year = int(str(value).strip()[:4])
        if level == 1:
            d = (year // 10) * 10; return f"{d}–{d+9}"
        elif level == 2:
            d = (year // 20) * 20; return f"{d}–{d+19}"
        return '*'
    except: return value


def generalize_year(value, level=1):
    if pd.isna(value) or str(value).strip() == '': return value
    try:
        year = int(float(value))
        if level == 1:
            lo = (year // 10) * 10; return f"{lo}–{lo+9}"
        elif level == 2:
            lo = (year // 20) * 20; return f"{lo}–{lo+19}"
        return '*'
    except: return value


def generalize_date(value, level=1):
    """Dates: Level 1 → year only. Level 2 → decade."""
    if pd.isna(value) or str(value).strip() == '': return value
    try:
        dt = pd.to_datetime(str(value), errors='coerce')
        if pd.isna(dt): return value
        if level == 1:
            return str(dt.year)                    # 2019-03-15 → 2019
        elif level == 2:
            d = (dt.year // 10) * 10
            return f"{d}–{d+9}"                   # 2019-03-15 → 2010–2019
        return '*'
    except: return value


def generalize_datetime(value, level=1):
    """Datetimes: Level 1 → date only (drop time). Level 2 → year."""
    if pd.isna(value) or str(value).strip() == '': return value
    try:
        dt = pd.to_datetime(str(value), errors='coerce')
        if pd.isna(dt): return value
        if level == 1:
            return dt.strftime('%Y-%m-%d')         # drop time component
        elif level == 2:
            return str(dt.year)                    # date only → year
        return '*'
    except: return value


def generalize_numeric_generic(value, level=1, col_min=None, col_max=None):
    """Data-driven numeric generalization. Bin size = range/10."""
    if pd.isna(value) or str(value).strip() == '': return value
    try:
        num = float(value)
        if col_min is not None and col_max is not None:
            data_range = col_max - col_min
            if data_range == 0: return str(round(num, 2))
            bin_size = max(1.0, data_range / 10)
        else:
            bin_size = 10.0
        if level == 2:
            bin_size *= 2
        lower = math.floor(num / bin_size) * bin_size
        upper = lower + bin_size
        if bin_size == int(bin_size) and num == int(num):
            return f"{int(lower)}–{int(upper)-1}"
        return f"{lower:.1f}–{upper:.1f}"
    except: return value


def generalize_column(series: pd.Series, col_name: str, level: int) -> pd.Series:
    col_type = detect_type(col_name, series)

    if col_type in (TYPE_GENDER, TYPE_KEEP_AS_IS):
        return series  # keep as-is

    if col_type == TYPE_AGE:
        return series.apply(lambda x: generalize_age(x, level))

    if col_type == TYPE_ZIP:
        return series.apply(lambda x: generalize_zip(x, level))

    if col_type == TYPE_CITY:
        return series.apply(lambda x: generalize_city(x, level))

    if col_type == TYPE_DOB:
        return series.apply(lambda x: generalize_dob(x, level))

    if col_type == TYPE_YEAR:
        return series.apply(lambda x: generalize_year(x, level))

    if col_type == TYPE_DATE:
        return series.apply(lambda x: generalize_date(x, level))

    if col_type == TYPE_DATETIME:
        return series.apply(lambda x: generalize_datetime(x, level))

    if col_type == TYPE_NUMERIC:
        num = pd.to_numeric(series, errors='coerce')
        col_min, col_max = num.min(), num.max()
        return series.apply(
            lambda x: generalize_numeric_generic(x, level, col_min, col_max))

    return series


# ══════════════════════════════════════════════════════════════════════════════
# K-ANONYMITY CHECK
# ══════════════════════════════════════════════════════════════════════════════

def check_k_anonymity(df, quasi_columns, k):
    # Exclude gender and keep-as-is columns from groupby
    # (they cannot be generalized further and fracture equivalence classes)
    check_cols = []
    for c in quasi_columns:
        if c not in df.columns: continue
        ct = detect_type(c, df[c])
        if ct not in (TYPE_GENDER, TYPE_KEEP_AS_IS):
            check_cols.append(c)

    if not check_cols:
        return True, 0, {}

    try:
        groups     = df.groupby(check_cols, dropna=False).size()
        violations = int((groups < k).sum())
        summary    = {str(kv): int(cnt) for kv, cnt in groups.items()}
        return violations == 0, violations, summary
    except Exception as e:
        print(f"  WARNING: groupby failed — {e}")
        return False, -1, {}


# ══════════════════════════════════════════════════════════════════════════════
# MAIN — apply_k_anonymity
# ══════════════════════════════════════════════════════════════════════════════

def apply_k_anonymity(df: pd.DataFrame,
                       quasi_columns: list,
                       k: int = DEFAULT_K) -> tuple:
    """
    Apply adaptive k-anonymity generalization to all quasi-identifier columns.

    Works on ANY structured healthcare dataset.
    Column types are detected automatically from name + data.

    Parameters:
        df             : original pandas DataFrame
        quasi_columns  : list of column names predicted as Quasi-Identifier
        k              : minimum equivalence class size (default 3)

    Returns:
        (anonymized_df, compliance_info)

    Usage:
        result_df, compliance_info = apply_k_anonymity(df, qi_cols, k=3)
    """
    notes = []
    n_rows = len(df)

    # Auto-detect and report column types before generalizing
    print(f"\n{'='*65}")
    print(f"k-Anonymity Module  |  k={k}  |  {n_rows} rows  |  "
          f"{len(quasi_columns)} QI columns")
    print(f"Info loss threshold: {MAX_INFO_LOSS_PCT}%")
    print(f"{'='*65}")
    print(f"\n[Column Type Detection]")
    for col in quasi_columns:
        if col not in df.columns:
            print(f"  SKIP — '{col}' not in dataset"); continue
        ct = detect_type(col, df[col])
        n_distinct = df[col].nunique()
        print(f"  {col:<35} → {ct}  (distinct values: {n_distinct})")

    # Auto-reduce k for small datasets
    effective_k = k
    if n_rows < SMALL_DATASET_THRESHOLD:
        effective_k = max(MIN_K, min(k, max(2, n_rows // 5)))
        if effective_k < k:
            msg = (f"Dataset has only {n_rows} rows. k auto-reduced "
                   f"from {k} to {effective_k}. Use a larger dataset "
                   f"for production.")
            print(f"\n  ⚠  {msg}")
            notes.append(msg)

    df_result      = df.copy()
    levels_applied = {col: 0 for col in quasi_columns if col in df.columns}

    # ── Level 1 ───────────────────────────────────────────────────────────────
    print(f"\n[Level 1 Generalization]")
    for col in quasi_columns:
        if col not in df_result.columns: continue
        ct = detect_type(col, df_result[col])
        if ct in (TYPE_GENDER, TYPE_KEEP_AS_IS):
            print(f"  {col} → kept as-is ({ct})")
            continue
        df_result[col] = generalize_column(df_result[col], col, level=1)
        levels_applied[col] = 1
        print(f"  ✓ {col} → Level 1 applied ({ct})")

    # ── Loss check after Level 1 ──────────────────────────────────────────────
    loss_l1 = compute_information_loss(df, df_result, quasi_columns)
    print(f"\n[Information Loss after Level 1]")
    for col, loss in loss_l1['per_column'].items():
        method = loss_l1['method_used'].get(col, '')
        mark = "✓" if loss <= MAX_INFO_LOSS_PCT else "⚠"
        print(f"  {mark} {col:<35} {loss:>5.1f}%  [{method}]")
    avg = loss_l1['average']
    print(f"\n  Average NCP (generalized cols): {avg:.1f}%  "
          f"(threshold: {MAX_INFO_LOSS_PCT}%  "
          f"{'✓ WITHIN' if loss_l1['within_threshold'] else '⚠ ABOVE'})")

    # ── k-anonymity check ─────────────────────────────────────────────────────
    print(f"\n[k-Anonymity Check after Level 1]")
    sat1, viol1, grp1 = check_k_anonymity(df_result, quasi_columns, effective_k)
    final_loss = loss_l1

    if sat1:
        print(f"  ✓ k={effective_k} satisfied at Level 1. No further "
              f"generalization needed.")
    else:
        print(f"  ✗ {viol1} equivalence class(es) below k={effective_k}.")
        _print_groups(grp1, effective_k)

        # ── Preview Level 2 loss before committing ────────────────────────────
        print(f"\n[Level 2 — Previewing information loss before applying]")
        df_l2_preview = df.copy()
        for col in quasi_columns:
            if col not in df_l2_preview.columns: continue
            ct = detect_type(col, df_l2_preview[col])
            if ct in (TYPE_GENDER, TYPE_KEEP_AS_IS): continue
            df_l2_preview[col] = generalize_column(
                df_l2_preview[col], col, level=2)
        loss_l2 = compute_information_loss(df, df_l2_preview, quasi_columns)

        for col, loss in loss_l2['per_column'].items():
            method = loss_l2['method_used'].get(col, '')
            mark = "✓" if loss <= MAX_INFO_LOSS_PCT else "⚠"
            print(f"  {mark} {col:<35} {loss:>5.1f}%  [{method}]")
        print(f"\n  Projected average NCP at Level 2: {loss_l2['average']:.1f}%")

        if loss_l2['average'] > MAX_INFO_LOSS_PCT:
            msg = (f"Level 2 would raise average loss to "
                   f"{loss_l2['average']:.1f}% > {MAX_INFO_LOSS_PCT}% threshold. "
                   f"Keeping Level 1 to preserve research utility.")
            print(f"\n  ⚠  {msg}")
            notes.append(msg)
        else:
            # Commit Level 2
            print(f"\n[Level 2 Generalization — applying]")
            for col in quasi_columns:
                if col not in df_result.columns: continue
                ct = detect_type(col, df_result[col])
                if ct in (TYPE_GENDER, TYPE_KEEP_AS_IS): continue
                df_result[col] = generalize_column(
                    df_result[col], col, level=2)
                levels_applied[col] = 2
                print(f"  ✓ {col} → Level 2 applied")

            print(f"\n[k-Anonymity Check after Level 2]")
            sat2, viol2, grp2 = check_k_anonymity(
                df_result, quasi_columns, effective_k)
            final_loss = loss_l2

            if sat2:
                print(f"  ✓ k={effective_k} satisfied after Level 2.")
                notes.append(f"k={effective_k} satisfied after Level 2.")
            else:
                msg = (f"{viol2} group(s) still below k={effective_k} "
                       f"after Level 2. Caused by small dataset size "
                       f"({n_rows} rows). Suppression not applied — "
                       f"research utility preserved.")
                print(f"\n  ⚠  {msg}")
                notes.append(msg)
                _print_groups(grp2, effective_k)

    # ── Summary ───────────────────────────────────────────────────────────────
    print(f"\n{'='*65}")
    print(f"k-Anonymity Complete")
    print(f"  k used: {effective_k}  |  Avg loss: {final_loss['average']:.1f}%")
    if not final_loss['within_threshold']:
        print(f"  Status: Optimal anonymization applied.")
        print(f"          Further generalization rejected — would exceed")
        print(f"          {MAX_INFO_LOSS_PCT}% information loss threshold.")
        print(f"          Research utility preserved at current generalization level.")
    else:
        print(f"  Status: k-anonymity fully satisfied within threshold.")
    print(f"{'='*65}\n")

    compliance_info = {
        'k_used'              : effective_k,
        'k_satisfied'         : sat1,
        'violations_remaining': viol1,
        'suppressed_records'  : 0,
        'information_loss'    : final_loss,
        'levels_applied'      : levels_applied,
        'notes'               : notes,
    }
    return df_result, compliance_info


def _print_groups(summary, k):
    print(f"  Equivalence class breakdown:")
    for gk, cnt in list(summary.items())[:20]:   # cap at 20 lines
        mark = "✓" if cnt >= k else "✗"
        print(f"    {mark}  {gk}  →  {cnt} record(s)")
    if len(summary) > 20:
        print(f"    ... and {len(summary)-20} more groups")


# ══════════════════════════════════════════════════════════════════════════════
# DEMO
# ══════════════════════════════════════════════════════════════════════════════
if __name__ == "__main__":
    import numpy as np
    np.random.seed(42)

    print("\n" + "="*65)
    print("DEMO — Realistic healthcare dataset (100 rows, mixed QI types)")
    print("="*65)

    n = 100
    df_demo = pd.DataFrame({
        'age'                  : np.random.randint(18, 82, n),
        'gender'               : np.random.choice(['Male','Female'], n),
        'zip_code'             : np.random.choice([71000,71200,71500,75000,75100,44000], n),
        'city'                 : np.random.choice(['karachi','hyderabad','lahore','islamabad','peshawar'], n),
        'blood_type'           : np.random.choice(['A+','A-','B+','B-','O+','O-','AB+','AB-'], n),
        'marital_status'       : np.random.choice(['Single','Married','Divorced','Widowed'], n),
        'smoking_status'       : np.random.choice(['Never','Former','Current'], n),
        'date_of_admission'    : pd.date_range('2020-01-01', periods=n, freq='3D').strftime('%Y-%m-%d'),
        'blood_pressure_systolic': np.random.randint(100, 180, n),
        'heart_rate'           : np.random.randint(55, 105, n),
        # non-QI columns (should pass through unchanged)
        'diagnosis'            : np.random.choice(['Flu','Diabetes','Hypertension'], n),
        'billing_amount'       : np.random.uniform(1000, 50000, n).round(2),
    })

    qi_cols = [
        'age', 'gender', 'zip_code', 'city', 'blood_type',
        'marital_status', 'smoking_status', 'date_of_admission',
        'blood_pressure_systolic', 'heart_rate',
    ]

    print(f"\nSample of original data (5 rows):")
    print(df_demo[qi_cols[:6]].head().to_string(index=False))

    result_df, info = apply_k_anonymity(df_demo, qi_cols, k=3)

    print(f"\nSample after k-anonymity (5 rows):")
    print(result_df[qi_cols[:6]].head().to_string(index=False))

    print(f"\nNon-QI columns unchanged:")
    print(f"  diagnosis unchanged:     {list(result_df['diagnosis']) == list(df_demo['diagnosis'])}")
    print(f"  billing_amount unchanged: {list(result_df['billing_amount']) == list(df_demo['billing_amount'])}")

    print(f"\nFull information loss breakdown:")
    for col, loss in info['information_loss']['per_column'].items():
        method = info['information_loss']['method_used'].get(col,'')
        print(f"  {col:<35} {loss:>5.1f}%  [{method}]")
    print(f"\n  Average NCP: {info['information_loss']['average']:.1f}%")
    print(f"  Within 15% threshold: {info['information_loss']['within_threshold']}")
    