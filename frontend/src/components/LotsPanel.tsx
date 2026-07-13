import { useState } from "react";
import { api } from "../api";
import type { Position } from "../types";
import { fmtMoney, fmtNum, fmtPct, signColor } from "../helpers";
import { useLang } from "../i18n";

const T = {
  es: {
    title: "💼 Mis compras y ventas",
    invalid: "Introduce un precio y un número de acciones válidos.",
    shares: "Acciones",
    avgCost: "Coste medio",
    marketValue: "Valor actual",
    unrealized: "P&L no realizado",
    realized: "P&L realizado (ventas): ",
    thType: "Tipo",
    thDate: "Fecha",
    thPrice: "Precio",
    thShares: "Acciones",
    thPnl: "P&L",
    thNote: "Nota",
    buy: "Compra",
    sell: "Venta",
    delete: "Eliminar",
    empty:
      "Aún no has registrado operaciones de este valor. Se guardan de forma permanente: solo las introduces una vez.",
    date: "Fecha",
    buyPrice: "Precio de compra",
    sellPrice: "Precio de venta",
    nShares: "Nº acciones",
    noteOpt: "Nota (opcional)",
    notePh: "ej. tras resultados",
    saving: "Guardando…",
    addBuy: "Añadir compra",
    addSell: "Añadir venta",
  },
  en: {
    title: "💼 My buys & sells",
    invalid: "Enter a valid price and number of shares.",
    shares: "Shares",
    avgCost: "Avg. cost",
    marketValue: "Market value",
    unrealized: "Unrealized P&L",
    realized: "Realized P&L (sells): ",
    thType: "Type",
    thDate: "Date",
    thPrice: "Price",
    thShares: "Shares",
    thPnl: "P&L",
    thNote: "Note",
    buy: "Buy",
    sell: "Sell",
    delete: "Delete",
    empty:
      "You haven't recorded any transactions for this stock yet. They're saved permanently: enter them once.",
    date: "Date",
    buyPrice: "Buy price",
    sellPrice: "Sell price",
    nShares: "Shares",
    noteOpt: "Note (optional)",
    notePh: "e.g. after earnings",
    saving: "Saving…",
    addBuy: "Add buy",
    addSell: "Add sell",
  },
} as const;

