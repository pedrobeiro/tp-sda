# Sistema de Controle do Drone – Instruções de Execução

Este sistema utiliza três programas que trabalham simultaneamente para controlar um drone simulado no CoppeliaSim usando OPC UA e um supervisório TCP/IP.

Antes de começar, **certifique-se de que**:

1. **CoppeliaSim** está aberto com o arquivo `drone.ttt` carregado.  
2. **Prosys OPC UA Simulation Server** está em execução, com o objeto `Drone` contendo as variáveis:  
   - `DroneX`, `DroneY`, `DroneZ`  
   - `TargetX`, `TargetY`, `TargetZ`

---

## 🚀 Como Executar o Sistema

Abra **três terminais** (ou três abas) e execute um script em cada um conforme instruções abaixo.

---

## 🟦 Terminal 1 — Ponte CoppeliaSim ⇄ OPC UA

Execute:
```
python3 bridge.py
```


Este módulo faz a ponte entre o CoppeliaSim e o Prosys, lendo a posição real do drone e movendo o alvo suavemente em direção ao comando `Target`.

---

## 🟩 Terminal 2 — CLP (OPC + TCP)

Execute:

```
python3 CLP.py
```

O CLP é responsável por:

- Ler `DroneX/Y/Z` do OPC UA  
- Enviar `TargetX/Y/Z` ao OPC UA  
- Servir dados via TCP/IP para o supervisório  
- Receber comandos `TARGET` e enviar status  

---

## 🟧 Terminal 3 — Supervisório (Interface Gráfica)

Execute:

```
python3 supervisorio.py
```

O supervisório permite:

- Escolher bandejas para inspeção (envio automático de `TARGET`)  
- Visualizar posição do drone em tempo real  
- Exibir timestamp  
- Registrar histórico em **historiador.txt**  

---