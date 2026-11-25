"use client";

import { createContext, useContext, useEffect, useState } from "react";
import { dictionaries, type Dict, type Lang } from "@/lib/i18n";

type Settings = { lang: Lang; setLang: (l: Lang) => void; large: boolean; setLarge: (v: boolean) => void; t: Dict };
const Ctx = createContext<Settings | null>(null);

export function Providers({ children }: { children: React.ReactNode }) {
  const [lang, setLangState] = useState<Lang>("en");
  const [large, setLargeState] = useState(false);

  useEffect(() => {
    try {
      const l = localStorage.getItem("pillsnap.lang") as Lang | null;
      if (l === "en" || l === "hi") setLangState(l);
      else if (navigator.language?.startsWith("hi")) setLangState("hi");
      setLargeState(localStorage.getItem("pillsnap.large") === "1");
    } catch {}
  }, []);

  useEffect(() => {
    document.documentElement.lang = lang;
    document.documentElement.classList.toggle("large-text", large);
  }, [lang, large]);

  const setLang = (l: Lang) => {
    setLangState(l);
    try {
      localStorage.setItem("pillsnap.lang", l);
    } catch {}
  };
  const setLarge = (v: boolean) => {
    setLargeState(v);
    try {
      localStorage.setItem("pillsnap.large", v ? "1" : "0");
    } catch {}
  };
  return <Ctx.Provider value={{ lang, setLang, large, setLarge, t: dictionaries[lang] }}>{children}</Ctx.Provider>;
}

export function useSettings() {
  const c = useContext(Ctx);
  if (!c) throw new Error("useSettings outside Providers");
  return c;
}
