import { useEffect, useState } from "react";
import { api } from "../api";
import { useLang } from "../i18n";

export default function WatchButton({ ticker }: { ticker: string }) {
  const lang = useLang();
  const [inList, setInList] = useState(false);

  useEffect(() => {
    let cancelled = false;
    api
      .watchlistStatus(ticker)
      .then((r) => !cancelled && setInList(r.in_watchlist))
      .catch(() => {});
    return () => {
      cancelled = true;
    };
  }, [ticker]);

  async function toggle() {
    if (inList) {
      await api.watchlistRemove(ticker);
      setInList(false);
    } else {
      await api.watchlistAdd(ticker);
      setInList(true);
    }
  }

  return (
    <button className="btn-ghost" onClick={toggle}>
      {inList
        ? lang === "en"
          ? "★ Watching"
          : "★ En seguimiento"
        : lang === "en"
          ? "☆ Watch"
          : "☆ Seguir"}
    </button>
  );
}
