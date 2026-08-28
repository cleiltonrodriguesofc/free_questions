#!/bin/bash
# Script para rodar o BACEN Study Simulator localmente

echo "Iniciando BACEN Study Simulator..."
echo "==================================="

# Verifica se o ambiente virtual existe, senão aborta
if [ ! -d "venv" ]; then
    echo "Erro: Ambiente virtual 'venv' não encontrado."
    echo "Crie um com: python3 -m venv venv"
    exit 1
fi

# Ativa o ambiente virtual
source venv/bin/activate

# Instala dependências se necessário
if [ -f "requirements.txt" ]; then
    echo "Verificando dependências..."
    pip install -r requirements.txt
fi

# Roda o servidor via uvicorn
echo "Iniciando o servidor FastAPI..."
uvicorn main:app --host 0.0.0.0 --port 8000 --reload
