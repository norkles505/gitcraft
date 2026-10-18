#!/usr/bin/env bash
# iniciar.sh - Prepara el entorno y ejecuta o compila GitCraft.
#   ./iniciar.sh              Instala dependencias y abre la app
#   ./iniciar.sh --compilar   Genera un ejecutable en dist/gitcraft
set -euo pipefail

cd "$(dirname "$(readlink -f "$0")")"

VENV=".venv"

preparar_entorno() {
    if [ ! -d "$VENV" ]; then
        echo ">> Creando entorno virtual..."
        python3 -m venv "$VENV"
    fi
    echo ">> Instalando dependencias..."
    "$VENV/bin/pip" install --quiet --upgrade pip
    "$VENV/bin/pip" install --quiet -r requirements.txt
}

case "${1:-}" in
    "")
        preparar_entorno
        echo ">> Iniciando GitCraft..."
        exec "$VENV/bin/python" main.py
        ;;
    --compilar|-c)
        preparar_entorno
        "$VENV/bin/pip" install --quiet pyinstaller
        echo ">> Compilando..."
        "$VENV/bin/pyinstaller" --noconfirm --clean --onefile --windowed --name gitcraft main.py
        echo ">> Listo: dist/gitcraft"
        ;;
    --ayuda|-h|--help)
        sed -n '2,4p' "$0"
        ;;
    *)
        echo "Opción desconocida: $1 (usa --ayuda)" >&2
        exit 1
        ;;
esac
