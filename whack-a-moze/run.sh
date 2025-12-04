#!/bin/bash

# Função para matar todos os processos ao receber Ctrl+C
cleanup() {
    echo ""
    echo "Encerrando todos os processos..."
    kill $(jobs -p) 2>/dev/null
    exit 0
}

# Captura Ctrl+C (SIGINT) e Ctrl+Z (SIGTSTP)
trap cleanup SIGINT SIGTERM

echo "Iniciando simulação do drone..."
echo "Pressione Ctrl+C para encerrar todos os processos"
echo ""

echo "1. Executando bridge.py..."
python3 bridge.py &
sleep 1

echo "2. Executando CLP.py..."
python3 CLP.py &
sleep 1

echo "3. Executando supervisorio.py..."
python3 supervisorio.py &
sleep 1

echo "4. Executando chained_server.py..."
python3 chained_server.py &
sleep 1

echo "5. Executando MES.py..."
python3 MES.py &

echo "5. Executando WHACK-A-MOZE!..."
python3 whack-a-moze.py &


echo ""
echo "Todos os processos iniciados! Aguardando execução..."
echo "Pressione Ctrl+C para encerrar"

wait