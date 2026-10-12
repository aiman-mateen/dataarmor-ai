import React from "react";
import { Shield } from "lucide-react";

export default function Footer() {
  return (
    <footer className="border-t border-slate-200 mt-12 pt-6 pb-8 text-center">
      <p className="text-sm font-medium text-slate-700 flex items-center justify-center gap-1.5">
        <Shield className="w-3.5 h-3.5 text-blue-800" /> DataArmor AI
      </p>
      <p className="text-xs text-slate-400 mt-1">
        AI-Powered Healthcare Data Privacy Platform · Final Year Project
      </p>
      <p className="text-xs text-slate-400">
        Software Engineering Department · Mehran University of Engineering &amp; Technology
      </p>
      <p className="text-xs text-slate-300 mt-2">© 2026 Team DataArmor AI</p>
    </footer>
  );
}
