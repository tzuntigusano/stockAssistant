# ═══════════════════════════════════════════════════════════════════════════
#  Stock Analyzer — GUIDED INSTALLER (Windows) · INSTALADOR GUIADO (Windows)
#
#  Checks/installs Python and Node.js, sets up the environment and asks for your
#  API keys explaining where to get each one. It never deletes keys you already
#  have. Bilingual: it asks your language at the start.
#
#  How to run:  right-click this file → "Run with PowerShell".
#  (If Windows blocks it, open PowerShell in this folder and run:
#      Set-ExecutionPolicy -Scope Process Bypass -Force ; .\Instalar.ps1  )
# ═══════════════════════════════════════════════════════════════════════════

$ErrorActionPreference = "Stop"
$root = $PSScriptRoot
if (-not $root) { $root = (Get-Location).Path }

# ── Idioma / Language ──
Clear-Host
Write-Host ""
Write-Host "  Idioma / Language:" -ForegroundColor Cyan
Write-Host "    [1] Español    [2] English"
$sel = (Read-Host "  > ").Trim()
$script:lang = if ($sel -eq "2") { "en" } else { "es" }
function T($es, $en) { if ($script:lang -eq "en") { return $en } else { return $es } }

function Section($n, $t) { Write-Host ""; Write-Host "──── $n  $t ────" -ForegroundColor Cyan }
function Ok($t)   { Write-Host "  [OK] $t" -ForegroundColor Green }
function Warn($t) { Write-Host "  [!]  $t" -ForegroundColor Yellow }
function Info($t) { Write-Host "       $t" -ForegroundColor DarkGray }
function Ask($t)  { return (Read-Host "  $t") }
function YesNo($t, $default = $true) {
  $hint = if ($default) { T "(S/n)" "(Y/n)" } else { T "(s/N)" "(y/N)" }
  $r = (Read-Host "  $t $hint").Trim().ToLower()
  if ($r -eq "") { return $default }
  return ($r -eq "s" -or $r -eq "si" -or $r -eq "sí" -or $r -eq "y" -or $r -eq "yes")
}

Write-Host ""
Write-Host "  ╔══════════════════════════════════════════════╗" -ForegroundColor Cyan
Write-Host "  ║        STOCK ANALYZER · Installer             ║" -ForegroundColor Cyan
Write-Host "  ╚══════════════════════════════════════════════╝" -ForegroundColor Cyan
Write-Host ""
Info (T "Este asistente hará todo paso a paso. No tienes que saber programar." `
        "This wizard does everything step by step. No coding needed.")
Info (T "Puedes cancelar en cualquier momento con Ctrl+C." `
        "You can cancel anytime with Ctrl+C.")
Write-Host ""
[void](Ask (T "Pulsa ENTER para empezar" "Press ENTER to start"))

# ─────────────────────────────────────────────────────────────── Python ────
Section "1/5" "Python"

function Find-Python {
  foreach ($c in @("python", "python3", "py")) {
    $cmd = Get-Command $c -ErrorAction SilentlyContinue
    if (-not $cmd) { continue }
    try { $v = (& $c --version 2>&1) } catch { continue }
    if ("$v" -match "Python (\d+)\.(\d+)") {
      if ([int]$Matches[1] -eq 3 -and [int]$Matches[2] -ge 10) { return $c }
    }
  }
  return $null
}

