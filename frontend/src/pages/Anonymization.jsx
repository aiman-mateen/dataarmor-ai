import React, { useState } from "react";
import { Lock, CheckCircle } from "lucide-react";
import Card from "../components/ui/Card";
import Badge from "../components/ui/Badge";
import Button from "../components/ui/Button";
import PageHeader from "../components/ui/PageHeader";

export default function Anonymization({
  go,
  applied,
  onApply,
  epsilon,
  setEpsilon,
  k,
  setK,
  apiResult,
  setApiResult,
  overrides,
}) {
  const [isLoading, setIsLoading] = useState(false);
  const [error, setError] = useState(null);

  const handleApply = async () => {
    setIsLoading(true);
    setError(null);

    try{
      const finalPredictions = {};
      if (apiResult?.predictions) {
        Object.entries(apiResult.predictions).forEach(([col, cls]) => {
          finalPredictions[col] = overrides?.[col] || cls;
        });
      }

      if (Object.keys(finalPredictions).length === 0) {
        throw new Error("No predictions found. Please run PHI detection first.");
      }

      const sessionFile = apiResult?.session_file;
      if (!sessionFile) {
        throw new Error("No session found. Please upload a dataset first.");
      }

      const params = new URLSearchParams({
        session_file: sessionFile,
        epsilon: epsilon,
        k: k,
      });

      const response = await fetch(`http://127.0.0.1:8000/anonymize?${params}`, {
        method: "POST",
        headers: { "Content-Type": "application/json" },
        body: JSON.stringify({ predictions: finalPredictions }),
      });

      if (!response.ok) {
        const errData = await response.json();
        throw new Error(errData.detail || `Server error: ${response.status}`);
      }

      const result = await response.json();

      setApiResult((prev) => ({
        ...prev,
        ...result,
        finalPredictions: finalPredictions,
      }));

      onApply();
      go("report");

    } catch (err) {
      console.error("Anonymization failed:", err);
      setError(err.message);
    } finally {
      setIsLoading(false);
    }
  };

  const techniques = [
    {
      label: "Direct Identifier",
      technique: "Masking",
      description: "Protects direct patient identity by irreversibly obscuring the value.",
      color: "red",
      control: null,
    },
    {
      label: "Quasi-Identifier",
      technique: "k-Anonymity",
      description: "Generalizes quasi-identifiers so each record is indistinguishable from at least k-1 others.",
      color: "orange",
      control: (
        <div className="mt-3">
          <label className="text-xs text-slate-500 font-medium">Anonymity Level (k)</label>
          <p className="text-xs text-slate-400 mb-2">
            Each record will be indistinguishable from at least k−1 others. Larger k provides stronger anonymity.
          </p>
          <input
            type="number"
            min={2}
            max={10}
            step={1}
            value={k}
            onChange={(e) => {
              const val = parseInt(e.target.value, 10);
              if (!isNaN(val)) setK(Math.min(10, Math.max(2, val)));
            }}
            className="w-24 border border-slate-300 rounded-md px-2 py-1 text-sm"
          />
        </div>
      ),
    },
    {
      label: "Sensitive Attribute",
      technique: "Differential Privacy",
      description: "Adds calibrated statistical noise to protect individual-level sensitive values.",
      color: "yellow",
      control: (
        <div className="mt-3">
          <div className="flex items-center justify-between mb-1">
            <label className="text-xs text-slate-500 font-medium">Privacy Budget (ε)</label>
            <span className="text-sm font-semibold text-slate-700">{epsilon.toFixed(1)}</span>
          </div>
          <input
            type="range"
            min={0.1}
            max={5.0}
            step={0.1}
            value={epsilon}
            onChange={(e) => setEpsilon(Number(e.target.value))}
            className="w-full accent-yellow-500"
          />
          <div className="flex justify-between text-xs text-slate-400 mt-1">
            <span>Higher Privacy</span>
            <span>Higher Utility</span>
          </div>
        </div>
      ),
    },
    {
      label: "Non-PHI",
      technique: "No Transformation Required",
      description: "Column does not require privacy protection and is left unchanged.",
      color: "gray",
      control: null,
    },
  ];

  return (
    <div>
      <PageHeader
        title="Anonymization Controls"
        description="Review the privacy technique applied to each detected class before running anonymization."
      />

      <div className="grid grid-cols-1 md:grid-cols-2 gap-4 mb-6">
        {techniques.map((t) => (
          <Card key={t.label} className="p-5">
            <Badge cls={t.label} />
            <p className="text-xs text-slate-400 uppercase tracking-wide font-medium mt-3 mb-1">
              TECHNIQUE
            </p>
            <p
              className={`text-lg font-semibold mb-2 ${
                t.color === "red"
                  ? "text-red-500"
                  : t.color === "orange"
                  ? "text-orange-500"
                  : t.color === "yellow"
                  ? "text-yellow-600"
                  : "text-slate-700"
              }`}
            >
              {t.technique}
            </p>
            <p className="text-sm text-slate-500">{t.description}</p>
            {t.control}
          </Card>
        ))}
      </div>

      {error && (
        <div className="mb-4 p-4 bg-red-50 border border-red-200 rounded-lg">
          <p className="text-sm text-red-600 font-medium">Error: {error}</p>
          <p className="text-xs text-red-400 mt-1">
            Check that your backend is running at http://127.0.0.1:8000
          </p>
        </div>
      )}

      {applied && !isLoading && (
        <div className="mb-4 p-4 bg-teal-50 border border-teal-200 rounded-lg flex items-center gap-3">
          <CheckCircle className="w-5 h-5 text-teal-500" />
          <p className="text-sm text-teal-700 font-medium">
            Privacy protection applied successfully to all detected columns.
          </p>
        </div>
      )}

      <div className="flex items-center gap-3">
        <Button
          variant="primary"
          onClick={handleApply}
          disabled={isLoading || applied}
        >
          <Lock className="w-4 h-4" />
          {isLoading
            ? "Applying Privacy Protection..."
            : applied
            ? "Protection Applied"
            : "Apply Privacy Protection"}
        </Button>

        {applied && (
          <Button variant="secondary" onClick={() => go("report")}>
            View Compliance Report
          </Button>
        )}
      </div>
    </div>
  );
}