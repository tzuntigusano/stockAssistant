#!/usr/bin/env bash
# ═══════════════════════════════════════════════════════════════════════════
#  Stock Analyzer — GUIDED INSTALLER (macOS / Linux) · INSTALADOR GUIADO
#
#  Checks/installs Python and Node.js, sets up the environment and asks for your
#  API keys explaining where to get each one. It never deletes keys you already
#  have. Bilingual: it asks your language at the start.
#
#  How to run:  ./instalar.sh   (on macOS you can also double-click Instalar.command)
# ═══════════════════════════════════════════════════════════════════════════

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

CYAN=$'\033[36m'; GREEN=$'\033[32m'; YELLOW=$'\033[33m'; DIM=$'\033[2m'; WHITE=$'\033[97m'; RESET=$'\033[0m'

# ── Idioma / Language ──
clear
echo
echo "  ${CYAN}Idioma / Language:${RESET}"
echo "    [1] Español    [2] English"
read -rp "  > " sel
if [ "$sel" = "2" ]; then LANG_SEL="en"; else LANG_SEL="es"; fi
t() { if [ "$LANG_SEL" = "en" ]; then printf '%s' "$2"; else printf '%s' "$1"; fi; }

section() { echo; echo "${CYAN}──── $1  $2 ────${RESET}"; }
ok()      { echo "${GREEN}  [OK] $1${RESET}"; }
warn()    { echo "${YELLOW}  [!]  $1${RESET}"; }
info()    { echo "${DIM}       $1${RESET}"; }

yesno() { # $1=question  $2=default(y/n)
  local ans hint
  if [ "$2" = "y" ]; then hint="$(t '(S/n)' '(Y/n)')"; else hint="$(t '(s/N)' '(y/N)')"; fi
  read -rp "  $1 $hint " ans
  ans="$(printf '%s' "$ans" | tr '[:upper:]' '[:lower:]')"
  if [ -z "$ans" ]; then [ "$2" = "y" ]; return; fi
  case "$ans" in s | si | sí | y | yes) return 0 ;; *) return 1 ;; esac
}

openurl() {
  if command -v open >/dev/null 2>&1; then open "$1"
  elif command -v xdg-open >/dev/null 2>&1; then xdg-open "$1"; fi
}

echo
echo "  ${CYAN}╔══════════════════════════════════════════════╗${RESET}"
echo "  ${CYAN}║        STOCK ANALYZER · Installer            ║${RESET}"
echo "  ${CYAN}╚══════════════════════════════════════════════╝${RESET}"
echo
info "$(t 'Este asistente hará todo paso a paso. No tienes que saber programar.' \
         'This wizard does everything step by step. No coding needed.')"
info "$(t 'Puedes cancelar en cualquier momento con Ctrl+C.' \
         'You can cancel anytime with Ctrl+C.')"
echo
read -rp "  $(t 'Pulsa ENTER para empezar' 'Press ENTER to start') "

# ─────────────────────────────────────────────────────────────── Python ────
section "1/5" "Python"

find_python() {
  local c v maj min
  for c in python3 python; do
    command -v "$c" >/dev/null 2>&1 || continue
    v="$("$c" -c 'import sys;print("%d.%d"%sys.version_info[:2])' 2>/dev/null)" || continue
    maj="${v%%.*}"; min="${v##*.}"
    if [ "$maj" = "3" ] && [ "${min:-0}" -ge 10 ] 2>/dev/null; then echo "$c"; return; fi
  done
}

PY="$(find_python)"
if [ -z "$PY" ]; then
  warn "$(t 'No encuentro Python 3.10 o superior.' 'Python 3.10+ not found.')"
  if command -v brew >/dev/null 2>&1; then
    if yesno "$(t '¿Lo instalo con Homebrew (brew install python)?' 'Install it with Homebrew (brew install python)?')" y; then
      brew install python
    fi
  else
    info "$(t 'Voy a abrir la web de descarga de Python.' 'Opening the Python download page.')"
    info "$(t '(en macOS también puedes instalar Homebrew desde https://brew.sh y luego: brew install python)' \
             '(on macOS you can also install Homebrew from https://brew.sh then: brew install python)')"
    openurl "https://www.python.org/downloads/"
    read -rp "  $(t 'Cuando lo instales, cierra y reabre la terminal y reejecuta. ENTER para salir' \
                    'Once installed, close and reopen the terminal and re-run. ENTER to exit') "
    exit 0
  fi
  PY="$(find_python)"
fi
[ -z "$PY" ] && { warn "$(t 'Sigo sin ver Python. Reinicia la terminal y reejecuta.' 'Still no Python. Restart the terminal and re-run.')"; exit 1; }
ok "Python: $("$PY" --version 2>&1)"

