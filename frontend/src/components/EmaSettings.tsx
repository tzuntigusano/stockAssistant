// Panel desplegable de configuración de EMAs del LiveChart.
// Es "tonto": recibe las EMAs y los manejadores; toda la persistencia vive en
// LiveChart. Separarlo mantiene el componente principal centrado en el gráfico.
import { type Ema, RANK, TF_OPTS } from "./liveChartConfig";

type Labels = { emaTfTitle: string; removeEma: string; addEma: string; tfNote: string };

export default function EmaSettings({
  emas,
  interval,
  labels,
  editEma,
  addEma,
  removeEma,
}: {
  emas: Ema[];
  interval: string;
  labels: Labels;
  editEma: (id: number, patch: Partial<Ema>) => void;
  addEma: () => void;
  removeEma: (id: number) => void;
}) {
  return (
    <div className="absolute left-0 top-full z-20 mt-1 w-64 rounded-lg border border-[var(--color-line)] bg-[var(--color-panel)] p-2 shadow-xl">
      {emas.map((e) => {
        const tfOpts = TF_OPTS.filter((t) => t.rank > (RANK[interval] ?? 0));
        return (
          <div key={e.id} className="flex items-center gap-1.5 py-0.5 text-xs">
            <input type="checkbox" checked={e.on} onChange={() => editEma(e.id, { on: !e.on })} />
            <span
              className="inline-block h-2 w-2 shrink-0 rounded-full"
              style={{ background: e.color }}
            />
            <span className="text-[var(--color-muted)]">EMA</span>
            <input
              type="number"
              min={1}
              max={400}
              value={e.length}
              onChange={(ev) =>
                editEma(e.id, { length: Math.max(1, Math.min(400, +ev.target.value || 1)) })
              }
              className="w-14 rounded border border-[var(--color-line)] bg-[var(--color-panel-2)] px-1 py-0.5 text-[var(--color-ink)] outline-none"
            />
            <select
              value={e.tf}
              onChange={(ev) => editEma(e.id, { tf: ev.target.value })}
              className="ml-auto rounded border border-[var(--color-line)] bg-[var(--color-panel-2)] px-1 py-0.5 text-[var(--color-ink)] outline-none"
              title={labels.emaTfTitle}
            >
              <option value="">TF —</option>
              {tfOpts.map((t) => (
                <option key={t.key} value={t.key}>
                  {t.label}
                </option>
              ))}
            </select>
            <button
              onClick={() => removeEma(e.id)}
              title={labels.removeEma}
              className="shrink-0 px-1 text-[var(--color-muted)] hover:text-[var(--color-bear)]"
            >
              ×
            </button>
          </div>
        );
      })}
      <button
        onClick={addEma}
        className="mt-1 w-full rounded border border-dashed border-[var(--color-line)] py-1 text-xs text-[var(--color-muted)] hover:border-[var(--color-accent)] hover:text-white"
      >
        {labels.addEma}
      </button>
      <p className="mt-1 border-t border-[var(--color-line)] pt-1 text-[10px] text-[var(--color-muted)]">
        {labels.tfNote}
      </p>
    </div>
  );
}
