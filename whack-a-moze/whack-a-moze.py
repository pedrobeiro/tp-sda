import time
import random
import socket
import threading
from coppeliasim_zmqremoteapi_client import RemoteAPIClient

############################
# CONFIG
############################
TRAY_COUNT = 4
SPAWN_INTERVAL = 2.0
DISPLAY_TIME = 8.0
HIDDEN_POS = [0, 0, -1]
Z_OFFSET = 0.2
CAPTURE_TOLERANCE = 1  # metros

TCP_HOST = "0.0.0.0"
TCP_PORT = 5001

############################
# Estado do jogo
############################
class EstadoJogo:
    def __init__(self):
        self.lock = threading.Lock()
        self.objeto_ativo = None
        self.objeto_handle = None
        self.pos_objeto = [0, 0, -1]
        self.score = 0
        self.vidas = 3
        self.capturado = False
        self.game_over = False  # NOVO

    def spawnar_objeto(self, nome, handle, pos):
        with self.lock:
            self.objeto_ativo = nome
            self.objeto_handle = handle
            self.pos_objeto = pos.copy()
            self.capturado = False
            print(f"[ESTADO] Objeto {nome} spawnado em ({pos[0]:.2f}, {pos[1]:.2f}, {pos[2]:.2f})")

    def remover_objeto(self):
        with self.lock:
            self.objeto_ativo = None
            self.objeto_handle = None
            self.pos_objeto = [0, 0, -1]
            self.capturado = False

    def foi_capturado(self):
        with self.lock:
            return self.capturado

    def tentar_captura(self, nome_clicado, pos_drone):
        with self.lock:
            if self.game_over:
                return "ERRO GAME_OVER", None

            print(f"\n[CAPTURA] Tentativa de capturar '{nome_clicado}'")
            print(f"[CAPTURA] Drone em: ({pos_drone[0]:.3f}, {pos_drone[1]:.3f}, {pos_drone[2]:.3f})")
            print(f"[CAPTURA] Objeto ativo: {self.objeto_ativo}")
            print(f"[CAPTURA] Pos objeto: ({self.pos_objeto[0]:.3f}, {self.pos_objeto[1]:.3f}, {self.pos_objeto[2]:.3f})")

            # 1. Sem objeto ativo
            if self.objeto_ativo is None or self.pos_objeto[2] == -1:
                self.vidas -= 1
                if self.vidas <= 0:
                    self.game_over = True
                print(f"[CAPTURA] FALHOU - Sem objeto ativo. Vidas: {self.vidas}")
                return f"ERRO SEM_OBJETO VIDAS={self.vidas}", None

            # 2. Objeto errado
            if nome_clicado != self.objeto_ativo:
                self.vidas -= 1
                if self.vidas <= 0:
                    self.game_over = True
                print(f"[CAPTURA] FALHOU - Objeto errado. Vidas: {self.vidas}")
                return f"ERRO OBJETO_ERRADO VIDAS={self.vidas}", None

            # 3. Distância
            dx = pos_drone[0] - self.pos_objeto[0]
            dy = pos_drone[1] - self.pos_objeto[1]
            dist = (dx**2 + dy**2)**0.5

            if dist > CAPTURE_TOLERANCE:
                self.vidas -= 1
                if self.vidas <= 0:
                    self.game_over = True
                print(f"[CAPTURA] FALHOU - Longe {dist:.3f}. Vidas: {self.vidas}")
                return f"ERRO LONGE DIST={dist:.3f} VIDAS={self.vidas}", None

            # Sucesso
            self.score += 1
            self.capturado = True
            handle = self.objeto_handle

            self.objeto_ativo = None
            self.objeto_handle = None
            self.pos_objeto = [0, 0, -1]

            print(f"[CAPTURA] SUCESSO! Score: {self.score}")
            return f"OK CAPTURADO SCORE={self.score} VIDAS={self.vidas}", handle

    def perder_vida_timeout(self):
        with self.lock:
            self.vidas -= 1
            if self.vidas <= 0:
                self.game_over = True

            self.objeto_ativo = None
            self.objeto_handle = None
            self.pos_objeto = [0, 0, -1]
            self.capturado = False
            print(f"[TIMEOUT] Perdeu vida. Vidas: {self.vidas}")
            return self.vidas

    def obter_status(self):
        with self.lock:
            return {
                "objeto": self.objeto_ativo or "NONE",
                "pos_x": self.pos_objeto[0],
                "pos_y": self.pos_objeto[1],
                "score": self.score,
                "vidas": self.vidas,
                "game_over": self.game_over
            }

    def verificar_game_over(self):
        with self.lock:
            return self.game_over