$py = Find-Python
if (-not $py) {
  Warn (T "No encuentro Python 3.10 o superior." "Python 3.10+ not found.")
  if (Get-Command winget -ErrorAction SilentlyContinue) {
    if (YesNo (T "¿Lo instalo automáticamente con winget?" "Install it automatically with winget?")) {
      winget install -e --id Python.Python.3.12 --accept-source-agreements --accept-package-agreements
      Write-Host ""
      Warn (T "Python instalado. Windows necesita una terminal nueva para verlo." `
              "Python installed. Windows needs a fresh terminal to see it.")
      Info (T "Cierra esta ventana, abre el instalador otra vez y continuará." `
              "Close this window, run the installer again and it will continue.")
      [void](Ask (T "ENTER para salir" "ENTER to exit")); exit
    }
  } else {
    Info (T "Voy a abrir la web de descarga. IMPORTANTE: marca la casilla" `
            "Opening the download page. IMPORTANT: tick the box")
    Info (T "'Add python.exe to PATH' durante la instalación." `
            "'Add python.exe to PATH' during installation.")
    Start-Process "https://www.python.org/downloads/"
    [void](Ask (T "Cuando lo instales, cierra y reabre esta ventana. ENTER para salir" `
                  "Once installed, close and reopen this window. ENTER to exit")); exit
  }
  $py = Find-Python
}
if (-not $py) { Warn (T "Sigo sin ver Python. Reinicia la terminal y reejecuta." "Still no Python. Restart the terminal and re-run."); exit 1 }
Ok "Python: $(& $py --version)"

# ───────────────────────────────────────────────────────────────── Node ────
Section "2/5" "Node.js"

if (-not (Get-Command npm -ErrorAction SilentlyContinue)) {
  Warn (T "No encuentro Node.js / npm." "Node.js / npm not found.")
  if (Get-Command winget -ErrorAction SilentlyContinue) {
    if (YesNo (T "¿Lo instalo automáticamente con winget?" "Install it automatically with winget?")) {
      winget install -e --id OpenJS.NodeJS.LTS --accept-source-agreements --accept-package-agreements
      Write-Host ""
      Warn (T "Node.js instalado. Cierra esta ventana y reabre el instalador para continuar." `
              "Node.js installed. Close this window and reopen the installer to continue.")
      [void](Ask (T "ENTER para salir" "ENTER to exit")); exit
    }
  } else {
    Info (T "Voy a abrir la web de descarga de Node.js (elige la versión LTS)." `
            "Opening the Node.js download page (choose the LTS version).")
    Start-Process "https://nodejs.org/en/download"
    [void](Ask (T "Cuando lo instales, cierra y reabre esta ventana. ENTER para salir" `
                  "Once installed, close and reopen this window. ENTER to exit")); exit
  }
}
if (-not (Get-Command npm -ErrorAction SilentlyContinue)) { Warn (T "Sigo sin ver npm. Reinicia la terminal." "Still no npm. Restart the terminal."); exit 1 }
Ok "Node.js: $(node --version)  ·  npm: $(npm --version)"

# ─────────────────────────────────────────────────────── Backend (venv) ────
Section "3/5" (T "Preparando el backend (Python)" "Setting up the backend (Python)")

$venvPy = Join-Path $root "backend\venv\Scripts\python.exe"
if (-not (Test-Path $venvPy)) {
  Info (T "Creando entorno virtual (una sola vez)…" "Creating virtual environment (one-time)…")
  & $py -m venv (Join-Path $root "backend\venv")
} else {
  Info (T "El entorno ya existía; reutilizo." "Environment already existed; reusing it.")
}
Info (T "Instalando dependencias de Python (puede tardar un par de minutos)…" `
        "Installing Python dependencies (may take a couple of minutes)…")
& $venvPy -m pip install --upgrade pip --quiet
& $venvPy -m pip install -r (Join-Path $root "backend\requirements.txt") --quiet
Ok (T "Backend listo." "Backend ready.")

# ────────────────────────────────────────────────────── Frontend (npm) ────
Section "4/5" (T "Preparando el frontend (web)" "Setting up the frontend (web)")

if (-not (Test-Path (Join-Path $root "frontend\node_modules"))) {
  Info (T "Instalando dependencias del frontend (puede tardar)…" "Installing frontend dependencies (may take a while)…")
  Push-Location (Join-Path $root "frontend")
  npm install
  Pop-Location
} else {
  Info (T "Las dependencias del frontend ya estaban; reutilizo." "Frontend dependencies already present; reusing them.")
}
Ok (T "Frontend listo." "Frontend ready.")

# ────────────────────────────────────────────────────────── API keys ────
Section "5/5" (T "Claves de acceso (API keys)" "Access keys (API keys)")
Info (T "Todas son OPCIONALES. Pulsa ENTER en cualquiera para omitirla." `
        "All are OPTIONAL. Press ENTER on any to skip it.")
