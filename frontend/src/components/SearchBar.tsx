import { useEffect, useRef, useState } from "react";
import { api } from "../api";
import type { SearchResult } from "../types";
import { useStore } from "../store/useStore";
import { useLang } from "../i18n";

export default function SearchBar() {
  const setTicker = useStore((s) => s.setTicker);
  const lang = useLang();
  const placeholder =
    lang === "en"
      ? "Search a stock (e.g. AAPL, Nokia, Santander)…"
      : "Busca una acción (ej. AAPL, Nokia, Santander)…";
  const [query, setQuery] = useState("");
  const [results, setResults] = useState<SearchResult[]>([]);
  const [open, setOpen] = useState(false);
  const [active, setActive] = useState(0);
  const boxRef = useRef<HTMLDivElement>(null);

  // Búsqueda con debounce
  useEffect(() => {
    if (query.trim().length < 1) {
      setResults([]);
      return;
    }
    const t = setTimeout(async () => {
      try {
        const r = await api.search(query.trim());
        setResults(r);
        setOpen(true);
        setActive(0);
      } catch {
        setResults([]);
      }
    }, 250);
    return () => clearTimeout(t);
  }, [query]);

  // Cerrar al hacer clic fuera
  useEffect(() => {
    const onClick = (e: MouseEvent) => {
      if (boxRef.current && !boxRef.current.contains(e.target as Node)) {
        setOpen(false);
      }
    };
    document.addEventListener("mousedown", onClick);
    return () => document.removeEventListener("mousedown", onClick);
  }, []);

  function pick(sym: string) {
    setTicker(sym);
    setQuery("");
    setResults([]);
    setOpen(false);
  }

  function onKeyDown(e: React.KeyboardEvent) {
    if (!open || results.length === 0) {
      if (e.key === "Enter" && query.trim()) pick(query.trim());
      return;
    }
    if (e.key === "ArrowDown") {
      e.preventDefault();
      setActive((a) => Math.min(a + 1, results.length - 1));
    } else if (e.key === "ArrowUp") {
      e.preventDefault();
      setActive((a) => Math.max(a - 1, 0));
    } else if (e.key === "Enter") {
      e.preventDefault();
      pick(results[active].symbol);
    } else if (e.key === "Escape") {
      setOpen(false);
    }
  }

  return (
    <div ref={boxRef} className="relative w-full max-w-md">
      <input
        className="input"
        placeholder={placeholder}
        value={query}
        onChange={(e) => setQuery(e.target.value)}
        onKeyDown={onKeyDown}
        onFocus={() => results.length && setOpen(true)}
      />
      {open && results.length > 0 && (
        <div className="absolute z-30 mt-1 w-full overflow-hidden rounded-lg border border-[var(--color-line)] bg-[var(--color-panel-2)] shadow-xl">
          {results.map((r, i) => (
            <button
              key={`${r.symbol}-${i}`}
              onClick={() => pick(r.symbol)}
              onMouseEnter={() => setActive(i)}
              className={`flex w-full items-center justify-between gap-3 px-3 py-2 text-left text-sm ${
                i === active ? "bg-[var(--color-accent)]/15" : ""
              }`}
            >
              <span className="flex items-center gap-2">
                <span className="font-semibold">{r.symbol}</span>
                <span className="truncate text-[var(--color-muted)]">{r.name}</span>
              </span>
              <span className="shrink-0 text-xs text-[var(--color-muted)]">{r.exchange}</span>
            </button>
          ))}
        </div>
      )}
    </div>
  );
}
