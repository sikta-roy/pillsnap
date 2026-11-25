"use client";

import { ShieldAlert } from "lucide-react";
import { useSettings } from "./Providers";

export function Disclaimer({ text, compact = false }: { text?: string; compact?: boolean }) {
  const { t } = useSettings();
  return (
    <div role="note" aria-label="Disclaimer" className={`flex items-start gap-3 rounded-xl border border-amber-200 bg-amber-50 text-amber-900 ${compact ? "p-3 text-sm" : "p-4"}`}>
      <ShieldAlert className="mt-0.5 h-5 w-5 shrink-0" aria-hidden />
      <p className="font-medium">{text || t.disclaimer}</p>
    </div>
  );
}
