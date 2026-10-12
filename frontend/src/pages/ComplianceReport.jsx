import React from "react";
import { PieChart, Pie, Cell, ResponsiveContainer, Tooltip } from "recharts";
import { PieChart as PieChartIcon, CheckCircle2, Download } from "lucide-react";
import Card from "../components/ui/Card";
import Button from "../components/ui/Button";
import Badge from "../components/ui/Badge";
import PageHeader from "../components/ui/PageHeader";
import { PHI_ROWS, TECHNIQUES } from "../data/placeholderData";
import { CLASS_STYLES, PIE_COLORS, CLASS_OPTIONS } from "../constants/theme";
import { downloadTextFile } from "../utils/download";

// Generic placeholder examples per class — until the backend returns real
// original/protected values per column, these represent "the kind of
// transformation" rather than that exact column's actual data.
const SAMPLE_BY_CLASS = {
  "Direct Identifier": { original: "John Smith", protected: "██████████" },
  "Quasi-Identifier": { original: "34", protected: "30–40" },
  "Sensitive Attribute": { original: "Type 2 Diabetes", protected: "Type 2 Diabetes ± noise" },
  "Non-PHI": { original: "H-0021", protected: "H-0021 (unchanged)" },
};

// Checks which classes actually exist in this dataset's detection results,
// so a technique shows "Not Applicable" when there's nothing for it to do.
function buildTransformationStatus(rows) {
  return TECHNIQUES.map((t) => {
    const count = rows.filter((r) => r.cls === t.cls).length;
    return { cls: t.cls, technique: t.technique, applicable: count > 0, count };
  });
}

function buildSanitizedCsv() {
  const header = "patient_name,age,diagnosis,gender,admission_date,hospital_id";
  const rows = [
    "██████████,5*,C34.9,█,2026-0█-██,H-0021",
    "██████████,7*,I25.1,█,2026-0█-██,H-0043",
    "██████████,3*,E11.9,█,2026-0█-██,H-0007",
  ];
  return [header, ...rows].join("\n");
}

function buildComplianceReportCsv(transformationStatus, classSummary, totalColumns, file, columnDetail, epsilon, k) {
  const esc = (v) => `"${String(v).replace(/"/g, '""')}"`;
  const lines = [
    "Section,Field,Value",
    `Metadata,Dataset,${esc(file?.name || "unknown")}`,
    `Metadata,Epsilon,${epsilon}`,
    `Metadata,K,${k}`,
    `Metadata,Total Columns,${totalColumns}`,
    "",
    "Class,Count,Percentage",
    ...classSummary.map((c) => `${esc(c.cls)},${c.count},${c.pct}%`),
    "",
    "Technique,Class,Applicable,Column Count,Parameter",
    ...transformationStatus.map((t) => {
      const param =
        t.cls === "Quasi-Identifier" ? `k=${k}` : t.cls === "Sensitive Attribute" ? `epsilon=${epsilon}` : "";
      return `${esc(t.technique)},${esc(t.cls)},${t.applicable ? "Yes" : "No"},${t.count},${param}`;
    }),
    "",
    "Column Name,Predicted Label,Privacy Technique,Original Sample,Anonymized Sample",
    ...columnDetail.map(
      (row) => `${esc(row.col)},${esc(row.cls)},${esc(row.technique)},${esc(row.original)},${esc(row.anonymized)}`
    ),
  ];
  return lines.join("\n");
}

function buildComplianceReportJson(transformationStatus, classSummary, totalColumns, file, columnDetail, epsilon, k) {
  return JSON.stringify(
    {
      dataset: file?.name || "unknown",
      privacyParameters: { epsilon, k },
      columnClassificationSummary: classSummary,
      transformationsApplied: transformationStatus.map((t) => ({
        technique: t.technique,
        class: t.cls,
        applicable: t.applicable,
        columnCount: t.count,
        ...(t.cls === "Quasi-Identifier" ? { k } : {}),
        ...(t.cls === "Sensitive Attribute" ? { epsilon } : {}),
      })),
      columnDetail,
    },
    null,
    2
  );
}

