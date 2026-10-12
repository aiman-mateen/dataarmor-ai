import { Home, FolderOpen, Search, Lock, FileText } from "lucide-react";

export const CLASS_STYLES = {
  "Direct Identifier": { text: "text-red-700", bg: "bg-red-50", dot: "bg-red-600", border: "border-red-200" },
  "Quasi-Identifier": { text: "text-orange-700", bg: "bg-orange-50", dot: "bg-orange-500", border: "border-orange-200" },
  "Sensitive Attribute": { text: "text-yellow-700", bg: "bg-yellow-50", dot: "bg-yellow-500", border: "border-yellow-200" },
  "Non-PHI": { text: "text-slate-600", bg: "bg-slate-100", dot: "bg-slate-400", border: "border-slate-200" },
};

export const CLASS_OPTIONS = Object.keys(CLASS_STYLES);

export const PIE_COLORS = {
  "Direct Identifier": "#dc2626",
  "Quasi-Identifier": "#f97316",
  "Sensitive Attribute": "#eab308",
  "Non-PHI": "#94a3b8",
};

export const NAV_ITEMS = [
  { id: "dashboard", label: "Dashboard", icon: Home },
  { id: "upload", label: "Dataset Upload", icon: FolderOpen },
  { id: "detection", label: "PHI Detection", icon: Search },
  { id: "anonymization", label: "Anonymization", icon: Lock },
  { id: "report", label: "Compliance Report", icon: FileText },
];