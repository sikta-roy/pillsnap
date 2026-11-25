"use client";

import Link from "next/link";
import { useEffect, useState } from "react";
import { History, Trash2 } from "lucide-react";
import { clearHistory, loadHistory, type HistoryItem } from "@/lib/history";
import { useSettings } from "@/components/Providers";

export default function HistoryPage() {
  const { t, lang } = useSettings();
  const [items, setItems] = useState<HistoryItem[]>([]);
  useEffect(() => setItems(loadHistory()), []);
  return (
    <div className="container-page max-w-3xl py-10">
      <div className="flex flex-wrap items-center justify-between gap-3">
        <h1 className="flex items-center gap-2 text-3xl font-bold tracking-tight">
          <History className="h-7 w-7 text-brand-600" aria-hidden /> {t.history.title}
        </h1>
        {items.length > 0 && (
          <button
            className="btn-ghost text-sm"
            onClick={() => {
              clearHistory();
              setItems([]);
            }}
          >
            <Trash2 className="h-4 w-4" aria-hidden /> {t.history.clear}
          </button>
        )}
      </div>
      <p className="mt-2 text-sm text-ink-500">{t.history.note}</p>
      {items.length === 0 ? (
        <div className="card mt-8 p-10 text-center text-ink-700">
          <p>{t.history.empty}</p>
          <Link href="/scan" className="btn-primary mt-6">
            {t.nav.scan}
          </Link>
        </div>
      ) : (
        <ul className="mt-6 space-y-3">
          {items.map((i) => (
            <li key={i.id} className="card flex items-center gap-4 p-4">
              {i.thumb ? <img src={i.thumb} alt="" className="h-16 w-16 rounded-xl object-cover" /> : <div className="h-16 w-16 rounded-xl bg-slate-100" />}
              <div className="min-w-0 flex-1">
                <p className="truncate font-semibold">{i.brand ?? "–"}</p>
                <p className="truncate text-sm text-ink-700">
                  {i.generic} {i.strength && `· ${i.strength}`}
                </p>
                <p className="text-xs text-ink-500">{new Date(i.date).toLocaleString(lang === "hi" ? "hi-IN" : undefined)}</p>
              </div>
              <div className="text-right">
                <p className={`text-sm font-bold tabular-nums ${i.status === "confident" ? "text-brand-700" : "text-amber-700"}`}>{i.confidence !== undefined ? `${Math.round(i.confidence * 100)}%` : "–"}</p>
                <p className="text-xs text-ink-500">{i.status === "confident" ? t.result.confident : t.result.unsure}</p>
              </div>
            </li>
          ))}
        </ul>
      )}
    </div>
  );
}
