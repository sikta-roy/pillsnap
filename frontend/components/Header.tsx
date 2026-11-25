"use client";

import Link from "next/link";
import { usePathname } from "next/navigation";
import { useState } from "react";
import { Menu, Pill, Type, X } from "lucide-react";
import { useSettings } from "./Providers";

export function Header() {
  const { t, lang, setLang, large, setLarge } = useSettings();
  const path = usePathname();
  const [open, setOpen] = useState(false);
  const links = [
    { href: "/scan", label: t.nav.scan },
    { href: "/history", label: t.nav.history },
    { href: "/disposal", label: t.nav.disposal },
  ];
  const Controls = (
    <div className="flex items-center gap-2">
      <div role="group" aria-label={t.a11y.language} className="flex rounded-full border border-slate-200 p-0.5 text-sm">
        {(["en", "hi"] as const).map((l) => (
          <button key={l} onClick={() => setLang(l)} aria-pressed={lang === l} className={`min-h-[36px] rounded-full px-3 font-semibold ${lang === l ? "bg-brand-600 text-white" : "text-ink-700 hover:bg-slate-50"}`}>
            {l === "en" ? "EN" : "हिं"}
          </button>
        ))}
      </div>
      <button onClick={() => setLarge(!large)} aria-pressed={large} title={t.a11y.largeText} aria-label={t.a11y.largeText} className={`flex min-h-[40px] items-center gap-1 rounded-full border px-3 text-sm font-semibold ${large ? "border-brand-600 bg-brand-50 text-brand-700" : "border-slate-200 text-ink-700 hover:bg-slate-50"}`}>
        <Type className="h-4 w-4" aria-hidden />
        <span>A+</span>
      </button>
    </div>
  );
  return (
    <header className="sticky top-0 z-30 border-b border-slate-100 bg-white/85 backdrop-blur">
      <a href="#main" className="sr-only focus:not-sr-only focus:absolute focus:left-4 focus:top-2 focus:z-50 focus:rounded focus:bg-white focus:px-3 focus:py-2">
        {t.a11y.skip}
      </a>
      <div className="container-page flex h-16 items-center justify-between gap-4">
        <Link href="/" className="flex items-center gap-2 text-lg font-bold text-ink-900" aria-label="PillSnap home">
          <span className="grid h-9 w-9 place-items-center rounded-xl bg-brand-600 text-white">
            <Pill className="h-5 w-5" aria-hidden />
          </span>
          PillSnap
        </Link>
        <nav aria-label="Main" className="hidden items-center gap-1 md:flex">
          {links.map((l) => (
            <Link key={l.href} href={l.href} aria-current={path === l.href ? "page" : undefined} className={`rounded-full px-4 py-2 text-sm font-medium ${path === l.href ? "bg-brand-50 text-brand-700" : "text-ink-700 hover:bg-slate-50"}`}>
              {l.label}
            </Link>
          ))}
        </nav>
        <div className="hidden md:block">{Controls}</div>
        <button className="grid h-11 w-11 place-items-center rounded-full border border-slate-200 md:hidden" onClick={() => setOpen(!open)} aria-expanded={open} aria-controls="mobile-menu" aria-label={t.a11y.menu}>
          {open ? <X className="h-5 w-5" /> : <Menu className="h-5 w-5" />}
        </button>
      </div>
      {open && (
        <div id="mobile-menu" className="border-t border-slate-100 bg-white md:hidden">
          <nav aria-label="Mobile" className="container-page flex flex-col gap-1 py-3">
            {links.map((l) => (
              <Link key={l.href} href={l.href} onClick={() => setOpen(false)} className="rounded-xl px-3 py-3 font-medium text-ink-900 hover:bg-slate-50">
                {l.label}
              </Link>
            ))}
            <div className="pt-2">{Controls}</div>
          </nav>
        </div>
      )}
    </header>
  );
}
