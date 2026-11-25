"use client";

import { useCallback, useRef, useState } from "react";
import { Camera, CheckCircle2, ImageUp } from "lucide-react";
import { ApiError, downscale, identify, type IdentifyResult } from "@/lib/api";
import { saveHistory } from "@/lib/history";
import { Disclaimer } from "@/components/Disclaimer";
import { useSettings } from "@/components/Providers";
import { ResultView } from "@/components/ResultView";
import { ScanningAnimation } from "@/components/ScanningAnimation";

type Phase = { kind: "idle" } | { kind: "scanning"; preview: string } | { kind: "result"; result: IdentifyResult } | { kind: "error"; message: string };

function record(r: IdentifyResult) {
  const m = r.matches[0];
  saveHistory({
    id: r.scan_id || `${Date.now()}`,
    date: new Date().toISOString(),
    status: r.status,
    pill_id: m?.pill.pill_id,
    brand: m?.pill.brand,
    generic: m?.pill.generic_name,
    strength: m?.pill.strength,
    confidence: m?.confidence,
    thumb: r.detected?.cleaned_image ?? null,
  });
}

export default function ScanPage() {
  const { t, lang } = useSettings();
  const [phase, setPhase] = useState<Phase>({ kind: "idle" });
  const [drag, setDrag] = useState(false);
  const camRef = useRef<HTMLInputElement>(null);
  const fileRef = useRef<HTMLInputElement>(null);

  const handle = useCallback(
    async (file: File | undefined) => {
      if (!file || !file.type.startsWith("image/")) return;
      const preview = URL.createObjectURL(file);
      setPhase({ kind: "scanning", preview });
      const started = Date.now();
      try {
        const blob = await downscale(file);
        const r = await identify(blob, lang);
        // keep the animation on screen long enough to be readable
        await new Promise((res) => setTimeout(res, Math.max(0, 2200 - (Date.now() - started))));
        record(r);
        setPhase({ kind: "result", result: r });
      } catch (e) {
        setPhase({ kind: "error", message: e instanceof ApiError && e.message === "offline" ? t.scan.offline : e instanceof ApiError && e.status === 400 ? e.message : t.scan.error });
      } finally {
        URL.revokeObjectURL(preview);
      }
    },
    [lang, t],
  );

  return (
    <div className="container-page py-8 sm:py-12">
      {phase.kind === "idle" || phase.kind === "error" ? (
        <div className="mx-auto max-w-2xl animate-fadeUp">
          <h1 className="text-3xl font-bold tracking-tight sm:text-4xl">{t.scan.title}</h1>
          <section className="mt-6 rounded-xl2 bg-sky-50 p-5" aria-labelledby="tips">
            <h2 id="tips" className="font-semibold">
              {t.scan.tipsTitle}
            </h2>
            <ul className="mt-3 space-y-2">
              {t.scan.tips.map((tip) => (
                <li key={tip} className="flex items-start gap-2 text-ink-700">
                  <CheckCircle2 className="mt-0.5 h-5 w-5 shrink-0 text-brand-600" aria-hidden />
                  {tip}
                </li>
              ))}
            </ul>
          </section>

          <div
            onDragOver={(e) => {
              e.preventDefault();
              setDrag(true);
            }}
            onDragLeave={() => setDrag(false)}
            onDrop={(e) => {
              e.preventDefault();
              setDrag(false);
              handle(e.dataTransfer.files?.[0]);
            }}
            className={`mt-6 rounded-xl2 border-2 border-dashed p-6 text-center transition sm:p-10 ${drag ? "border-brand-500 bg-brand-50" : "border-slate-200"}`}
          >
            <div className="flex flex-col justify-center gap-3 sm:flex-row">
              <button className="btn-primary px-7 text-lg" onClick={() => camRef.current?.click()}>
                <Camera className="h-5 w-5" aria-hidden /> {t.scan.take}
              </button>
              <button className="btn-ghost px-7 text-lg" onClick={() => fileRef.current?.click()}>
                <ImageUp className="h-5 w-5" aria-hidden /> {t.scan.upload}
              </button>
            </div>
            <p className="mt-4 hidden text-sm text-ink-500 sm:block">{t.scan.drop}</p>
            <input ref={camRef} type="file" accept="image/*" capture="environment" className="sr-only" aria-label={t.scan.take} onChange={(e) => handle(e.target.files?.[0])} />
            <input ref={fileRef} type="file" accept="image/*" className="sr-only" aria-label={t.scan.upload} onChange={(e) => handle(e.target.files?.[0])} />
          </div>
          {phase.kind === "error" && (
            <p className="mt-4 rounded-xl bg-red-50 p-4 text-red-800" role="alert">
              {phase.message}
            </p>
          )}
          <div className="mt-6">
            <Disclaimer compact />
          </div>
        </div>
      ) : phase.kind === "scanning" ? (
        <ScanningAnimation preview={phase.preview} />
      ) : (
        <div className="mx-auto max-w-4xl">
          <ResultView initial={phase.result} onReset={() => setPhase({ kind: "idle" })} onUpdate={record} />
        </div>
      )}
    </div>
  );
}
