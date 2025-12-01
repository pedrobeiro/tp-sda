# Sistema de Controle do Drone – Instruções de Execução

Este sistema utiliza **cinco programas** que trabalham simultaneamente para controlar um drone simulado no CoppeliaSim usando OPC UA, um supervisório TCP/IP e uma arquitetura em *chained server* para integração com um sistema MES.

Antes de começar, **certifique-se de que**:

1. **CoppeliaSim** está aberto com o arquivo `drone.ttt` carregado.  
2. **Prosys OPC UA Simulation Server** está em execução, com o objeto `Drone` contendo as variáveis:  
   - `DroneX`, `DroneY`, `DroneZ`  
   - `TargetX`, `TargetY`, `TargetZ`

---

## 🚀 Como Executar o Sistema

Abra **cinco terminais** (ou cinco abas) e execute um script em cada um conforme instruções abaixo.

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
- Registrar histórico em historiador.txt  

---

## 🟨 Terminal 4 — Servidor Encadeado OPC UA (Chained Server)

Execute:

```
python3 chained_server.py
```

Este módulo implementa o servidor OPC UA encadeado (chained server), com a seguinte função:

- Atua como cliente OPC UA do Prosys Simulation Server, lendo continuamente:  
  - `DroneX`, `DroneY`, `DroneZ`  
  - `TargetX`, `TargetY`, `TargetZ`  
- Publica essas mesmas variáveis em um novo servidor OPC UA, no endpoint:  
  - `opc.tcp://localhost:54000/OPCUA/ChainedServer`  
- Exponde um novo objeto `Drone` com as variáveis espelhadas, para consumo por outros clientes (no caso, o MES).

Em termos práticos, ele faz o “espelhamento” das informações do drone em um segundo servidor OPC UA, sem afetar a lógica já existente do CLP, do supervisório ou da ponte com o CoppeliaSim.

---

## 🟥 Terminal 5 — MES (Cliente OPC UA + Registro em mes.txt)

Execute:

```
python3 mes.py
```

O módulo MES é um cliente OPC UA que se conecta ao servidor encadeado (chained_server.py) e realiza:

- Leitura periódica das variáveis:  
  - `DroneX`, `DroneY`, `DroneZ`  
  - `TargetX`, `TargetY`, `TargetZ`  
- Registro das informações em um arquivo chamado mes.txt, incluindo timestamp, no formato texto, por exemplo:

```
AAAA-MM-DD HH:MM:SS.mmm; DRONE_X=x_atual; DRONE_Y=y_atual; DRONE_Z=z_atual; TARGET_X=x_desejado; TARGET_Y=y_desejado; TARGET_Z=z_desejado
```

Esse arquivo representa o log do sistema MES, armazenando os dados de processo que poderiam ser usados posteriormente para rastreabilidade, análise de produção, indicadores etc.

---

## 🔁 Visão Geral da Arquitetura

Resumindo o fluxo de dados:

- CoppeliaSim  
  ⇄ bridge.py  
  ⇄ Prosys OPC UA Simulation Server (objeto `Drone`)  
  ⇄ CLP.py (cliente OPC + servidor TCP)  
  ⇄ supervisorio.py (cliente TCP com interface gráfica e historiador)

Em paralelo, para o MES:

- Prosys OPC UA Simulation Server  
  ⇄ chained_server.py (cliente OPC + novo servidor OPC encadeado)  
  ⇄ mes.py (cliente OPC que grava mes.txt)

Assim, o requisito da arquitetura de chained server é atendido: há um segundo cliente OPC UA encapsulado em outro servidor OPC UA, que fornece as mesmas informações do drone para um cliente MES, responsável por salvar os dados de processo em mes.txt.
