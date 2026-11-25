"use client";

import Link from "next/link";
import { useEffect, useId, useRef, useState } from "react";
import { AlertTriangle, BookOpen, Info, Loader2, MessageCircleQuestion, Send, Thermometer, Trash2, UserX } from "lucide-react";
import { ask, drugInfo, type AskResult, type DrugInfo, type Statement } from "@/lib/api";
import { useSettings } from "./Providers";

function List({ items, tone = "default" }: { items: Statement[]; tone?: "default" | "danger" }) {
  if (!items?.length) return <p className="text-ink-500">–</p>;
  return (
    <ul className="space-y-2">
      {items.map((s, i) => (
        <li key={i} className="flex gap-3">
          <span className={`mt-2 h-1.5 w-1.5 shrink-0 rounded-full ${tone === "danger" ? "bg-red-500" : "bg-brand-500"}`} aria-hidden />
          <span>{s.text}</span>
        </li>
      ))}
    </ul>
  );
}

function Block({ title, icon: Icon, children, tone }: { title: string; icon: React.ElementType; children: React.ReactNode; tone?: "danger" }) {
  return (
    <div className={`rounded-xl border p-4 sm:p-5 ${tone === "danger" ? "border-red-100 bg-red-50/60" : "border-slate-100 bg-white"}`}>
      <h4 className={`mb-3 flex items-center gap-2 font-semibold ${tone === "danger" ? "text-red-800" : ""}`}>
        <Icon className="h-5 w-5" aria-hidden /> {title}
      </h4>
      {children}
    </div>
  );
}

function AskBox({ pillId }: { pillId: string }) {
  const { t, lang } = useSettings();
  const [q, setQ] = useState("");
  const [busy, setBusy] = useState(false);
  const [res, setRes] = useState<AskResult | null>(null);
  const id = useId();
  return (
    <div className="rounded-xl border border-slate-100 bg-sky-50 p-4 sm:p-5">
      <label htmlFor={id} className="flex items-center gap-2 font-semibold">
        <MessageCircleQuestion className="h-5 w-5 text-brand-600" aria-hidden /> {t.ask.title}
      </label>
      <form
        className="mt-3 flex gap-2"
        onSubmit={async (e) => {
          e.preventDefault();
          if (!q.trim()) return;
          setBusy(true);
          try {
            setRes(await ask(pillId, q.trim(), lang));
          } catch {
            setRes({ answer: [{ text: t.scan.error, source_ids: [] }], answerable: false, disclaimer: "" });
          } finally {
            setBusy(false);
          }
        }}
      >
        <input id={id} className="input" value={q} onChange={(e) => setQ(e.target.value)} placeholder={t.ask.placeholder} maxLength={300} />
        <button className="btn-primary shrink-0" disabled={busy} aria-label={t.ask.send}>
          {busy ? <Loader2 className="h-4 w-4 animate-spin" /> : <Send className="h-4 w-4" />}
        </button>
      </form>
      <p className="mt-2 text-xs text-ink-500">{t.ask.note}</p>
      {res && (
        <div className="mt-3 rounded-lg bg-white p-3" aria-live="polite">
          {res.answer.map((a, i) => (
            <p key={i} className={res.refused ? "font-medium text-amber-800" : ""}>
              {a.text}
            </p>
          ))}
        </div>
      )}
    </div>
  );
}

