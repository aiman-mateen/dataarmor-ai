import React from "react";
import { CLASS_STYLES } from "../../constants/theme";  
export default function Badge({ cls }) {
  const s = CLASS_STYLES[cls];
  return (
    <span className={`inline-flex items-center gap-1.5 px-2.5 py-1 rounded-full text-xs font-medium border ${s.bg} ${s.text} ${s.border}`}>
      <span className={`w-1.5 h-1.5 rounded-full ${s.dot}`} />
      {cls}
    </span>
  );
}