export default function LotsPanel({
  ticker,
  position,
  currency,
  onChange,
}: {
  ticker: string;
  position: Position | null;
  currency: string;
  onChange: () => void;
}) {
  const t = T[useLang()];
  const [side, setSide] = useState<"buy" | "sell">("buy");
  const [date, setDate] = useState(new Date().toISOString().slice(0, 10));
  const [price, setPrice] = useState("");
  const [shares, setShares] = useState("");
  const [note, setNote] = useState("");
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);

  async function add() {
    setError(null);
    const p = parseFloat(price.replace(",", "."));
    const s = parseFloat(shares.replace(",", "."));
    if (!p || !s || p <= 0 || s <= 0) {
      setError(t.invalid);
      return;
    }
    setBusy(true);
    try {
      await api.addLot({ ticker, price: p, shares: s, side, date, note });
      setPrice("");
      setShares("");
      setNote("");
      onChange();
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function remove(id: number) {
    await api.deleteLot(id);
    onChange();
  }

  const pos = position;
  const hasTx = pos && pos.lots.length > 0;

  return (
    <div className="card">
      <div className="card-title">{t.title}</div>

      {/* Resumen de posición */}
      {pos?.has_position && (
        <div className="mb-4 grid grid-cols-2 gap-3 rounded-lg bg-[var(--color-panel-2)] p-4 sm:grid-cols-4">
          <div>
            <div className="stat-label">{t.shares}</div>
            <div className="stat-value">{fmtNum(pos.total_shares, 2)}</div>
          </div>
          <div>
            <div className="stat-label">{t.avgCost}</div>
            <div className="stat-value">{fmtMoney(pos.avg_price, currency)}</div>
          </div>
          <div>
            <div className="stat-label">{t.marketValue}</div>
            <div className="stat-value">{fmtMoney(pos.market_value, currency)}</div>
          </div>
          <div>
            <div className="stat-label">{t.unrealized}</div>
            <div className={`stat-value ${signColor(pos.unrealized_pnl)}`}>
              {fmtMoney(pos.unrealized_pnl, currency)} ({fmtPct(pos.unrealized_pnl_pct)})
            </div>
          </div>
        </div>
      )}

      {pos && pos.realized_pnl !== 0 && (
        <p className="mb-4 text-sm">
          <span className="text-[var(--color-muted)]">{t.realized}</span>
          <span className={`font-medium ${signColor(pos.realized_pnl)}`}>
            {fmtMoney(pos.realized_pnl, currency)}
          </span>
        </p>
      )}

      {/* Tabla de transacciones */}
      {hasTx ? (
        <div className="mb-4 overflow-x-auto">
          <table className="w-full text-sm">
            <thead>
              <tr className="text-left text-xs text-[var(--color-muted)]">
                <th className="pb-2 font-medium">{t.thType}</th>
                <th className="pb-2 font-medium">{t.thDate}</th>
                <th className="pb-2 font-medium">{t.thPrice}</th>
                <th className="pb-2 font-medium">{t.thShares}</th>
                <th className="pb-2 font-medium">{t.thPnl}</th>
                <th className="pb-2 font-medium">{t.thNote}</th>
                <th></th>
              </tr>
            </thead>
            <tbody>
              {pos!.lots.map((l) => {
                const isSell = l.side === "sell";
                const pnl = isSell ? l.realized : l.pnl;
                const pnlPct = isSell ? l.realized_pct : l.pnl_pct;
                return (
                  <tr key={l.id} className="border-t border-[var(--color-line)]">
                    <td className="py-2">
                      <span
                        className={`rounded px-1.5 py-0.5 text-xs font-medium ${
                          isSell
                            ? "bg-[var(--color-bear)]/15 text-[var(--color-bear)]"
                            : "bg-[var(--color-bull)]/15 text-[var(--color-bull)]"
                        }`}
                      >
                        {isSell ? t.sell : t.buy}
                      </span>
                    </td>
                    <td className="py-2">{l.date}</td>
                    <td className="py-2">{fmtMoney(l.price, currency)}</td>
                    <td className="py-2">{fmtNum(l.shares, 2)}</td>
                    <td className={`py-2 ${signColor(pnl)}`}>
                      {pnl !== undefined && pnl !== null
                        ? `${fmtMoney(pnl, currency)}${
                            pnlPct != null ? ` (${fmtPct(pnlPct)})` : ""
                          }`
                        : "—"}
                    </td>
                    <td className="py-2 text-[var(--color-muted)]">{l.note}</td>
                    <td className="py-2 text-right">
                      <button
                        onClick={() => remove(l.id)}
                        className="text-[var(--color-muted)] hover:text-[var(--color-bear)]"
                        title={t.delete}
                      >
                        ✕
                      </button>
                    </td>
                  </tr>
                );
              })}
            </tbody>
          </table>
        </div>
      ) : (
        <p className="mb-4 text-sm text-[var(--color-muted)]">{t.empty}</p>
      )}

      {/* Selector compra / venta */}
      <div className="mb-3 flex gap-1 rounded-lg bg-[var(--color-panel-2)] p-1">
        <button
          onClick={() => setSide("buy")}
          className={`flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition ${
            side === "buy" ? "bg-[var(--color-bull)] text-white" : "text-[var(--color-muted)]"
          }`}
        >
          {t.buy}
        </button>
        <button
          onClick={() => setSide("sell")}
          className={`flex-1 rounded-md px-3 py-1.5 text-sm font-medium transition ${
            side === "sell" ? "bg-[var(--color-bear)] text-white" : "text-[var(--color-muted)]"
          }`}
        >
          {t.sell}
        </button>
      </div>

      {/* Formulario */}
      <div className="grid grid-cols-2 gap-3 sm:grid-cols-4">
        <div>
          <label className="stat-label">{t.date}</label>
          <input
            type="date"
            className="input mt-1"
            value={date}
            onChange={(e) => setDate(e.target.value)}
          />
        </div>
        <div>
          <label className="stat-label">{side === "buy" ? t.buyPrice : t.sellPrice}</label>
          <input
            className="input mt-1"
            inputMode="decimal"
            placeholder="0,00"
            value={price}
            onChange={(e) => setPrice(e.target.value)}
          />
        </div>
        <div>
          <label className="stat-label">{t.nShares}</label>
          <input
            className="input mt-1"
            inputMode="decimal"
            placeholder="0"
            value={shares}
            onChange={(e) => setShares(e.target.value)}
          />
        </div>
        <div>
          <label className="stat-label">{t.noteOpt}</label>
          <input
            className="input mt-1"
            placeholder={t.notePh}
            value={note}
            onChange={(e) => setNote(e.target.value)}
          />
        </div>
      </div>
      {error && <p className="mt-2 text-sm text-[var(--color-bear)]">{error}</p>}
      <button className="btn mt-3" onClick={add} disabled={busy}>
        {busy ? t.saving : side === "buy" ? t.addBuy : t.addSell}
      </button>
    </div>
  );
}