# ───────────────────────────────────────────────────────────────── Node ────
section "2/5" "Node.js"

if ! command -v npm >/dev/null 2>&1; then
  warn "$(t 'No encuentro Node.js / npm.' 'Node.js / npm not found.')"
  if command -v brew >/dev/null 2>&1; then
    if yesno "$(t '¿Lo instalo con Homebrew (brew install node)?' 'Install it with Homebrew (brew install node)?')" y; then
      brew install node
    fi
  else
    info "$(t 'Voy a abrir la web de descarga de Node.js (elige la versión LTS).' \
             'Opening the Node.js download page (choose the LTS version).')"
    openurl "https://nodejs.org/en/download"
    read -rp "  $(t 'Cuando lo instales, cierra y reabre la terminal y reejecuta. ENTER para salir' \
                    'Once installed, close and reopen the terminal and re-run. ENTER to exit') "
    exit 0
  fi
fi
command -v npm >/dev/null 2>&1 || { warn "$(t 'Sigo sin ver npm. Reinicia la terminal.' 'Still no npm. Restart the terminal.')"; exit 1; }
ok "Node.js: $(node --version)  ·  npm: $(npm --version)"

# ─────────────────────────────────────────────────────── Backend (venv) ────
section "3/5" "$(t 'Preparando el backend (Python)' 'Setting up the backend (Python)')"

if [ ! -d "backend/venv" ]; then
  info "$(t 'Creando entorno virtual (una sola vez)…' 'Creating virtual environment (one-time)…')"
  "$PY" -m venv backend/venv
else
  info "$(t 'El entorno ya existía; reutilizo.' 'Environment already existed; reusing it.')"
fi
info "$(t 'Instalando dependencias de Python (puede tardar un par de minutos)…' \
         'Installing Python dependencies (may take a couple of minutes)…')"
backend/venv/bin/python -m pip install --upgrade pip --quiet
backend/venv/bin/python -m pip install -r backend/requirements.txt --quiet
ok "$(t 'Backend listo.' 'Backend ready.')"

# ────────────────────────────────────────────────────── Frontend (npm) ────
section "4/5" "$(t 'Preparando el frontend (web)' 'Setting up the frontend (web)')"

if [ ! -d "frontend/node_modules" ]; then
  info "$(t 'Instalando dependencias del frontend (puede tardar)…' 'Installing frontend dependencies (may take a while)…')"
  (cd frontend && npm install)
else
  info "$(t 'Las dependencias del frontend ya estaban; reutilizo.' 'Frontend dependencies already present; reusing them.')"
fi
ok "$(t 'Frontend listo.' 'Frontend ready.')"

# ────────────────────────────────────────────────────────── API keys ────
section "5/5" "$(t 'Claves de acceso (API keys)' 'Access keys (API keys)')"
info "$(t 'Todas son OPCIONALES. Pulsa ENTER en cualquiera para omitirla.' \
         'All are OPTIONAL. Press ENTER on any to skip it.')"
info "$(t 'Si ya tenías claves puestas, se conservan (ENTER = mantener).' \
         'Any keys you already had are kept (ENTER = keep).')"

