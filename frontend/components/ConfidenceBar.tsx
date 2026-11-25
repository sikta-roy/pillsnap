export function ConfidenceBar({ value, label, threshold = 0.7 }: { value: number; label?: string; threshold?: number }) {
  const pct = Math.round(value * 100);
  const color = value >= threshold ? "bg-brand-500" : value >= 0.4 ? "bg-amber-400" : "bg-slate-300";
  return (
    <div>
      {label && (
        <div className="mb-1 flex justify-between text-xs font-medium text-ink-500">
          <span>{label}</span>
          <span className="tabular-nums text-ink-900">{pct}%</span>
        </div>
      )}
      <div className="h-2 overflow-hidden rounded-full bg-slate-100" role="meter" aria-valuemin={0} aria-valuemax={100} aria-valuenow={pct} aria-label={label ? `${label} ${pct}%` : `${pct}%`}>
        <div className={`h-full rounded-full ${color} transition-[width] duration-700`} style={{ width: `${Math.max(2, pct)}%` }} />
      </div>
    </div>
  );
}
