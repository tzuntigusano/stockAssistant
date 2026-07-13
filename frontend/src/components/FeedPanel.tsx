import { useEffect, useRef, useState } from "react";
import ReactMarkdown from "react-markdown";
import { api } from "../api";
import type { FeedPost } from "../types";
import { useLang, currentLang, localeFor } from "../i18n";

const T = {
  es: {
    title: "📌 Muro",
    post1: "publicación",
    postN: "publicaciones",
    placeholder: "Pega un link de X, pega/arrastra una imagen o escribe una nota…",
    image: "📎 Imagen",
    hintX: "Link de X",
    hintImg: "Imagen",
    hintText: "Nota de texto",
    posting: "Publicando…",
    publish: "Publicar",
    removeImg: "Quitar imagen",
    empty: "Aún no hay publicaciones. Añade links de X, imágenes o notas.",
    edit: "Editar",
    del: "Eliminar",
    save: "Guardar",
    cancel: "Cancelar",
    confirmDel: "¿Eliminar esta publicación?",
    open: "Abrir ↗",
    loadingTweet: "Cargando tweet…",
    more: "Ver más publicaciones",
  },
  en: {
    title: "📌 Wall",
    post1: "post",
    postN: "posts",
    placeholder: "Paste an X link, paste/drop an image or write a note…",
    image: "📎 Image",
    hintX: "X link",
    hintImg: "Image",
    hintText: "Text note",
    posting: "Posting…",
    publish: "Post",
    removeImg: "Remove image",
    empty: "No posts yet. Add X links, images or notes.",
    edit: "Edit",
    del: "Delete",
    save: "Save",
    cancel: "Cancel",
    confirmDel: "Delete this post?",
    open: "Open ↗",
    loadingTweet: "Loading tweet…",
    more: "Show more posts",
  },
} as const;

const PAGE = 5;
const X_URL = /^https?:\/\/(www\.)?(x|twitter)\.com\/\S+$/i;

function isXUrl(s: string) {
  return X_URL.test(s.trim());
}