Info (T "Si ya tenías claves puestas, se conservan (ENTER = mantener)." `
        "Any keys you already had are kept (ENTER = keep).")

$envPath = Join-Path $root "backend\.env"
$envMap = [ordered]@{}
if (Test-Path $envPath) {
  foreach ($line in (Get-Content $envPath)) {
    if ($line -match '^\s*#') { continue }
    if ($line -match '^\s*([A-Za-z0-9_]+)\s*=\s*(.*)$') { $envMap[$Matches[1]] = $Matches[2].Trim() }
  }
}

function Mask($v) {
  if ($v.Length -gt 8) { return $v.Substring(0, 4) + "…" + $v.Substring($v.Length - 3) }
  elseif ($v.Length -gt 0) { return "•••" }
  else { return "" }
}

function AskKey($name, $title, $desc, $url) {
  Write-Host ""
  Write-Host "  · $title" -ForegroundColor White
  Info $desc
  if ($url) {
    Info (T "Conseguirla aquí:  $url" "Get it here:  $url")
    if (YesNo (T "¿Abro esa web en el navegador?" "Open that page in the browser?") $false) { Start-Process $url }
  }
  $cur = if ($envMap.Contains($name)) { $envMap[$name] } else { "" }
  if ($cur) {
    $v = Ask ("$name  [$(Mask $cur)] " + (T "(ENTER = mantener)" "(ENTER = keep)"))
    if ($v.Trim() -eq "") { return $cur } else { return $v.Trim() }
  }
  $v = Ask ("$name  " + (T "(ENTER para omitir)" "(ENTER to skip)"))
  return $v.Trim()
}

$envMap["GEMINI_API_KEY"] = AskKey "GEMINI_API_KEY" `
  (T "IA en la nube — Gemini (recomendada)" "Cloud AI — Gemini (recommended)") `
  (T "Redacta los análisis y permite controlar el gráfico por chat. Tiene nivel gratuito." `
     "Writes the analysis and lets you control the chart by chat. Has a free tier.") `
  "https://aistudio.google.com/apikey"

$envMap["FINNHUB_API_KEY"] = AskKey "FINNHUB_API_KEY" `
  (T "Precio en tiempo real — Finnhub" "Real-time price — Finnhub") `
  (T "Sin esto el precio va con retraso (Yahoo). Registro gratis en 1 minuto." `
     "Without it the price is delayed (Yahoo). Free sign-up in 1 minute.") `
  "https://finnhub.io/register"

Write-Host ""
if (YesNo (T "¿Quieres configurar alertas al MÓVIL por Telegram?" "Set up MOBILE alerts via Telegram?") $false) {
  Info (T "1) Abre Telegram, busca @BotFather, envía /newbot y sigue los pasos." `
          "1) Open Telegram, find @BotFather, send /newbot and follow the steps.")
  Info (T "2) Te dará un token; pégalo aquí abajo." "2) It gives you a token; paste it below.")
  $envMap["TELEGRAM_BOT_TOKEN"] = AskKey "TELEGRAM_BOT_TOKEN" `
    (T "Token del bot de Telegram" "Telegram bot token") `
    (T "Lo da @BotFather al crear el bot." "Given by @BotFather when you create the bot.") `
    "https://t.me/BotFather"
  Info (T "El chat_id se detecta luego: escribe 'hola' a tu bot, arranca la app y abre" `
          "The chat_id is detected later: message your bot, start the app and open")
  Info "http://localhost:8000/api/telegram/detect"
  $envMap["TELEGRAM_CHAT_ID"] = AskKey "TELEGRAM_CHAT_ID" `
    (T "chat_id de Telegram" "Telegram chat_id") `
    (T "Puedes dejarlo vacío y rellenarlo después." "You can leave it empty and fill it later.") `
    $null
}

# Valores por defecto útiles si no existían.
if (-not $envMap.Contains("GEMINI_MODEL")) { $envMap["GEMINI_MODEL"] = "gemini-2.5-flash" }
if (-not $envMap.Contains("OLLAMA_MODEL")) { $envMap["OLLAMA_MODEL"] = "qwen3.6:latest" }

# Escribe backend/.env conservando cualquier otra clave que ya hubiera.
$known = @("GEMINI_API_KEY", "GEMINI_MODEL", "OLLAMA_MODEL", "FINNHUB_API_KEY", "TELEGRAM_BOT_TOKEN", "TELEGRAM_CHAT_ID")
$out = New-Object System.Collections.Generic.List[string]
$out.Add("# Stock Analyzer .env — " + (T "generado por Instalar.ps1." "generated by Instalar.ps1."))
$out.Add("GEMINI_API_KEY=$($envMap['GEMINI_API_KEY'])")
$out.Add("GEMINI_MODEL=$($envMap['GEMINI_MODEL'])")
$out.Add("OLLAMA_MODEL=$($envMap['OLLAMA_MODEL'])")
$out.Add("FINNHUB_API_KEY=$($envMap['FINNHUB_API_KEY'])")
$out.Add("TELEGRAM_BOT_TOKEN=$($envMap['TELEGRAM_BOT_TOKEN'])")
$out.Add("TELEGRAM_CHAT_ID=$($envMap['TELEGRAM_CHAT_ID'])")
foreach ($k in $envMap.Keys) {
  if ($known -notcontains $k) { $out.Add("$k=$($envMap[$k])") }
}
Set-Content -Path $envPath -Value $out -Encoding UTF8
Ok (T "Claves guardadas en backend\.env" "Keys saved to backend\.env")

# ─────────────────────────────────────────────────────────────── Final ────
Write-Host ""
Write-Host ("  ✔ " + (T "TODO LISTO" "ALL DONE")) -ForegroundColor Green
Info (T "A partir de ahora, para usar la app haz doble clic en 'Iniciar-App.bat'" `
        "From now on, to use the app double-click 'Iniciar-App.bat'")
Info (T "o ejecuta  .\start.ps1" "or run  .\start.ps1")
Write-Host ""
if (YesNo (T "¿Arranco la app ahora?" "Start the app now?")) {
  & (Join-Path $root "start.ps1")
} else {
  [void](Ask (T "ENTER para cerrar" "ENTER to close"))
}
