import React from "react";

export default function PageHeader({ title, description }) {
  return (
    <div className="mb-8">
      <h1 className="text-2xl font-semibold text-slate-900 tracking-tight">{title}</h1>
      <p className="text-slate-500 mt-1.5 text-[15px]">{description}</p>
    </div>
  );
}
