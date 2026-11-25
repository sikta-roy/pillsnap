"use client";

import Link from "next/link";
import { Baby, Camera, CheckCircle2, ChevronDown, FileSearch, Leaf, ScanLine, Shuffle } from "lucide-react";
import { useSettings } from "@/components/Providers";

function HeroVisual() {
  return (
    <div aria-hidden className="relative mx-auto aspect-square w-full max-w-sm">
      <div className="absolute inset-0 rounded-[2.5rem] bg-gradient-to-br from-brand-100 via-sky-50 to-white" />
      <div className="absolute inset-6 overflow-hidden rounded-[2rem] border border-white bg-white/80 shadow-card">
        <div className="absolute inset-x-6 top-6 flex items-center justify-between text-xs font-semibold text-ink-500">
          <span>PillSnap</span>
          <span className="rounded-full bg-brand-50 px-2 py-0.5 text-brand-700">AI</span>
        </div>
        {/* pill */}
        <div className="absolute left-1/2 top-[42%] h-20 w-40 -translate-x-1/2 -translate-y-1/2 -rotate-12 rounded-full bg-gradient-to-b from-white to-slate-200 shadow-[0_10px_25px_-10px_rgba(15,34,51,.45)] ring-1 ring-slate-200">
          <span className="absolute inset-0 grid place-items-center text-sm font-bold tracking-wider text-slate-400">DOLO 650</span>
        </div>
        <div className="absolute inset-x-8 h-0.5 animate-scan bg-gradient-to-r from-transparent via-brand-400 to-transparent shadow-[0_0_12px_2px_rgba(36,163,154,.5)]" />
        <div className="absolute inset-x-5 bottom-5 rounded-2xl border border-slate-100 bg-white p-4 shadow-card">
          <div className="flex items-center justify-between">
            <div>
              <p className="text-sm font-bold text-ink-900">Dolo 650</p>
              <p className="text-xs text-ink-500">Paracetamol · 650 mg</p>
            </div>
            <span className="rounded-full bg-brand-50 px-2.5 py-1 text-xs font-bold text-brand-700">92%</span>
          </div>
          <div className="mt-3 h-1.5 overflow-hidden rounded-full bg-slate-100">
            <div className="h-full w-[92%] rounded-full bg-brand-500" />
          </div>
        </div>
      </div>
    </div>
  );
}

export default function Home() {
  const { t } = useSettings();
  const stepIcons = [Camera, ScanLine, FileSearch];
  const whyIcons = [Shuffle, Baby, Leaf];
  return (
    <>
      <section className="relative overflow-hidden">
        <div className="pointer-events-none absolute -top-40 right-0 h-[480px] w-[480px] rounded-full bg-brand-50 blur-3xl" aria-hidden />
        <div className="container-page relative grid items-center gap-12 py-14 md:grid-cols-2 md:py-24">
          <div className="animate-fadeUp">
            <p className="chip mb-5 bg-brand-50 text-brand-700">{t.hero.eyebrow}</p>
            <h1 className="text-4xl font-bold leading-tight tracking-tight text-ink-900 sm:text-5xl">{t.hero.title}</h1>
            <p className="mt-5 max-w-xl text-lg text-ink-700">{t.hero.subtitle}</p>
            <div className="mt-8 flex flex-wrap gap-3">
              <Link href="/scan" className="btn-primary px-7 text-lg">
                <Camera className="h-5 w-5" aria-hidden />
                {t.hero.cta}
              </Link>
              <a href="#how" className="btn-ghost">
                {t.hero.secondary}
              </a>
            </div>
            <ul className="mt-8 flex flex-wrap gap-x-6 gap-y-2 text-sm text-ink-700">
              {t.hero.trust.map((x) => (
                <li key={x} className="flex items-center gap-1.5">
                  <CheckCircle2 className="h-4 w-4 text-brand-600" aria-hidden />
                  {x}
                </li>
              ))}
            </ul>
          </div>
          <HeroVisual />
        </div>
      </section>

      <section id="how" className="scroll-mt-20 bg-sky-50 py-16 md:py-20">
        <div className="container-page">
          <h2 className="text-center text-3xl font-bold tracking-tight">{t.how.title}</h2>
          <ol className="mt-10 grid gap-5 md:grid-cols-3">
            {t.how.steps.map((s, i) => {
              const Icon = stepIcons[i];
              return (
                <li key={s.t} className="card p-6">
                  <div className="flex items-center gap-3">
                    <span className="grid h-11 w-11 place-items-center rounded-2xl bg-brand-600 text-white">
                      <Icon className="h-5 w-5" aria-hidden />
                    </span>
                    <span className="text-sm font-bold text-brand-700">0{i + 1}</span>
                  </div>
                  <h3 className="mt-4 text-lg font-semibold">{s.t}</h3>
                  <p className="mt-2 text-ink-700">{s.d}</p>
                </li>
              );
            })}
          </ol>
        </div>
      </section>

      <section className="py-16 md:py-20">
        <div className="container-page">
          <h2 className="text-center text-3xl font-bold tracking-tight">{t.why.title}</h2>
          <div className="mt-10 grid gap-5 md:grid-cols-3">
            {t.why.items.map((s, i) => {
              const Icon = whyIcons[i];
              return (
                <div key={s.t} className="rounded-xl2 border border-slate-100 p-6">
                  <Icon className="h-7 w-7 text-brand-600" aria-hidden />
                  <h3 className="mt-4 text-lg font-semibold">{s.t}</h3>
                  <p className="mt-2 text-ink-700">{s.d}</p>
                </div>
              );
            })}
          </div>
        </div>
      </section>

      <section className="pb-6">
        <div className="container-page max-w-3xl">
          <h2 className="text-center text-3xl font-bold tracking-tight">{t.faq.title}</h2>
          <div className="mt-8 space-y-3">
            {t.faq.items.map((f) => (
              <details key={f.q} className="card group p-5 [&_summary::-webkit-details-marker]:hidden">
                <summary className="flex cursor-pointer list-none items-center justify-between gap-4 font-semibold">
                  {f.q}
                  <ChevronDown className="h-5 w-5 shrink-0 text-ink-500 transition-transform group-open:rotate-180" aria-hidden />
                </summary>
                <p className="mt-3 text-ink-700">{f.a}</p>
              </details>
            ))}
          </div>
          <div className="mt-10 text-center">
            <Link href="/scan" className="btn-primary px-7">
              <Camera className="h-5 w-5" aria-hidden />
              {t.hero.cta}
            </Link>
          </div>
        </div>
      </section>
    </>
  );
}