ENV="backend/.env"
env_get() { [ -f "$ENV" ] || return; grep -E "^$1=" "$ENV" | tail -1 | cut -d= -f2-; }
mask() {
  local v="$1" n=${#1}
  if [ "$n" -gt 8 ]; then printf '%s…%s' "${v:0:4}" "${v: -3}"
  elif [ "$n" -gt 0 ]; then printf '•••'; fi
}

REPLY_KEY=""
ask_key() { # $1=name $2=title $3=desc $4=url
  local name="$1" title="$2" desc="$3" url="$4" cur ans
  echo; echo "  ${WHITE}· $title${RESET}"
  info "$desc"
  cur="$(env_get "$name")"
  if [ -n "$url" ]; then
    info "$(t "Conseguirla aquí:  $url" "Get it here:  $url")"
    if yesno "$(t '¿Abro esa web en el navegador?' 'Open that page in the browser?')" n; then openurl "$url"; fi
  fi
  if [ -n "$cur" ]; then
    read -rp "  $name  [$(mask "$cur")] $(t '(ENTER = mantener)' '(ENTER = keep)'): " ans
    if [ -z "$ans" ]; then REPLY_KEY="$cur"; else REPLY_KEY="$ans"; fi
  else
    read -rp "  $name  $(t '(ENTER para omitir)' '(ENTER to skip)'): " ans
    REPLY_KEY="$ans"
  fi
}

ask_key "GEMINI_API_KEY" \
  "$(t 'IA en la nube — Gemini (recomendada)' 'Cloud AI — Gemini (recommended)')" \
  "$(t 'Redacta los análisis y permite controlar el gráfico por chat. Tiene nivel gratuito.' \
      'Writes the analysis and lets you control the chart by chat. Has a free tier.')" \
  "https://aistudio.google.com/apikey"
GEMINI_API_KEY="$REPLY_KEY"

ask_key "FINNHUB_API_KEY" \
  "$(t 'Precio en tiempo real — Finnhub' 'Real-time price — Finnhub')" \
  "$(t 'Sin esto el precio va con retraso (Yahoo). Registro gratis en 1 minuto.' \
      'Without it the price is delayed (Yahoo). Free sign-up in 1 minute.')" \
  "https://finnhub.io/register"
FINNHUB_API_KEY="$REPLY_KEY"

TELEGRAM_BOT_TOKEN="$(env_get TELEGRAM_BOT_TOKEN)"
TELEGRAM_CHAT_ID="$(env_get TELEGRAM_CHAT_ID)"
echo
if yesno "$(t '¿Quieres configurar alertas al MÓVIL por Telegram?' 'Set up MOBILE alerts via Telegram?')" n; then
  info "$(t '1) Abre Telegram, busca @BotFather, envía /newbot y sigue los pasos.' \
           '1) Open Telegram, find @BotFather, send /newbot and follow the steps.')"
  info "$(t '2) Te dará un token; pégalo aquí abajo.' '2) It gives you a token; paste it below.')"
  ask_key "TELEGRAM_BOT_TOKEN" \
    "$(t 'Token del bot de Telegram' 'Telegram bot token')" \
    "$(t 'Lo da @BotFather al crear el bot.' 'Given by @BotFather when you create the bot.')" \
    "https://t.me/BotFather"
  TELEGRAM_BOT_TOKEN="$REPLY_KEY"
  info "$(t "El chat_id se detecta luego: escribe 'hola' a tu bot, arranca la app y abre" \
           'The chat_id is detected later: message your bot, start the app and open')"
  info "http://localhost:8000/api/telegram/detect"
  ask_key "TELEGRAM_CHAT_ID" \
    "$(t 'chat_id de Telegram' 'Telegram chat_id')" \
    "$(t 'Puedes dejarlo vacío y rellenarlo después.' 'You can leave it empty and fill it later.')" \
    ""
  TELEGRAM_CHAT_ID="$REPLY_KEY"
fi

GEMINI_MODEL="$(env_get GEMINI_MODEL)"; [ -z "$GEMINI_MODEL" ] && GEMINI_MODEL="gemini-2.5-flash"
OLLAMA_MODEL="$(env_get OLLAMA_MODEL)"; [ -z "$OLLAMA_MODEL" ] && OLLAMA_MODEL="qwen3.6:latest"

# Conserva cualquier OTRA clave que ya hubiera en el .env.
EXTRAS=""
if [ -f "$ENV" ]; then
  EXTRAS="$(grep -E '^[A-Za-z0-9_]+=' "$ENV" | grep -vE '^(GEMINI_API_KEY|GEMINI_MODEL|OLLAMA_MODEL|FINNHUB_API_KEY|TELEGRAM_BOT_TOKEN|TELEGRAM_CHAT_ID)=' || true)"
fi

{
  echo "# Stock Analyzer .env — $(t 'generado por instalar.sh.' 'generated by instalar.sh.')"
  echo "GEMINI_API_KEY=$GEMINI_API_KEY"
  echo "GEMINI_MODEL=$GEMINI_MODEL"
  echo "OLLAMA_MODEL=$OLLAMA_MODEL"
  echo "FINNHUB_API_KEY=$FINNHUB_API_KEY"
  echo "TELEGRAM_BOT_TOKEN=$TELEGRAM_BOT_TOKEN"
  echo "TELEGRAM_CHAT_ID=$TELEGRAM_CHAT_ID"
  [ -n "$EXTRAS" ] && echo "$EXTRAS"
} >"$ENV"
ok "$(t 'Claves guardadas en backend/.env' 'Keys saved to backend/.env')"

# ─────────────────────────────────────────────────────────────── Final ────
echo
echo "  ${GREEN}✔ $(t 'TODO LISTO' 'ALL DONE')${RESET}"
info "$(t 'A partir de ahora, para usar la app ejecuta  ./start.sh' \
         'From now on, to use the app run  ./start.sh')"
info "$(t "(en macOS también puedes hacer doble clic en 'Iniciar-App.command')" \
         "(on macOS you can also double-click 'Iniciar-App.command')")"
echo
if yesno "$(t '¿Arranco la app ahora?' 'Start the app now?')" y; then
  exec ./start.sh
fi