export default function ComplianceReport({ onDownload, file, overrides, anonymizationDone, go, epsilon, k, apiResult }) {
  if (!anonymizationDone) {
    return (
      <div>
        <PageHeader
          title="Compliance Report"
          description="Run anonymization first to generate a compliance report."
        />
        <Card className="p-10 flex flex-col items-center text-center">
          <div className="w-12 h-12 rounded-full bg-slate-100 flex items-center justify-center mb-4">
            <Download className="w-5 h-5 text-slate-400" />
          </div>
          <p className="text-sm font-medium text-slate-700">No compliance report available yet</p>
          <p className="text-sm text-slate-500 mt-1 mb-5">
            Apply privacy protection on the Anonymization page to generate this report.
          </p>
          <Button variant="primary" onClick={() => go("anonymization")}>
            Go to Anonymization
          </Button>
        </Card>
      </div>
    );
  }

  const baseRows = apiResult
    ? Object.entries(apiResult.predictions).map(([col, cls]) => ({
        col,
        cls,
        conf: 85,
      }))
    : PHI_ROWS;

  const effectiveRows = baseRows.map((row) => ({ ...row, cls: overrides[row.col] || row.cls }));
  const totalColumns = effectiveRows.length;
  const classSummary = CLASS_OPTIONS.map((cls) => {
    const count = effectiveRows.filter((r) => r.cls === cls).length;
    const pct = totalColumns > 0 ? Math.round((count / totalColumns) * 100) : 0;
    return { cls, count, pct };
  });
  const pieData = classSummary.map((c) => ({ name: c.cls, value: c.pct }));
  const transformationStatus = buildTransformationStatus(effectiveRows);
  const columnDetail = effectiveRows.map((row) => {
    const technique = TECHNIQUES.find((t) => t.cls === row.cls)?.technique;
    const backendRow = apiResult?.compliance_report?.find((r) => r.column_name === row.col);
    const original = backendRow?.original_sample ?? SAMPLE_BY_CLASS[row.cls].original;
    const anonymized = backendRow?.transformed_sample ?? SAMPLE_BY_CLASS[row.cls].protected;
    return { col: row.col, cls: row.cls, technique, original, anonymized };
  });

    const handleDownloadCsv = () => {
      if (apiResult?.compliance_report) {
        window.open("http://127.0.0.1:8000/download/anonymized", "_blank");
      } else {
        downloadTextFile("sanitized_patient_records.csv", buildSanitizedCsv(), "text/csv");
      }
      onDownload?.();
    };

    const handleDownloadReportCsv = () => {
      if (apiResult?.compliance_report) {
        window.open("http://127.0.0.1:8000/download/compliance_csv", "_blank");
      } else {
        downloadTextFile(
          "compliance_report.csv",
          buildComplianceReportCsv(transformationStatus, classSummary, totalColumns, file, columnDetail, epsilon, k),
          "text/csv"
        );
      }
      onDownload?.();
    };

    const handleDownloadReportJson = () => {
      if (apiResult?.compliance_report) {
        window.open("http://127.0.0.1:8000/download/compliance_json", "_blank");
      } else {
        downloadTextFile(
          "compliance_report.json",
          buildComplianceReportJson(transformationStatus, classSummary, totalColumns, file, columnDetail, epsilon, k),
          "application/json"
        );
      }
      onDownload?.();
    };

  return (
    <div>
      <PageHeader
        title="Compliance Report"
        description={`Summary of the anonymization process applied to ${apiResult?.filename || file?.name || "your dataset"}.`}
      />
      <div className="grid grid-cols-2 lg:grid-cols-4 gap-4 mb-6">
        {classSummary.map((c) => {
          const s = CLASS_STYLES[c.cls];
          return (
            <Card key={c.cls} className="p-5">
              <span className={`w-2 h-2 rounded-full inline-block ${s.dot} mb-3`} />
              <p className="text-2xl font-semibold text-slate-900">{c.pct}%</p>
              <p className="text-xs text-slate-500 mt-0.5">{c.cls}</p>
            </Card>
          );
        })}
      </div>
      <div className="grid grid-cols-1 lg:grid-cols-5 gap-4 mb-6">
        <Card className="p-6 lg:col-span-2">
          <h3 className="text-sm font-semibold text-slate-900 mb-4 flex items-center gap-2">
            <PieChartIcon className="w-4 h-4 text-blue-800" /> Column Classification
          </h3>
          <div className="h-56">
            <ResponsiveContainer width="100%" height="100%">
              <PieChart>
                <Pie data={pieData} dataKey="value" nameKey="name" innerRadius={55} outerRadius={80} paddingAngle={2}>
                  {pieData.map((entry) => (
                    <Cell key={entry.name} fill={PIE_COLORS[entry.name]} stroke="none" />
                  ))}
                </Pie>
                <Tooltip
                  formatter={(v) => `${v}%`}
                  contentStyle={{ borderRadius: 8, border: "1px solid #e2e8f0", fontSize: 13 }}
                />
              </PieChart>
            </ResponsiveContainer>
          </div>
        </Card>
        <Card className="p-6 lg:col-span-3">
          <h3 className="text-sm font-semibold text-slate-900 mb-4">Transformation Summary</h3>
          <div className="space-y-3">
            {transformationStatus.map((t) => (
              <div key={t.cls} className="flex items-center gap-2.5 text-sm">
                {t.applicable ? (
                  <CheckCircle2 className="w-4 h-4 text-teal-600 shrink-0" />
                ) : (
                  <span className="w-4 h-4 rounded-full border border-slate-300 shrink-0" />
                )}
                <span className={t.applicable ? "text-slate-700" : "text-slate-400"}>
                  {t.applicable
                    ? t.cls === "Quasi-Identifier"
                      ? `${t.technique} (k = ${k}) applied to ${t.count} ${t.cls} column${t.count > 1 ? "s" : ""}`
                      : t.cls === "Sensitive Attribute"
                      ? `${t.technique} (ε = ${epsilon}) applied to ${t.count} ${t.cls} column${t.count > 1 ? "s" : ""}`
                      : `${t.technique} applied to ${t.count} ${t.cls} column${t.count > 1 ? "s" : ""}`
                    : `${t.technique} — Not Applicable (no ${t.cls} columns detected)`}
                </span>
              </div>
            ))}
          </div>
        </Card>
      </div>
      <Card className="overflow-hidden mb-6">
        <div className="p-6 pb-0">
          <h3 className="text-sm font-semibold text-slate-900">Column-Level Detail</h3>
          <p className="text-sm text-slate-500 mt-1 mb-2">Per-column classification and the transformation applied.</p>
        </div>
        <div className="overflow-x-auto">
          <table className="w-full text-sm">
            <thead className="bg-slate-50 border-b border-slate-200">
              <tr>
                {["Column Name", "Predicted Label", "Privacy Technique Applied", "Original Sample", "Anonymized Sample"].map(
                  (h) => (
                    <th key={h} className="text-left font-medium text-slate-500 px-6 py-3 text-xs uppercase tracking-wide">
                      {h}
                    </th>
                  )
                )}
              </tr>
            </thead>
            <tbody>
              {effectiveRows.map((row, i) => {
                const technique = TECHNIQUES.find((t) => t.cls === row.cls)?.technique;
                const sample = SAMPLE_BY_CLASS[row.cls];
                return (
                  <tr
                    key={row.col}
                    className={`${i % 2 === 0 ? "bg-white" : "bg-slate-50/60"} border-b border-slate-100 last:border-0`}
                  >
                    <td className="px-6 py-3 font-medium text-slate-700 font-mono text-[13px]">{row.col}</td>
                    <td className="px-6 py-3">
                      <Badge cls={row.cls} />
                    </td>
                    <td className="px-6 py-3 text-slate-600">{technique}</td>
                    <td className="px-6 py-3 text-slate-500 font-mono text-[13px]">{columnDetail[i]?.original}</td>
                    <td className="px-6 py-3 text-slate-500 font-mono text-[13px]">{columnDetail[i]?.anonymized}</td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      </Card>
      <Card className="p-6">
        <h3 className="text-sm font-semibold text-slate-900 mb-1">Downloads</h3>
        <p className="text-sm text-slate-500 mb-4">Export the sanitized dataset and a full compliance record.</p>
        <div className="flex flex-wrap gap-3">
          <Button variant="success" onClick={handleDownloadCsv}>
            <Download className="w-4 h-4" /> Download Anonymized Dataset (.csv)
          </Button>
          <Button variant="secondary" onClick={handleDownloadReportCsv}>
            <Download className="w-4 h-4" /> Download Compliance Report (.csv)
          </Button>
          <Button variant="secondary" onClick={handleDownloadReportJson}>
            <Download className="w-4 h-4" /> Download Compliance Report (.json)
          </Button>
        </div>
      </Card>
    </div>
  );
}