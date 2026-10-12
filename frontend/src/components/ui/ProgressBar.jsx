import React from "react";

export default function ProgressBar({ value, variant = "success", showLabel = true, className = "" }) {
  const fill = { success: "bg-teal-600", primary: "bg-blue-800", neutral: "bg-slate-400" }[variant];

  return (
    <div className={`flex items-center gap-2.5 ${className}`}>
      <div className="flex-1 h-1.5 rounded-full bg-slate-100 overflow-hidden">
        <div className={`h-full rounded-full ${fill} transition-all`} style={{ width: `${value}%` }} />
      </div>
      {showLabel && <span className="text-xs font-medium text-slate-600 tabular-nums w-9">{value}%</span>}
    </div>
  );
}
