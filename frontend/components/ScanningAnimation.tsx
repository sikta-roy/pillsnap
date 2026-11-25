"use client";

import { useEffect, useState } from "react";
import { Check, Loader2 } from "lucide-react";
import { useSettings } from "./Providers";

export function ScanningAnimation({ preview }: { preview: string | null }) {
  const { t } = useSettings();
  const [step, setStep] = useState(0);
  useEffect(() => {
    const id = setInterval(() => setStep((s) => Math.min(s + 1, t.scan.scanSteps.length - 1)), 1100);
    return () => clearInterval(id);
  }, [t.scan.scanSteps.length]);
  return (
    <div className="card mx-auto max-w-md animate-fadeUp p-6" role="status" aria-live="polite">
      <div className="relative mx-auto aspect-square w-full max-w-xs overflow-hidden rounded-2xl bg-slate-100">
        {preview && <img src={preview} alt="" className="h-full w-full object-cover" />}
        <div className="absolute inset-0 bg-brand-900/10" />
        <div className="absolute inset-x-0 h-1 animate-scan bg-gradient-to-r from-transparent via-brand-400 to-transparent shadow-[0_0_18px_4px_rgba(36,163,154,.55)]" />
        <div className="absolute inset-4 rounded-xl border-2 border-dashed border-white/80" />
      </div>
      <h2 className="mt-6 text-center text-xl font-semibold">{t.scan.scanning}</h2>
      <ol className="mt-4 space-y-2">
        {t.scan.scanSteps.map((s, i) => (
          <li key={s} className={`flex items-center gap-3 text-sm ${i <= step ? "text-ink-900" : "text-ink-300"}`}>
            {i < step ? <Check className="h-4 w-4 text-brand-600" aria-hidden /> : i === step ? <Loader2 className="h-4 w-4 animate-spin text-brand-600" aria-hidden /> : <span className="h-4 w-4 rounded-full border border-slate-200" aria-hidden />}
            {s}
          </li>
        ))}
      </ol>
    </div>
  );
}
