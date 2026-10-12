import React from "react";
import { Shield } from "lucide-react";
import { NAV_ITEMS } from "../../constants/theme";
export default function Sidebar({ page, setPage }) {
  return (
    <aside className="w-60 shrink-0 min-h-screen bg-white border-r border-slate-200 flex flex-col">
      <div className="px-5 py-5 flex items-center gap-2.5 border-b border-slate-200">
        <div className="w-8 h-8 rounded-lg bg-blue-800 flex items-center justify-center shrink-0">
          <Shield className="w-4 h-4 text-white" strokeWidth={2} />
        </div>
        <div>
          <p className="text-sm font-semibold text-slate-900 leading-tight">DataArmor AI</p>
          <p className="text-[11px] text-slate-400 leading-tight">Healthcare Privacy</p>
        </div>
      </div>

      <nav className="flex-1 px-3 py-4 space-y-1">
        {NAV_ITEMS.map((item) => {
          const active = page === item.id;
          return (
            <button
              key={item.id}
              onClick={() => setPage(item.id)}
              className={`w-full flex items-center gap-3 px-3 py-2.5 rounded-lg text-sm font-medium transition-colors ${
                active
                  ? "bg-blue-800 text-white shadow-sm"
                  : "text-slate-600 hover:bg-teal-50 hover:text-teal-700"
              }`}
            >
              <item.icon className="w-4 h-4" strokeWidth={1.75} />
              {item.label}
            </button>
          );
        })}
      </nav>

      <div className="px-5 py-4 border-t border-slate-200 flex items-center gap-1.5">
        <span className="w-1.5 h-1.5 rounded-full bg-teal-500" />
        <p className="text-[11px] text-slate-400">Version 1.0</p>
      </div>
    </aside>
  );
}
