"use client";

import { Brain } from "lucide-react";
import type { IdentifyResult } from "@/lib/api";
import { ConfidenceBar } from "./ConfidenceBar";
import { useSettings } from "./Providers";

export function HowAIDecided({ result }: { result: IdentifyResult }) {
  const { t } = useSettings();
  const d = result.detected;
  if (!d) return null;
  const imprint = d.imprint.text;
  return (
    <section className="card p-5 sm:p-6" aria-labelledby="how-decided">
      <h3 id="how-decided" className="flex items-center gap-2 text-lg font-semibold">
        <Brain className="h-5 w-5 text-brand-600" aria-hidden /> {t.decided.title}
      </h3>
      <div className="mt-5 grid gap-6 sm:grid-cols-[140px_1fr]">
        {d.cleaned_image && (
          <figure>
            <img src={d.cleaned_image} alt={t.decided.cleaned} className="aspect-square w-full rounded-xl border border-slate-100 object-cover" />
            <figcaption className="mt-2 text-xs text-ink-500">{t.decided.cleaned}</figcaption>
          </figure>
        )}
        <dl className="grid gap-4 sm:grid-cols-3">
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-ink-500">{t.decided.shape}</dt>
            <dd className="mt-1 font-semibold capitalize">{d.shape[0]?.label}</dd>
            <dd className="mt-2">
              <ConfidenceBar value={d.shape[0]?.confidence ?? 0} />
            </dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-ink-500">{t.decided.color}</dt>
            <dd className="mt-1 font-semibold capitalize">{d.color.filter((c) => c.confidence > 0.25).map((c) => c.label).join(" / ") || d.color[0]?.label}</dd>
            <dd className="mt-2">
              <ConfidenceBar value={d.color[0]?.confidence ?? 0} />
            </dd>
          </div>
          <div>
            <dt className="text-xs font-semibold uppercase tracking-wide text-ink-500">{t.decided.imprint}</dt>
            <dd className="mt-1 font-mono font-semibold">{imprint ? `"${imprint}"` : <span className="font-sans text-ink-500">{t.decided.notRead}</span>}</dd>
            {imprint && (
              <dd className="mt-2">
                {d.imprint.source === "you typed it" ? <span className="chip text-xs">{t.decided.typed}</span> : <ConfidenceBar value={d.imprint.confidence} />}
              </dd>
            )}
          </div>
        </dl>
      </div>

      {result.matches.length > 0 && (
        <div className="mt-6">
          <h4 className="text-sm font-semibold text-ink-700">{t.decided.evidence}</h4>
          <div className="mt-3 overflow-x-auto">
            <table className="w-full min-w-[520px] text-sm">
              <thead>
                <tr className="text-left text-xs uppercase tracking-wide text-ink-500">
                  <th className="py-2 pr-3 font-semibold">#</th>
                  <th className="py-2 pr-3 font-semibold">{t.result.possible}</th>
                  <th className="py-2 pr-3 font-semibold">{t.decided.emb}</th>
                  <th className="py-2 pr-3 font-semibold">{t.decided.shapeMatch}</th>
                  <th className="py-2 pr-3 font-semibold">{t.decided.colorMatch}</th>
                  <th className="py-2 pr-3 font-semibold">{t.decided.imprintMatch}</th>
                  <th className="py-2 font-semibold">{t.result.confidence}</th>
                </tr>
              </thead>
              <tbody>
                {result.matches.map((m, i) => (
                  <tr key={m.pill.pill_id} className="border-t border-slate-100">
                    <td className="py-2 pr-3 text-ink-500">{i + 1}</td>
                    <td className="py-2 pr-3 font-medium">{m.pill.brand}</td>
                    {[m.evidence.embedding_similarity, m.evidence.shape_match, m.evidence.color_match, m.evidence.imprint_similarity].map((v, j) => (
                      <td key={j} className="py-2 pr-3 tabular-nums text-ink-700">
                        {v === null || v === undefined ? "–" : `${Math.round(Math.max(0, v) * 100)}%`}
                      </td>
                    ))}
                    <td className="py-2 font-semibold tabular-nums">{Math.round(m.confidence * 100)}%</td>
                  </tr>
                ))}
              </tbody>
            </table>
          </div>
        </div>
      )}
    </section>
  );
}
