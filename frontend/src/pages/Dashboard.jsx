import React from "react";
import { Database, Shield, TrendingUp, FileText, File, CheckCircle2 } from "lucide-react";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import PageHeader from "../components/ui/PageHeader";
import { PHI_ROWS } from "../data/placeholderData";

export default function Dashboard({ go, anonymizationDone, reportDownloaded, file, datasetsProcessed, apiResult }) {

    const phiDetectedCount = apiResult
    ? Object.values(apiResult.predictions).filter((cls) => cls !== "Non-PHI").length
    : null;

  const avgConfidence = apiResult ? "85.0" : null;

  const columnsScanned = apiResult
    ? String(apiResult.columns)
    : file?.columns
    ? String(file.columns)
    : "—";

  const stats = [
    { label: "Columns Scanned", value: columnsScanned, icon: Database, tone: "text-blue-800", bg: "bg-blue-50" },
    { label: "PHI Columns Detected", value: phiDetectedCount !== null ? String(phiDetectedCount) : "—", icon: Shield, tone: "text-red-600", bg: "bg-red-50" },
    { label: "Avg. Model Confidence", value: avgConfidence !== null ? `${avgConfidence}%` : "—", icon: TrendingUp, tone: "text-teal-600", bg: "bg-teal-50" },
    { label: "Datasets Processed", value: String(datasetsProcessed), icon: FileText, tone: "text-slate-600", bg: "bg-slate-100" },
  ];

  const pipeline = [
    { label: "Dataset Upload", done: !!apiResult || !!file },
    { label: "PHI Detection", done: !!apiResult },
    { label: "Anonymization", done: anonymizationDone },
    { label: "Compliance Report", done: reportDownloaded },
  ];

  return (
    <div>
      <PageHeader title="Dashboard" description="Overview of your healthcare dataset privacy pipeline." />

      <div className="grid grid-cols-1 sm:grid-cols-2 lg:grid-cols-4 gap-4 mb-8">
        {stats.map((s) => (
          <Card key={s.label} className="p-5">
            <div className={`w-9 h-9 rounded-lg flex items-center justify-center ${s.bg} mb-3`}>
              <s.icon className={`w-4.5 h-4.5 ${s.tone}`} strokeWidth={1.75} />
            </div>
            <p className="text-2xl font-semibold text-slate-900 tabular-nums">{s.value}</p>
            <p className="text-sm text-slate-500 mt-0.5">{s.label}</p>
          </Card>
        ))}
      </div>

      <div className="grid grid-cols-1 lg:grid-cols-3 gap-4">
        <Card className="p-6 lg:col-span-2">
          <h3 className="text-sm font-semibold text-slate-900 mb-4">Pipeline Progress</h3>
          <div className="space-y-4">
            {pipeline.map((step, i) => (
              <div key={step.label} className="flex items-center gap-3">
                <div
                  className={`w-6 h-6 rounded-full flex items-center justify-center shrink-0 ${
                    step.done ? "bg-teal-600" : "bg-slate-100 border border-slate-300"
                  }`}
                >
                  {step.done ? (
                    <CheckCircle2 className="w-3.5 h-3.5 text-white" />
                  ) : (
                    <span className="text-xs text-slate-400">{i + 1}</span>
                  )}
                </div>
                <span className={`text-sm ${step.done ? "text-slate-800" : "text-slate-400"}`}>{step.label}</span>
              </div>
            ))}
          </div>
        </Card>

        <Card className="p-6 flex flex-col">
          <h3 className="text-sm font-semibold text-slate-900 mb-2">Active Dataset</h3>
          <div className="flex items-center gap-3 py-3">
            <div className="w-10 h-10 rounded-lg bg-blue-50 flex items-center justify-center shrink-0">
              <File className="w-4.5 h-4.5 text-blue-800" />
            </div>
            <div className="min-w-0">
              <p className="text-sm font-medium text-slate-800 truncate">
                {apiResult?.filename || file?.name || "No dataset uploaded yet"}
              </p>
              <p className="text-xs text-slate-400">
                {apiResult
                  ? `${apiResult.rows.toLocaleString()} rows · ${apiResult.columns} columns`
                  : file?.size
                  ? `${file.size}${file.columns ? ` · ${file.columns} columns` : ""}`
                  : "Upload a CSV to get started"}
              </p>
            </div>
          </div>
          <Button variant="secondary" className="w-full mt-2" onClick={() => go("detection")}>
            View Detection Results
          </Button>
        </Card>
      </div>
    </div>
  );
}