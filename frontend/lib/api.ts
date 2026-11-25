import type { Lang } from "./i18n";

export const API_URL = (process.env.NEXT_PUBLIC_API_URL || "http://localhost:8000").replace(/\/$/, "");

export type Statement = { text: string; source_ids: string[] };
export type PublicPill = {
  pill_id: string;
  brand: string;
  generic_name: string;
  strength: string;
  manufacturer: string;
  market: string;
  shape: string;
  colors: string[];
  imprint: string;
  dosage_form?: string;
  rx_status?: string;
  appearance_source?: string;
};
export type Match = {
  pill: PublicPill;
  confidence: number;
  evidence: {
    embedding_similarity?: number | null;
    shape_match?: number;
    color_match?: number;
    imprint_similarity?: number | null;
    barcode?: boolean;
    pack_text?: boolean;
  };
};
export type Ranked = { label: string; confidence: number };
export type IdentifyResult = {
  scan_id?: string | null;
  status: "confident" | "needs_confirmation" | "no_match";
  threshold?: number;
  message?: string | null;
  matches: Match[];
  detected?: {
    shape: Ranked[];
    color: Ranked[];
    imprint: { text: string; confidence: number; source: string };
    methods: { embedding_model: boolean; cnn_shape: Ranked[] | null; classical_shape: Ranked[] | null };
    cleaned_image?: string | null;
  };
  photo_tips?: string[];
  confirmed_by?: "imprint" | "barcode" | "pack_text";
  read_text?: string;
  timings?: Record<string, number>;
  disclaimer: string;
};
export type DrugInfo = {
  pill: PublicPill;
  drug_class?: string;
  rx_status?: string;
  overview: { uses: Statement[]; how_it_works: Statement[] };
  side_effects: { common: Statement[]; serious: Statement[] };
  alternatives: {
    same_salt_in_catalog: PublicPill[];
    same_salt_brands: Record<string, string[]>;
    similar_medicines: { name: string; note: string }[];
    generic_tip: string;
    note: string;
  };
  safety: { who_should_not_take: Statement[]; warnings: Statement[]; storage: Statement[]; expiry: string[] };
  grounding: { generator: "llm" | "extractive"; model?: string | null; statements_dropped: number; sources: string[]; content_language: Lang };
  disclaimer: string;
};
export type AskResult = { answer: Statement[]; answerable: boolean; refused?: string; generator?: string; disclaimer: string };
export type Disposal = { title: string; steps: { title: string; text: string }[]; do_not: string[]; special: string[]; source: string };

export class ApiError extends Error {
  constructor(message: string, public status?: number) {
    super(message);
  }
}

async function handle<T>(res: Response): Promise<T> {
  if (!res.ok) {
    let msg = res.statusText;
    try {
      const j = await res.json();
      msg = j.detail || msg;
    } catch {}
    throw new ApiError(String(msg), res.status);
  }
  return res.json() as Promise<T>;
}

async function call<T>(path: string, init?: RequestInit): Promise<T> {
  let res: Response;
  try {
    res = await fetch(`${API_URL}${path}`, init);
  } catch {
    throw new ApiError("offline");
  }
  return handle<T>(res);
}

export function identify(file: Blob, lang: Lang) {
  const fd = new FormData();
  fd.append("image", file, "pill.jpg");
  fd.append("lang", lang);
  return call<IdentifyResult>("/api/identify", { method: "POST", body: fd });
}

export function confirm(body: { scan_id?: string | null; imprint?: string; barcode?: string; lang: Lang }) {
  return call<IdentifyResult>("/api/confirm", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify(body) });
}

export function scanPack(file: Blob, lang: Lang) {
  const fd = new FormData();
  fd.append("image", file, "pack.jpg");
  fd.append("lang", lang);
  return call<IdentifyResult>("/api/scan-pack", { method: "POST", body: fd });
}

export function drugInfo(pillId: string, lang: Lang) {
  return call<DrugInfo>(`/api/drug/${encodeURIComponent(pillId)}?lang=${lang}`);
}

export function ask(pillId: string, question: string, lang: Lang) {
  return call<AskResult>("/api/ask", { method: "POST", headers: { "Content-Type": "application/json" }, body: JSON.stringify({ pill_id: pillId, question, lang }) });
}

export function disposal(lang: Lang) {
  return call<Disposal>(`/api/disposal?lang=${lang}`);
}

/** Downscale big phone photos before upload (faster on mobile data, same accuracy). */
export async function downscale(file: File, maxSide = 1280): Promise<Blob> {
  try {
    const bmp = await createImageBitmap(file);
    const s = Math.min(1, maxSide / Math.max(bmp.width, bmp.height));
    if (s >= 1) return file;
    const c = document.createElement("canvas");
    c.width = Math.round(bmp.width * s);
    c.height = Math.round(bmp.height * s);
    c.getContext("2d")!.drawImage(bmp, 0, 0, c.width, c.height);
    return await new Promise((r) => c.toBlob((b) => r(b || file), "image/jpeg", 0.9));
  } catch {
    return file;
  }
}
