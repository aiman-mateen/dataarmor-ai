import React from "react";

export default function Button({ children, variant = "primary", className = "", ...props }) {
  const variants = {
    primary: "bg-blue-800 hover:bg-blue-900 text-white shadow-sm",
    secondary: "bg-white hover:bg-slate-50 text-slate-700 border border-slate-300",
    success: "bg-teal-600 hover:bg-teal-700 text-white shadow-sm",
    danger: "bg-red-600 hover:bg-red-700 text-white shadow-sm",
  };

  return (
    <button
      className={`inline-flex items-center justify-center gap-2 px-4 py-2.5 rounded-lg text-sm font-medium transition-colors disabled:opacity-50 disabled:cursor-not-allowed ${variants[variant]} ${className}`}
      {...props}
    >
      {children}
    </button>
  );
}