function xHandle(url: string): string {
  const m = url.match(/(?:x|twitter)\.com\/([^/?#]+)/i);
  const h = m?.[1];
  if (!h || ["i", "home", "search", "explore"].includes(h.toLowerCase())) return "X";
  return "@" + h;
}

function fmtDateTime(epoch: number): string {
  return new Date(epoch * 1000).toLocaleString(localeFor(currentLang()), {
    dateStyle: "short",
    timeStyle: "short",
  });
}

function fileToDataUrl(file: File): Promise<string> {
  return new Promise((res, rej) => {
    const r = new FileReader();
    r.onload = () => res(r.result as string);
    r.onerror = rej;
    r.readAsDataURL(file);
  });
}

function XIcon() {
  return (
    <svg viewBox="0 0 24 24" className="h-4 w-4 shrink-0 fill-current" aria-hidden>
      <path d="M18.244 2.25h3.308l-7.227 8.26 8.502 11.24H16.17l-5.214-6.817L4.99 21.75H1.68l7.73-8.835L1.254 2.25H8.08l4.713 6.231zm-1.161 17.52h1.833L7.084 4.126H5.117z" />
    </svg>
  );
}

// Carga el script de X (widgets.js) una sola vez.
let twttrPromise: Promise<any> | null = null;
function loadTwitter(): Promise<any> {
  const w = window as any;
  if (w.twttr?.widgets) return Promise.resolve(w.twttr);
  if (twttrPromise) return twttrPromise;
  twttrPromise = new Promise((resolve, reject) => {
    const s = document.createElement("script");
    s.src = "https://platform.twitter.com/widgets.js";
    s.async = true;
    s.onload = () => {
      const t = (window as any).twttr;
      if (t?.ready) t.ready(() => resolve(t));
      else resolve(t);
    };
    s.onerror = reject;
    document.head.appendChild(s);
  });
  return twttrPromise;
}

// Tarjeta de respaldo (si el tweet no carga: sin conexión, borrado, etc.).
function XCard({ url }: { url: string }) {
  const t = T[useLang()];
  return (
    <button
      onClick={() => window.open(url, "_blank", "noopener")}
      className="flex w-full items-center gap-2 rounded-lg border border-[var(--color-line)] bg-[var(--color-panel)] p-2.5 text-left transition hover:border-[var(--color-accent)]"
    >
      <XIcon />
      <div className="min-w-0">
        <div className="text-sm font-medium text-[var(--color-ink)]">{xHandle(url)}</div>
        <div className="truncate text-xs text-[var(--color-muted)]">{url}</div>
      </div>
      <span className="ml-auto text-xs text-[var(--color-muted)]">{t.open}</span>
    </button>
  );
}

// Tweet incrustado real vía widgets.js; cae a la tarjeta si falla.
function Tweet({ url }: { url: string }) {
  const t = T[useLang()];
  const ref = useRef<HTMLDivElement>(null);
  const [status, setStatus] = useState<"loading" | "ok" | "fail">("loading");
  const id = url.match(/status\/(\d+)/)?.[1];

  useEffect(() => {
    if (!id || !ref.current) {
      setStatus("fail");
      return;
    }
    let cancelled = false;
    setStatus("loading");
    ref.current.innerHTML = "";
    loadTwitter()
      .then((twttr) => {
        if (cancelled || !ref.current) return undefined;
        return twttr.widgets.createTweet(id, ref.current, {
          theme: "dark",
          dnt: true,
          align: "center",
        });
      })
      .then((el) => {
        if (!cancelled) setStatus(el ? "ok" : "fail");
      })
      .catch(() => {
        if (!cancelled) setStatus("fail");
      });
    return () => {
      cancelled = true;
    };
  }, [id]);

  if (status === "fail") return <XCard url={url} />;
  return (
    <div className="overflow-hidden">
      <div ref={ref} />
      {status === "loading" && (
        <div className="rounded-lg border border-[var(--color-line)] bg-[var(--color-panel)] p-2.5 text-xs text-[var(--color-muted)]">
          {t.loadingTweet}
        </div>
      )}
    </div>
  );
}

export default function FeedPanel({ ticker }: { ticker: string }) {
  const t = T[useLang()];
  const [posts, setPosts] = useState<FeedPost[]>([]);
  const [total, setTotal] = useState(0);
  const [text, setText] = useState("");
  const [imageData, setImageData] = useState<string | null>(null);
  const [busy, setBusy] = useState(false);
  const [error, setError] = useState<string | null>(null);
  const [editingId, setEditingId] = useState<number | null>(null);
  const [editText, setEditText] = useState("");
  const fileRef = useRef<HTMLInputElement>(null);

  // Al entrar en la acción: reinicia la paginación y carga los primeros.
  useEffect(() => {
    setPosts([]);
    setTotal(0);
    setEditingId(null);
    api
      .feed(ticker, 0, PAGE)
      .then((r) => {
        setPosts(r.posts);
        setTotal(r.total);
      })
      .catch(() => {});
  }, [ticker]);

  async function loadMore() {
    try {
      const r = await api.feed(ticker, posts.length, PAGE);
      setPosts((p) => [...p, ...r.posts]);
      setTotal(r.total);
    } catch {
      /* ignora */
    }
  }

  const kind: FeedPost["kind"] = imageData ? "image" : isXUrl(text) ? "x" : "text";
  const canPost = !!imageData || !!text.trim();

  async function submit() {
    if (!canPost || busy) return;
    setBusy(true);
    setError(null);
    try {
      const body =
        kind === "image"
          ? { kind, image: imageData!, text: text.trim() || undefined }
          : kind === "x"
            ? { kind, url: text.trim() }
            : { kind, text: text.trim() };
      const post = await api.addFeedPost(ticker, body);
      setPosts((p) => [post, ...p]); // más nuevas arriba
      setTotal((t) => t + 1);
      setText("");
      setImageData(null);
    } catch (e) {
      setError((e as Error).message);
    } finally {
      setBusy(false);
    }
  }

  async function del(id: number) {
    if (!confirm(t.confirmDel)) return;
    try {
      await api.deleteFeedPost(id);
      setPosts((p) => p.filter((x) => x.id !== id));
      setTotal((t) => Math.max(0, t - 1));
    } catch {
      /* ignora */
    }
  }

  function startEdit(p: FeedPost) {
    setEditingId(p.id);
    setEditText(p.kind === "x" ? (p.url ?? "") : (p.text ?? ""));
  }

  async function saveEdit(p: FeedPost) {
    try {
      const body = p.kind === "x" ? { url: editText.trim() } : { text: editText };
      const upd = await api.editFeedPost(p.id, body);
      setPosts((list) => list.map((x) => (x.id === p.id ? upd : x)));
      setEditingId(null);
    } catch {
      /* ignora */
    }
  }

  function onPaste(e: React.ClipboardEvent) {
    const items = e.clipboardData?.items;
    if (!items) return;
    for (const it of items) {
      if (it.type.startsWith("image/")) {
        const file = it.getAsFile();
        if (file) {
          e.preventDefault();
          fileToDataUrl(file).then(setImageData);
        }
        return;
      }
    }
  }

  function onDrop(e: React.DragEvent) {
    e.preventDefault();
    const file = Array.from(e.dataTransfer?.files ?? []).find((f) => f.type.startsWith("image/"));
    if (file) fileToDataUrl(file).then(setImageData);
  }

  const hint =
    kind === "x" ? t.hintX : kind === "image" ? t.hintImg : text.trim() ? t.hintText : "";

  return (
    <div className="card">
      <div className="card-title">
        <span>{t.title}</span>
        {total > 0 && (
          <span className="ml-auto text-xs font-normal normal-case text-[var(--color-muted)]">
            {total} {total === 1 ? t.post1 : t.postN}
          </span>
        )}
      </div>

      {/* Añadir publicación */}
      <div
        className="mb-4 rounded-lg border border-[var(--color-line)] bg-[var(--color-panel-2)] p-2"
        onDrop={onDrop}
        onDragOver={(e) => e.preventDefault()}
      >
        <textarea
          className="w-full resize-y bg-transparent text-sm text-[var(--color-ink)] outline-none placeholder:text-[var(--color-muted)]"
          rows={2}
          placeholder={t.placeholder}
          value={text}
          onChange={(e) => setText(e.target.value)}
          onPaste={onPaste}
        />
        {imageData && (
          <div className="relative mt-2 inline-block">
            <img
              src={imageData}
              alt=""
              className="max-h-40 rounded-lg border border-[var(--color-line)]"
            />
            <button
              onClick={() => setImageData(null)}
              className="absolute -right-2 -top-2 flex h-5 w-5 items-center justify-center rounded-full bg-[var(--color-bear)] text-xs text-white"
              title={t.removeImg}
            >
              ×
            </button>
          </div>
        )}
        <div className="mt-2 flex items-center gap-2">
          <input
            ref={fileRef}
            type="file"
            accept="image/*"
            className="hidden"
            onChange={(e) => {
              const f = e.target.files?.[0];
              if (f) fileToDataUrl(f).then(setImageData);
              e.target.value = "";
            }}
          />
          <button className="btn-ghost text-xs" onClick={() => fileRef.current?.click()}>
            {t.image}
          </button>
          {hint && <span className="text-xs text-[var(--color-muted)]">{hint}</span>}
          <button className="btn ml-auto" onClick={submit} disabled={!canPost || busy}>
            {busy ? t.posting : t.publish}
          </button>
        </div>
      </div>

      {error && <p className="mb-3 text-sm text-[var(--color-bear)]">{error}</p>}

      {/* Publicaciones (más nuevas primero) */}
      {posts.length === 0 ? (
        <p className="text-sm text-[var(--color-muted)]">{t.empty}</p>
      ) : (
        <div className="space-y-3">
          {posts.map((p) => (
            <div
              key={p.id}
              className="rounded-lg border border-[var(--color-line)] bg-[var(--color-panel-2)] p-3"
            >
              <div className="mb-1.5 flex items-center gap-2">
                <span className="text-xs text-[var(--color-muted)]">
                  {fmtDateTime(p.created_at)}
                </span>
                <div className="ml-auto flex gap-1 text-xs">
                  <button
                    className="text-[var(--color-muted)] hover:text-[var(--color-accent)]"
                    title={t.edit}
                    onClick={() => startEdit(p)}
                  >
                    ✏️
                  </button>
                  <button
                    className="text-[var(--color-muted)] hover:text-[var(--color-bear)]"
                    title={t.del}
                    onClick={() => del(p.id)}
                  >
                    🗑️
                  </button>
                </div>
              </div>

              {editingId === p.id ? (
                <div>
                  <textarea
                    className="input"
                    rows={p.kind === "x" ? 1 : 3}
                    value={editText}
                    onChange={(e) => setEditText(e.target.value)}
                  />
                  <div className="mt-2 flex gap-2">
                    <button className="btn text-xs" onClick={() => saveEdit(p)}>
                      {t.save}
                    </button>
                    <button className="btn-ghost text-xs" onClick={() => setEditingId(null)}>
                      {t.cancel}
                    </button>
                  </div>
                </div>
              ) : (
                <>
                  {p.kind === "x" && p.url && <Tweet url={p.url} />}

                  {p.kind === "image" && p.image && (
                    <a
                      href={`/api/feed/image/${p.image}`}
                      target="_blank"
                      rel="noopener noreferrer"
                    >
                      <img
                        src={`/api/feed/image/${p.image}`}
                        alt=""
                        className="max-h-96 w-auto rounded-lg border border-[var(--color-line)]"
                      />
                    </a>
                  )}

                  {p.text && (
                    <div className="md mt-1">
                      <ReactMarkdown>{p.text}</ReactMarkdown>
                    </div>
                  )}
                </>
              )}
            </div>
          ))}

          {posts.length < total && (
            <button className="btn-ghost w-full text-sm" onClick={loadMore}>
              {t.more} ({total - posts.length})
            </button>
          )}
        </div>
      )}
    </div>
  );
}
