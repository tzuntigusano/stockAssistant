#!/usr/bin/env bash
# Arranca el analizador en macOS / Linux.
# La primera vez crea el entorno de Python e instala dependencias solo.
# Uso:  ./start.sh    (o doble clic en Iniciar-App.command en macOS)

set -e
ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

# --- Comprobaciones ---
PY="$(command -v python3 || command -v python || true)"
if [ -z "$PY" ]; then
  echo "❌ No se encontró Python 3. Instálalo desde https://www.python.org/downloads/  (o 'brew install python')."
  exit 1
fi
if ! command -v npm >/dev/null 2>&1; then
  echo "❌ No se encontró Node.js/npm. Instálalo desde https://nodejs.org  (o 'brew install node')."
  exit 1
fi

# --- Backend: entorno + dependencias (solo la primera vez) ---
if [ ! -d "backend/venv" ]; then
  echo "📦 Creando entorno de Python e instalando dependencias (primera vez, tarda un poco)…"
  "$PY" -m venv backend/venv
  backend/venv/bin/python -m pip install --upgrade pip
  backend/venv/bin/python -m pip install -r backend/requirements.txt
fi

# --- Frontend: dependencias (solo la primera vez) ---
if [ ! -d "frontend/node_modules" ]; then
  echo "📦 Instalando dependencias del frontend (primera vez)…"
  (cd frontend && npm install)
fi

# --- .env (avisa si falta) ---
if [ ! -f "backend/.env" ]; then
  echo "⚠️  No hay backend/.env. Copia backend/.env.example a backend/.env y pon tus claves (opcional para arrancar)."
fi

# Cierra cualquier backend anterior ocupando el puerto 8000
if command -v lsof >/dev/null 2>&1; then
  lsof -ti tcp:8000 | xargs kill -9 2>/dev/null || true
fi

echo "🚀 Backend  → http://localhost:8000"
(cd backend && venv/bin/python -m uvicorn main:app --port 8000) &
BACK_PID=$!

echo "🚀 Frontend → http://localhost:5173"
(cd frontend && npm run dev) &
FRONT_PID=$!

# Al salir (Ctrl+C), para ambos procesos
trap 'kill $BACK_PID $FRONT_PID 2>/dev/null' EXIT INT TERM

# Abre el navegador
sleep 5
if command -v open >/dev/null 2>&1; then
  open "http://localhost:5173"          # macOS
elif command -v xdg-open >/dev/null 2>&1; then
  xdg-open "http://localhost:5173"      # Linux
fi

echo "✅ Listo. Cierra esta ventana o pulsa Ctrl+C para parar."
wait
