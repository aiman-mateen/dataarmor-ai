const BASE_URL = (
  import.meta.env.VITE_API_URL || "http://127.0.0.1:8000"
).replace(/\/+$/, "");

export async function detectPHI(file) {
  const formData = new FormData();
  formData.append("file", file);

  const response = await fetch(`${BASE_URL}/detect`, {
    method: "POST",
    body: formData,
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Detection failed");
  }

  return response.json();
}

export async function applyAnonymization(sessionFile, epsilon, k, predictions) {
  const params = new URLSearchParams({
    session_file: sessionFile,
    epsilon: epsilon,
    k: k,
  });

  const response = await fetch(`${BASE_URL}/anonymize?${params}`, {
    method: "POST",
    headers: { "Content-Type": "application/json" },
    body: JSON.stringify({ predictions }),
  });

  if (!response.ok) {
    const error = await response.json();
    throw new Error(error.detail || "Anonymization failed");
  }

  return response.json();
}

export function getDownloadUrl(type) {
  const paths = {
    anonymized: `${BASE_URL}/download/anonymized`,
    compliance_csv: `${BASE_URL}/download/compliance_csv`,
    compliance_json: `${BASE_URL}/download/compliance_json`,
  };
  return paths[type];
}