export function DrugTabs({ pillId, unconfirmed }: { pillId: string; unconfirmed?: boolean }) {
  const { t, lang } = useSettings();
  const [info, setInfo] = useState<DrugInfo | null>(null);
  const [err, setErr] = useState(false);
  const [tab, setTab] = useState(0);
  const tabsRef = useRef<(HTMLButtonElement | null)[]>([]);
  useEffect(() => {
    let live = true;
    setInfo(null);
    setErr(false);
    drugInfo(pillId, lang)
      .then((d) => live && setInfo(d))
      .catch(() => live && setErr(true));
    return () => {
      live = false;
    };
  }, [pillId, lang]);

  const tabs = [t.result.tabs.overview, t.result.tabs.side, t.result.tabs.alt, t.result.tabs.safety];
  if (err) return <p className="card p-6 text-red-700">{t.scan.error}</p>;
  if (!info)
    return (
      <div className="card grid place-items-center p-10" role="status">
        <Loader2 className="h-6 w-6 animate-spin text-brand-600" aria-label="Loading" />
      </div>
    );

  const onKey = (e: React.KeyboardEvent, i: number) => {
    if (e.key !== "ArrowRight" && e.key !== "ArrowLeft") return;
    const n = (i + (e.key === "ArrowRight" ? 1 : tabs.length - 1)) % tabs.length;
    setTab(n);
    tabsRef.current[n]?.focus();
  };
  const p = info.pill;
  return (
    <section className="card overflow-hidden" aria-label={`${p.brand} details`}>
      <div className="border-b border-slate-100 p-5 sm:p-6">
        <div className="flex flex-wrap items-start justify-between gap-3">
          <div>
            <h3 className="text-2xl font-bold">{p.brand}</h3>
            <p className="text-ink-700">
              {p.generic_name} · {p.strength}
            </p>
          </div>
          {info.rx_status && <span className="chip">{info.rx_status}</span>}
        </div>
        <dl className="mt-4 grid grid-cols-2 gap-3 text-sm sm:grid-cols-4">
          <div>
            <dt className="text-ink-500">{t.result.strength}</dt>
            <dd className="font-semibold">{p.strength}</dd>
          </div>
          <div>
            <dt className="text-ink-500">{t.result.maker}</dt>
            <dd className="font-semibold">{p.manufacturer}</dd>
          </div>
          <div>
            <dt className="text-ink-500">Imprint</dt>
            <dd className="font-mono font-semibold">{p.imprint}</dd>
          </div>
          <div>
            <dt className="text-ink-500">Class</dt>
            <dd className="font-semibold">{info.drug_class}</dd>
          </div>
        </dl>
        {unconfirmed && (
          <p className="mt-4 flex items-start gap-2 rounded-lg bg-amber-50 p-3 text-sm text-amber-900">
            <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden /> {t.result.unsureHelp}
          </p>
        )}
        {p.appearance_source === "demo" && <p className="mt-3 text-xs text-ink-500">{t.result.demoData}</p>}
      </div>

      <div role="tablist" aria-label="Medicine information" className="flex overflow-x-auto border-b border-slate-100 px-2 sm:px-4">
        {tabs.map((name, i) => (
          <button
            key={name}
            ref={(el) => {
              tabsRef.current[i] = el;
            }}
            role="tab"
            id={`tab-${i}`}
            aria-selected={tab === i}
            aria-controls={`panel-${i}`}
            tabIndex={tab === i ? 0 : -1}
            onKeyDown={(e) => onKey(e, i)}
            onClick={() => setTab(i)}
            className={`relative min-h-[48px] shrink-0 px-4 font-semibold ${tab === i ? "text-brand-700" : "text-ink-500 hover:text-ink-900"}`}
          >
            {name}
            {tab === i && <span className="absolute inset-x-3 bottom-0 h-0.5 rounded-full bg-brand-600" />}
          </button>
        ))}
      </div>

      <div role="tabpanel" id={`panel-${tab}`} aria-labelledby={`tab-${tab}`} className="space-y-4 p-5 sm:p-6">
        {lang === "hi" && info.grounding.content_language === "en" && <p className="rounded-lg bg-sky-50 p-3 text-sm text-ink-700">{t.result.hindiFallback}</p>}
        {tab === 0 && (
          <>
            <Block title={t.result.uses} icon={Info}>
              <List items={info.overview.uses} />
            </Block>
            <Block title={t.result.howItWorks} icon={BookOpen}>
              <List items={info.overview.how_it_works} />
            </Block>
            <AskBox pillId={pillId} />
          </>
        )}
        {tab === 1 && (
          <>
            <Block title={t.result.common} icon={Info}>
              <List items={info.side_effects.common} />
            </Block>
            <Block title={t.result.serious} icon={AlertTriangle} tone="danger">
              <List items={info.side_effects.serious} tone="danger" />
            </Block>
          </>
        )}
        {tab === 2 && (
          <>
            <Block title={t.result.sameSalt} icon={Info}>
              <ul className="flex flex-wrap gap-2">
                {Object.entries(info.alternatives.same_salt_brands).flatMap(([region, names]) =>
                  names.map((n) => (
                    <li key={region + n} className="chip">
                      {n} <span className="text-xs text-ink-500">{region}</span>
                    </li>
                  )),
                )}
              </ul>
              <p className="mt-3 text-sm text-ink-700">{info.alternatives.generic_tip}</p>
            </Block>
            <Block title={t.result.similar} icon={BookOpen}>
              <ul className="space-y-2">
                {info.alternatives.similar_medicines.map((s) => (
                  <li key={s.name}>
                    <span className="font-semibold">{s.name}:</span> {s.note}
                  </li>
                ))}
              </ul>
            </Block>
            <p className="flex items-start gap-2 rounded-lg bg-amber-50 p-3 text-sm font-medium text-amber-900">
              <AlertTriangle className="mt-0.5 h-4 w-4 shrink-0" aria-hidden /> {info.alternatives.note}
            </p>
          </>
        )}
        {tab === 3 && (
          <>
            <Block title={t.result.whoNot} icon={UserX} tone="danger">
              <List items={info.safety.who_should_not_take} tone="danger" />
            </Block>
            <Block title={t.result.warnings} icon={AlertTriangle}>
              <List items={info.safety.warnings} />
            </Block>
            <Block title={t.result.expiry} icon={AlertTriangle}>
              <List items={info.safety.expiry.map((text) => ({ text, source_ids: [] }))} />
            </Block>
            <Block title={t.result.storage} icon={Thermometer}>
              <List items={info.safety.storage} />
            </Block>
            <Link href="/disposal" className="btn-ghost w-full sm:w-auto">
              <Trash2 className="h-4 w-4" aria-hidden /> {t.result.disposalLink}
            </Link>
          </>
        )}
        <div className="border-t border-slate-100 pt-4 text-xs text-ink-500">
          <p className="font-semibold text-ink-700">{info.grounding.generator === "llm" ? t.result.generatorLlm : t.result.generatorExtractive}</p>
          <p className="mt-1">
            {t.result.sources}: {info.grounding.sources.join(" · ")}
          </p>
        </div>
      </div>
    </section>
  );
}
