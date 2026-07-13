import { useEffect, useRef } from "react";
import { useLang } from "../i18n";

/**
 * Gráfico avanzado de TradingView (widget gratuito embebido).
 * Se recrea cada vez que cambia el símbolo o el idioma.
 */
export default function TradingViewChart({ symbol }: { symbol: string }) {
  const containerRef = useRef<HTMLDivElement>(null);
  const lang = useLang();

  useEffect(() => {
    const container = containerRef.current;
    if (!container) return;
    container.innerHTML = "";

    const script = document.createElement("script");
    script.src = "https://s3.tradingview.com/external-embedding/embed-widget-advanced-chart.js";
    script.async = true;
    script.innerHTML = JSON.stringify({
      symbol,
      interval: "D",
      timezone: "Europe/Madrid",
      theme: "dark",
      style: "1",
      locale: lang,
      hide_side_toolbar: false,
      allow_symbol_change: false,
      support_host: "https://www.tradingview.com",
      studies: ["STD;EMA", "STD;RSI"],
      autosize: true,
    });
    container.appendChild(script);
  }, [symbol, lang]);

  return (
    <div className="h-[520px] w-full overflow-hidden rounded-xl border border-[var(--color-line)]">
      <div ref={containerRef} className="h-full w-full" />
    </div>
  );
}