############################
# Thread TCP Server
############################
def thread_tcp(estado, stop_event, sim):
    try:
        servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind((TCP_HOST, TCP_PORT))
        servidor.listen(1)
        servidor.settimeout(1.0)

        print(f"[GAME-TCP] Servidor em {TCP_HOST}:{TCP_PORT}")

        conn = None

        while not stop_event.is_set():
            if estado.verificar_game_over():
                print("[GAME-TCP] GAME OVER → fechando conexão com supervisório")
                if conn:
                    try:
                        conn.close()
                    except:
                        pass
                servidor.close()
                return

            if conn is None:
                try:
                    conn, addr = servidor.accept()
                    print(f"[GAME-TCP] Cliente conectado: {addr}")
                    conn.sendall(b"GAME PRONTO\n")
                except socket.timeout:
                    continue

            try:
                conn.settimeout(0.5)
                data = conn.recv(1024)

                if not data:
                    conn.close()
                    conn = None
                    continue

                comando = data.decode().strip()
                partes = comando.split()

                if partes[0].upper() == "CAPTURAR" and len(partes) == 5:
                    nome = partes[1].lower()
                    pos_drone = [float(partes[2]), float(partes[3]), float(partes[4])]
                    resultado, obj_handle = estado.tentar_captura(nome, pos_drone)

                    # esconder se capturado
                    if obj_handle is not None:
                        sim.setObjectPosition(obj_handle, -1, HIDDEN_POS)

                    conn.sendall(f"{resultado}\n".encode())

                elif partes[0].upper() == "STATUS":
                    st = estado.obter_status()
                    resposta = (
                        f"OBJETO={st['objeto']} POS={st['pos_x']:.3f},{st['pos_y']:.3f} "
                        f"SCORE={st['score']} VIDAS={st['vidas']}\n"
                    )
                    conn.sendall(resposta.encode())

                elif partes[0].upper() == "QUIT":
                    conn.sendall(b"TCHAU\n")
                    conn.close()
                    conn = None

                else:
                    conn.sendall(b"ERRO: comando desconhecido\n")

            except socket.timeout:
                continue
            except Exception:
                if conn:
                    conn.close()
                    conn = None

        if conn:
            conn.close()
        servidor.close()

    except Exception as e:
        print(f"[GAME-TCP] ERRO FATAL: {e}")


############################
# Main
############################
def main():
    client = RemoteAPIClient()
    sim = client.getObject('sim')

    if sim.getSimulationState() != sim.simulation_stopped:
        sim.stopSimulation()
        while sim.getSimulationState() != sim.simulation_stopped:
            time.sleep(0.1)
    sim.startSimulation()
    time.sleep(0.5)

    # Carregar bandejas
    trays = []
    for i in range(TRAY_COUNT):
        try:
            tray = sim.getObject(f"/genericTray[{i}]")
            trays.append(tray)
        except:
            pass

    armando = sim.getObject("/Armando")
    mozelli = sim.getObject("/Mozelli")
    objects = {"armando": armando, "mozelli": mozelli}

    for obj in objects.values():
        sim.setObjectPosition(obj, -1, HIDDEN_POS)

    estado = EstadoJogo()
    stop_event = threading.Event()

    tcp_thread = threading.Thread(
        target=thread_tcp,
        args=(estado, stop_event, sim),
        daemon=True
    )
    tcp_thread.start()

    game_over_triggered = False

    try:
        while True:

            # ============================
            #      GAME OVER MODE
            # ============================
            if estado.verificar_game_over():

                if not game_over_triggered:
                    print("\n=========== GAME OVER ===========")
                    print("Enviando mensagens para o supervisório...")

                    # SPAM NO LOG
                    for _ in range(50):
                        print("O MOZELLI ESTÁ CONTROLANDO VOCÊ!")
                        print("O ARMANDO ESTÁ TE VENDO!")
                        time.sleep(0.03)

                    print("[GAME] Supervisório desconectado!")
                    game_over_triggered = True

                # Objetos aparecendo atrás do drone
                drone = sim.getObject("/Quadcopter/base")
                drone_pos = sim.getObjectPosition(drone, -1)
                x, y, z = drone_pos

                nome = random.choice(["armando", "mozelli"])
                handle = objects[nome]

                spawn = [x, y, z - 0.2]
                sim.setObjectPosition(handle, -1, spawn)

                print(f"[ASSOMBRAÇÃO] {nome.upper()} apareceu atrás do drone!")
                time.sleep(1)
                continue

            # ============================
            #     MODO NORMAL DO JOGO
            # ============================

            time.sleep(SPAWN_INTERVAL)

            nome = random.choice(list(objects.keys()))
            tray_idx = random.randint(0, len(trays) - 1)

            handle_obj = objects[nome]
            tray_pos = sim.getObjectPosition(trays[tray_idx], -1)

            spawn = [tray_pos[0], tray_pos[1], tray_pos[2] + Z_OFFSET]
            sim.setObjectPosition(handle_obj, -1, spawn)

            estado.spawnar_objeto(nome, handle_obj, spawn)
            time.sleep(DISPLAY_TIME)

            if not estado.foi_capturado():
                vidas = estado.perder_vida_timeout()
                sim.setObjectPosition(handle_obj, -1, HIDDEN_POS)

            estado.remover_objeto()

    except KeyboardInterrupt:
        pass
    finally:
        stop_event.set()
        sim.stopSimulation()
        print("[GAME] Finalizado")


if __name__ == "__main__":
    main()
