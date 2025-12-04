# README – Sistema Distribuído de Controle de Drone

Este repositório contém o trabalho prático da disciplina de Sistemas Distribuídos para Automação (SDA), cujo objetivo é implementar a integração entre um drone simulado no CoppeliaSim, um servidor OPC UA (Prosys), um CLP virtual, um supervisório e uma arquitetura *chained server* para alimentação de um sistema MES.


---

# Estrutura do Projeto

Toda a implementação principal está localizada na pasta **tp**.  
Dentro dela encontram-se:

- `bridge.py`
- `CLP.py`
- `supervisorio.py`
- `chained_server.py`
- `mes.py`
- `run.sh` (script de execução automática)

## Execução completa (via script)

Antes de executar, certifique-se de:

1. Abrir o **CoppeliaSim** com a cena `drone.ttt`.
2. Iniciar o **Prosys OPC UA Simulation Server**, contendo:
   - Objeto `Drone`
   - Variáveis `DroneX`, `DroneY`, `DroneZ`
   - Variáveis `TargetX`, `TargetY`, `TargetZ`

Para rodar tudo automaticamente:

```
./run.sh
```


O script executa todos os módulos necessários.

### Arquivos gerados:

- `historiador.txt` — gerado pelo supervisório  
- `MES.txt` — gerado pelo módulo MES  

---

# Whack-a-Moze – Minigame baseado na arquitetura distribuída

![Cena do projeto](whack-a-moze/assets/jogo.png)

Além da implementação principal, o repositório contém o **Whack-a-Moze**, um minigame que reutiliza integralmente a infraestrutura distribuída do projeto.

No jogo:

- Personagens (Armandos e Mozellis) aparecem aleatoriamente nas bandejas.
- O jogador deve mover o drone até a bandeja correta para capturar o personagem.
- O jogo utiliza:
  - As variáveis OPC UA do drone
  - O CLP virtual
  - O mesmo fluxo de dados Prosys → CLP → Coppelia → supervisório

Para rodar o minigame entre na pasta dele:

```
cd whack-a-moze
```

e rode o script que inicializará todos os módulos necessários.

```
./run.sh
```

O supervisório vai ser aberto e os inimigos começam a aparecer aleatoriamente.

---

# Tutorial Completo – Execução Manual (Terminal por Terminal)

Abaixo está o passo a passo caso você deseje executar cada componente individualmente para depuração.
Os passos são os mesmos tanto para o TP quanto para o jogo.

1. No primeiro terminal, execute:
```
   python3 bridge.py
```

2. No segundo terminal, execute:
```
   python3 CLP.py
```

3. No terceiro terminal, execute:
```
   python3 supervisorio.py
```

4. No quarto terminal, execute:
```
   python3 chained_server.py
```

5. No quinto terminal, execute:
```
   python3 mes.py
```