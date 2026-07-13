# Arranca el backend (FastAPI) y el frontend (Vite) en dos ventanas separadas.
$root = $PSScriptRoot

# Cierra cualquier backend anterior para evitar el error de "puerto 8000 ocupado".
Get-CimInstance Win32_Process -Filter "Name='python.exe'" |
  Where-Object { $_.CommandLine -like '*uvicorn*' } |
  ForEach-Object { Stop-Process -Id $_.ProcessId -Force -ErrorAction SilentlyContinue }

Write-Host "Arrancando backend en http://localhost:8000 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
  '-NoExit', '-Command',
  "cd '$root\backend'; .\venv\Scripts\python.exe -m uvicorn main:app --port 8000"
)

Write-Host "Arrancando frontend en http://localhost:5173 ..." -ForegroundColor Cyan
Start-Process powershell -ArgumentList @(
  '-NoExit', '-Command',
  "cd '$root\frontend'; npm run dev"
)

Start-Sleep -Seconds 5
Write-Host "Abriendo http://localhost:5173 en el navegador..." -ForegroundColor Green
Start-Process "http://localhost:5173"
