
export const PHI_ROWS = [

  { col: "patient_name", cls: "Direct Identifier", conf: 99 },
  { col: "national_id", cls: "Direct Identifier", conf: 98 },
  { col: "medical_record_no", cls: "Direct Identifier", conf: 96 },
  { col: "phone_number", cls: "Direct Identifier", conf: 97 },
  { col: "email_address", cls: "Direct Identifier", conf: 95 },
{ col: "age", cls: "Direct Identifier", conf: 95 },
  { col: "gender", cls: "Direct Identifier", conf: 91 },
 
  
  { col: "zip_code", cls: "Quasi-Identifier", conf: 89 },
  { col: "admission_date", cls: "Quasi-Identifier", conf: 88 },
  { col: "marital_status", cls: "Quasi-Identifier", conf: 87 },
  { col: "insurance_provider", cls: "Quasi-Identifier", conf: 90 },
  { col: "city", cls: "Quasi-Identifier", conf: 86 },
  { col: "state", cls: "Quasi-Identifier", conf: 85 },
  { col: "ethnicity", cls: "Quasi-Identifier", conf: 92 },
  { col: "employment_status", cls: "Quasi-Identifier", conf: 88 },


  { col: "diagnosis", cls: "Sensitive Attribute", conf: 97 },
  { col: "diagnosis_code", cls: "Sensitive Attribute", conf: 94 },
  { col: "treatment_type", cls: "Sensitive Attribute", conf: 90 },
  { col: "lab_result", cls: "Sensitive Attribute", conf: 93 },
  { col: "medication", cls: "Sensitive Attribute", conf: 91 },
  { col: "allergy_info", cls: "Sensitive Attribute", conf: 89 },
  { col: "mental_health_status", cls: "Sensitive Attribute", conf: 96 },
  { col: "substance_use_history", cls: "Sensitive Attribute", conf: 95 },


  { col: "hospital_id", cls: "Non-PHI", conf: 84 },
  { col: "bed_number", cls: "Non-PHI", conf: 81 },
  { col: "ward_number", cls: "Non-PHI", conf: 78 },
  { col: "equipment_id", cls: "Non-PHI", conf: 76 },
  { col: "shift_code", cls: "Non-PHI", conf: 75 },
  { col: "bed_type", cls: "Non-PHI", conf: 77 },
];

export const TECHNIQUES = [
  { cls: "Direct Identifier", technique: "Masking", desc: "Protects direct patient identity by irreversibly obscuring the value." },
  { cls: "Quasi-Identifier", technique: "k-Anonymity", desc: "Generalizes quasi-identifiers so each record is indistinguishable from at least k-1 others." },
  { cls: "Sensitive Attribute", technique: "Differential Privacy", desc: "Adds calibrated statistical noise to protect individual-level sensitive values." },
  { cls: "Non-PHI", technique: "No Transformation Required", desc: "Column does not require privacy protection and is left unchanged." },
];

export const COMPLIANCE_SUMMARY = [
  { cls: "Direct Identifier", pct: 18 },
  { cls: "Quasi-Identifier", pct: 34 },
  { cls: "Sensitive Attribute", pct: 27 },
  { cls: "Non-PHI", pct: 21 },
];