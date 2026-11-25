"use client";

import { useEffect, useState } from "react";
import { AlertTriangle, BadgeCheck, Camera, Lightbulb } from "lucide-react";
import type { IdentifyResult, Match } from "@/lib/api";
import { ConfidenceBar } from "./ConfidenceBar";
import { ConfirmPanel } from "./ConfirmPanel";
import { Disclaimer } from "./Disclaimer";
import { DrugTabs } from "./DrugTabs";
import { HowAIDecided } from "./HowAIDecided";
import { useSettings } from "./Providers";

function MatchCard({ m, rank, selected, onSelect, threshold }: { m: Match; rank: number; selected: boolean; onSelect: () => void; threshold: number }) {
  const { t } = useSettings();
  return (
    <button onClick={onSelect} aria-pressed={selected} className={`card w-full p-4 text-left transition hover:border-brand-300 ${selected ? "border-brand-500 ring-2 ring-brand-200" : ""}`}>
      <div className="flex items-start justify-between gap-2">
        <div>
          <p className="text-xs font-semibold text-ink-500">#{rank}</p>
          <p className="font-semibold">{m.pill.brand}</p>
          <p className="text-sm text-ink-700">
            {m.pill.generic_name} · {m.pill.strength}
          </p>
          <p className="mt-1 text-xs text-ink-500">
            <span className="capitalize">{m.pill.colors.join("/")}</span> · <span className="capitalize">{m.pill.shape}</span> · <span className="font-mono">{m.pill.imprint}</span>
          </p>
        </div>
      </div>
      <div className="mt-3">
        <ConfidenceBar value={m.confidence} label={t.result.confidence} threshold={threshold} />
      </div>
    </button>
  );
}

export function ResultView({ initial, onReset, onUpdate }: { initial: IdentifyResult; onReset: () => void; onUpdate?: (r: IdentifyResult) => void }) {
  const { t } = useSettings();
  const [result, setResult] = useState(initial);
  const [selected, setSelected] = useState<string | null>(initial.status === "confident" ? initial.matches[0]?.pill.pill_id ?? null : null);
  useEffect(() => {
    setResult(initial);
    setSelected(initial.status === "confident" ? initial.matches[0]?.pill.pill_id ?? null : null);
  }, [initial]);

  const update = (r: IdentifyResult) => {
    // keep the photo analysis if the confirmation came from barcode / pack text
    const merged = { ...r, detected: r.detected ?? result.detected };
    setResult(merged);
    setSelected(r.status === "confident" ? r.matches[0]?.pill.pill_id ?? null : null);
    onUpdate?.(merged);
  };

  const confident = result.status === "confident";
  const top = result.matches[0];
  const threshold = result.threshold ?? 0.7;
  return (
    <div className="space-y-6 animate-fadeUp">
      <Disclaimer text={result.disclaimer} />

      {confident && top ? (
        <section className="card border-brand-200 p-5 sm:p-6" aria-live="polite">
          <p className="flex items-center gap-2 text-sm font-semibold text-brand-700">
            <BadgeCheck className="h-5 w-5" aria-hidden /> {t.result.confident}
            {result.confirmed_by && <span className="chip text-xs">✓ {result.confirmed_by}</span>}
          </p>
          <div className="mt-3 flex flex-wrap items-end justify-between gap-4">
            <div>
              <h2 className="text-3xl font-bold">{top.pill.brand}</h2>
              <p className="text-lg text-ink-700">
                {top.pill.generic_name} · {top.pill.strength} · {top.pill.manufacturer}
              </p>
            </div>
            <div className="w-full sm:w-56">
              <ConfidenceBar value={top.confidence} label={t.result.confidence} threshold={threshold} />
            </div>
          </div>
        </section>
      ) : (
        <section className="card border-amber-200 bg-amber-50/50 p-5 sm:p-6" aria-live="polite">
          <h2 className="flex items-center gap-2 text-xl font-bold text-amber-900">
            <AlertTriangle className="h-6 w-6" aria-hidden /> {t.result.unsure}
          </h2>
          <p className="mt-2 text-amber-900">{result.message || t.result.unsureHelp}</p>
        </section>
      )}

      {!!result.photo_tips?.length && !confident && (
        <ul className="space-y-2">
          {result.photo_tips.map((k) => (
            <li key={k} className="flex items-start gap-2 text-sm text-ink-700">
              <Lightbulb className="mt-0.5 h-4 w-4 shrink-0 text-amber-500" aria-hidden />
              {(t.photoTips as Record<string, string>)[k] ?? k}
            </li>
          ))}
        </ul>
      )}

      {!confident && result.matches.length > 0 && (
        <section aria-labelledby="possible">
          <h3 id="possible" className="mb-3 text-lg font-semibold">
            {t.result.possible}
          </h3>
          <div className="grid gap-3 md:grid-cols-3">
            {result.matches.map((m, i) => (
              <MatchCard key={m.pill.pill_id} m={m} rank={i + 1} threshold={threshold} selected={selected === m.pill.pill_id} onSelect={() => setSelected(m.pill.pill_id)} />
            ))}
          </div>
        </section>
      )}

      {!confident && <ConfirmPanel scanId={result.scan_id} onResult={update} />}

      {selected && <DrugTabs pillId={selected} unconfirmed={!confident} />}

      {confident && result.matches.length > 1 && (
        <section aria-labelledby="others">
          <h3 id="others" className="mb-3 text-sm font-semibold text-ink-500">
            {t.result.possible}
          </h3>
          <div className="grid gap-3 md:grid-cols-3">
            {result.matches.map((m, i) => (
              <MatchCard key={m.pill.pill_id} m={m} rank={i + 1} threshold={threshold} selected={selected === m.pill.pill_id} onSelect={() => setSelected(m.pill.pill_id)} />
            ))}
          </div>
        </section>
      )}

      <HowAIDecided result={result} />

      {confident && <ConfirmPanel scanId={result.scan_id} onResult={update} />}

      <div className="flex justify-center pt-2">
        <button onClick={onReset} className="btn-primary">
          <Camera className="h-5 w-5" aria-hidden /> {t.scan.again}
        </button>
      </div>
    </div>
  );
}
