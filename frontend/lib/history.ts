export type HistoryItem = {
  id: string;
  date: string;
  status: string;
  pill_id?: string;
  brand?: string;
  generic?: string;
  strength?: string;
  confidence?: number;
  thumb?: string | null;
};

const KEY = "pillsnap.history.v1";

export function loadHistory(): HistoryItem[] {
  try {
    return JSON.parse(localStorage.getItem(KEY) || "[]");
  } catch {
    return [];
  }
}

export function saveHistory(item: HistoryItem) {
  try {
    const items = [item, ...loadHistory().filter((i) => i.id !== item.id)].slice(0, 50);
    localStorage.setItem(KEY, JSON.stringify(items));
  } catch {
    /* storage full or blocked: history is optional */
  }
}

export function clearHistory() {
  try {
    localStorage.removeItem(KEY);
  } catch {}
}
