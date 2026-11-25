"use client";

import Link from "next/link";
import { Phone } from "lucide-react";
import { Disclaimer } from "./Disclaimer";
import { useSettings } from "./Providers";

export function Footer() {
  const { t } = useSettings();
  return (
    <footer className="mt-20 border-t border-slate-100 bg-sky-50">
      <div className="container-page space-y-6 py-10">
        <Disclaimer />
        <p className="flex items-start gap-2 text-sm text-ink-700">
          <Phone className="mt-0.5 h-4 w-4 shrink-0 text-red-600" aria-hidden />
          {t.footer.emergency}
        </p>
        <div className="flex flex-col justify-between gap-3 text-sm text-ink-500 sm:flex-row">
          <p>© {new Date().getFullYear()} PillSnap. {t.footer.made}</p>
          <nav aria-label="Footer" className="flex gap-4">
            <Link href="/scan" className="hover:text-brand-700">{t.nav.scan}</Link>
            <Link href="/disposal" className="hover:text-brand-700">{t.nav.disposal}</Link>
            <Link href="/history" className="hover:text-brand-700">{t.nav.history}</Link>
          </nav>
        </div>
      </div>
    </footer>
  );
}
