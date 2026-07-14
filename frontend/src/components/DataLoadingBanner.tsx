// Aviso de "cargando por primera vez". Se muestra solo si las peticiones a Yahoo
// llevan encoladas más de 600 ms (caché fría). Con la caché caliente la cola se
// vacía al instante y el aviso no llega a aparecer.
import { useEffect, useState } from "react";
import { onPendingData } from "../api";
import { useLang } from "../i18n";

const T = {
  es: {
    msg: "Cargando datos por primera vez… se hace poco a poco para no saturar Yahoo (la próxima vez irá al instante).",
  },
  en: {
    msg: "Loading data for the first time… it goes gradually to avoid Yahoo's rate limit (next time it'll be instant).",
  },
} as const;

const DELAY_MS = 600;

export default function DataLoadingBanner() {
  const t = T[useLang()];
  const [show, setShow] = useState(false);

  useEffect(() => {
    let timer: ReturnType<typeof setTimeout> | null = null;
    const unsub = onPendingData((n) => {
      if (n > 0) {
        // Empieza a contar; si sigue ocupado tras el retardo, muestra el aviso.
        if (timer === null) timer = setTimeout(() => setShow(true), DELAY_MS);
      } else {
        if (timer) {
          clearTimeout(timer);
          timer = null;
        }
        setShow(false);
      }
    });
    return () => {
      unsub();
      if (timer) clearTimeout(timer);
    };
  }, []);

  if (!show) return null;
  return (
    <div className="flex items-center gap-2 rounded-lg border border-[var(--color-line)] bg-[var(--color-panel-2)] px-3 py-2 text-sm text-[var(--color-muted)]">
      <span className="animate-pulse">⏳</span>
      <span>{t.msg}</span>
    </div>
  );
}
