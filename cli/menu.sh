#!/usr/bin/env bash
# cli/menu.sh
# Wrapper simples para executar o menu Python

# Obtém o diretório onde o script está localizado
SCRIPT_DIR="$( cd "$( dirname "${BASH_SOURCE[0]}" )" && pwd )"
WORKSPACE_DIR="$( cd "$SCRIPT_DIR/.." && pwd )"

# Usa o Python do ambiente virtual se existir
if [ -f "$WORKSPACE_DIR/.venv/bin/python" ]; then
    PYTHON="$WORKSPACE_DIR/.venv/bin/python"
else
    PYTHON="python3"
fi

# Executa o menu Python
cd "$WORKSPACE_DIR"
$PYTHON cli/run.py "$@"
