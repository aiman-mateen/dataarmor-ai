from feature_extractor import extract_features_for_inference, preprocess_for_model

# Use any real healthcare CSV you already have
csv_path = r"D:\FYP\mimic_fhir_csvs\mimic_patient.csv"

print("Step 1: Extracting features...")
features_df, column_names = extract_features_for_inference(csv_path)

print(f"Columns processed: {len(column_names)}")
print(f"Column names: {column_names}")
print(f"\nRaw features shape: {features_df.shape}")
print(features_df.head())

print("\nStep 2: Preprocessing for model...")
X = preprocess_for_model(features_df)

print(f"Model input shape: {X.shape}")
print(f"Columns: {list(X.columns)}")
print(f"\nAny nulls: {X.isnull().sum().sum()}")
print("\nFirst row:")
print(X.iloc[0])