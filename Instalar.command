#!/usr/bin/env bash
# Doble clic en Finder (macOS) para lanzar el instalador guiado.
# La primera vez, si macOS no deja ejecutarlo, abre Terminal en esta carpeta y:
#   chmod +x Instalar.command instalar.sh start.sh
cd "$(dirname "$0")"
exec ./instalar.sh
