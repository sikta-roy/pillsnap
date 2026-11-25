"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, Ban, Loader2, Recycle } from "lucide-react";
import { disposal, type Disposal } from "@/lib/api";
import { fallbackDisposal } from "@/lib/disposal";
import { useSettings } from "@/components/Providers";

export default function DisposalPage() {
  const { lang } = useSettings();
  const [d, setD] = useState<Disposal | null>(null);
  useEffect(() => {
    setD(null);
    disposal(lang)
      .then(setD)
      .catch(() => setD(fallbackDisposal[lang]));
  }, [lang]);
  if (!d)
    return (
      <div className="grid place-items-center py-24" role="status">
        <Loader2 className="h-6 w-6 animate-spin text-brand-600" aria-label="Loading" />
      </div>
    );
  return (
    <div className="container-page max-w-3xl py-10">
      <h1 className="flex items-center gap-3 text-3xl font-bold tracking-tight">
        <Recycle className="h-8 w-8 text-brand-600" aria-hidden /> {d.title}
      </h1>
      <ol className="mt-8 space-y-4">
        {d.steps.map((s, i) => (
          <li key={s.title} className="card flex gap-4 p-5">
            <span className="grid h-9 w-9 shrink-0 place-items-center rounded-full bg-brand-600 font-bold text-white">{i + 1}</span>
            <div>
              <h2 className="font-semibold">{s.title}</h2>
              <p className="mt-1 text-ink-700">{s.text}</p>
            </div>
          </li>
        ))}
      </ol>
      <section className="mt-8 rounded-xl2 border border-red-100 bg-red-50/60 p-5">
        <ul className="space-y-2">
          {d.do_not.map((x) => (
            <li key={x} className="flex items-start gap-2 text-red-900">
              <Ban className="mt-0.5 h-5 w-5 shrink-0" aria-hidden /> {x}
            </li>
          ))}
        </ul>
      </section>
      <section className="mt-6 rounded-xl2 bg-sky-50 p-5">
        <ul className="space-y-2">
          {d.special.map((x) => (
            <li key={x} className="flex items-start gap-2 text-ink-700">
              <AlertTriangle className="mt-0.5 h-5 w-5 shrink-0 text-amber-500" aria-hidden /> {x}
            </li>
          ))}
        </ul>
      </section>
      <p className="mt-6 text-xs text-ink-500">{d.source}</p>
    </div>
  );
}
