"use client";

import { useId, useRef, useState } from "react";
import { Barcode, Loader2, Package, Search } from "lucide-react";
import { confirm, downscale, scanPack, type IdentifyResult } from "@/lib/api";
import { useSettings } from "./Providers";

type BarcodeDetectorLike = { detect: (src: ImageBitmapSource) => Promise<{ rawValue: string }[]> };

export function ConfirmPanel({ scanId, onResult }: { scanId?: string | null; onResult: (r: IdentifyResult) => void }) {
  const { t, lang } = useSettings();
  const [imprint, setImprint] = useState("");
  const [code, setCode] = useState("");
  const [busy, setBusy] = useState<string | null>(null);
  const [note, setNote] = useState<string | null>(null);
  const packRef = useRef<HTMLInputElement>(null);
  const barRef = useRef<HTMLInputElement>(null);
  const ids = { imprint: useId(), code: useId() };

  const run = async (kind: string, fn: () => Promise<IdentifyResult>) => {
    setBusy(kind);
    setNote(null);
    try {
      const r = await fn();
      if (r.status === "no_match" && r.message) setNote(r.message);
      else onResult(r);
    } catch {
      setNote(t.scan.error);
    } finally {
      setBusy(null);
    }
  };

  const onBarcodePhoto = async (f: File) => {
    const BD = (globalThis as unknown as { BarcodeDetector?: new () => BarcodeDetectorLike }).BarcodeDetector;
    if (!BD) {
      setNote(t.confirm.noBarcodeApi);
      return;
    }
    try {
      const codes = await new BD().detect(await createImageBitmap(f));
      if (codes[0]?.rawValue) {
        setCode(codes[0].rawValue);
        run("barcode", () => confirm({ scan_id: scanId, barcode: codes[0].rawValue, lang }));
      } else setNote(t.confirm.noBarcodeApi);
    } catch {
      setNote(t.confirm.noBarcodeApi);
    }
  };

  return (
    <section className="card p-5 sm:p-6" aria-labelledby="confirm-title">
      <h3 id="confirm-title" className="text-lg font-semibold">
        {t.confirm.title}
      </h3>
      <form
        className="mt-4"
        onSubmit={(e) => {
          e.preventDefault();
          if (imprint.trim()) run("imprint", () => confirm({ scan_id: scanId, imprint: imprint.trim(), lang }));
        }}
      >
        <label htmlFor={ids.imprint} className="text-sm font-medium text-ink-700">
          {t.confirm.imprintLabel}
        </label>
        <div className="mt-1 flex gap-2">
          <input id={ids.imprint} className="input font-mono uppercase" value={imprint} onChange={(e) => setImprint(e.target.value)} placeholder={t.confirm.imprintPlaceholder} maxLength={40} autoCapitalize="characters" autoComplete="off" />
          <button className="btn-primary shrink-0" disabled={!!busy || !imprint.trim()}>
            {busy === "imprint" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Search className="h-4 w-4" />}
            <span className="hidden sm:inline">{t.confirm.check}</span>
          </button>
        </div>
      </form>

      <div className="my-5 flex items-center gap-3 text-xs font-semibold uppercase text-ink-300">
        <span className="h-px flex-1 bg-slate-100" /> {t.confirm.or} <span className="h-px flex-1 bg-slate-100" />
      </div>

      <div className="grid gap-4 sm:grid-cols-2">
        <div>
          <button type="button" className="btn-ghost w-full" onClick={() => packRef.current?.click()} disabled={!!busy}>
            {busy === "pack" ? <Loader2 className="h-4 w-4 animate-spin" /> : <Package className="h-4 w-4" />} {t.confirm.pack}
          </button>
          <p className="mt-1 text-xs text-ink-500">{t.confirm.packHelp}</p>
          <input
            ref={packRef}
            type="file"
            accept="image/*"
            capture="environment"
            className="sr-only"
            aria-label={t.confirm.pack}
            onChange={async (e) => {
              const f = e.target.files?.[0];
              if (f) run("pack", async () => scanPack(await downscale(f, 1600), lang));
              e.target.value = "";
            }}
          />
        </div>
        <form
          onSubmit={(e) => {
            e.preventDefault();
            if (code.trim()) run("barcode", () => confirm({ scan_id: scanId, barcode: code.trim(), lang }));
          }}
        >
          <label htmlFor={ids.code} className="sr-only">
            {t.confirm.barcode}
          </label>
          <div className="flex gap-2">
            <input id={ids.code} className="input" inputMode="numeric" value={code} onChange={(e) => setCode(e.target.value)} placeholder={t.confirm.barcode} maxLength={40} />
            <button type="button" className="btn-ghost shrink-0 px-3" onClick={() => barRef.current?.click()} aria-label={t.confirm.scanBarcode} title={t.confirm.scanBarcode}>
              <Barcode className="h-4 w-4" />
            </button>
          </div>
          <p className="mt-1 text-xs text-ink-500">{t.confirm.barcodeHelp}</p>
          <input
            ref={barRef}
            type="file"
            accept="image/*"
            capture="environment"
            className="sr-only"
            aria-label={t.confirm.scanBarcode}
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) onBarcodePhoto(f);
              e.target.value = "";
            }}
          />
        </form>
      </div>
      {note && (
        <p className="mt-4 rounded-lg bg-amber-50 p-3 text-sm text-amber-900" role="alert">
          {note}
        </p>
      )}
    </section>
  );
}
