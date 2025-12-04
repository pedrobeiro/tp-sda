"""
CLP - Cliente OPC UA + Servidor TCP/IP (VERSÃO COM GAME)
"""

import time
import socket
import threading
from datetime import datetime
from opcua import Client

OPCUA_URL = "opc.tcp://localhost:53530/OPCUA/SimulationServer"
TCP_HOST = "0.0.0.0"
TCP_PORT = 5000
GAME_HOST = "localhost"
GAME_PORT = 5001

class DadosCompartilhados:
    def __init__(self):
        self.lock = threading.Lock()
        
        # Drone
        self.drone_x = 0.0
        self.drone_y = 0.0
        self.drone_z = 0.0
        
        # Target
        self.target_x = 0.0
        self.target_y = 0.0
        self.target_z = 1.5
        self.novo_comando = False
        
        # Game
        self.game_objeto = "NONE"
        self.game_pos_x = 0.0
        self.game_pos_y = 0.0
        self.game_score = 0
        self.game_vidas = 3
        
        # Socket do game (compartilhado)
        self.game_socket = None
        self.game_socket_lock = threading.Lock()
    
    def atualizar_drone(self, x, y, z):
        with self.lock:
            self.drone_x = x
            self.drone_y = y
            self.drone_z = z
    
    def obter_drone(self):
        with self.lock:
            return (self.drone_x, self.drone_y, self.drone_z)
    
    def definir_target(self, x, y, z):
        with self.lock:
            self.target_x = x
            self.target_y = y
            self.target_z = z
            self.novo_comando = True
    
    def obter_target(self):
        with self.lock:
            target = (self.target_x, self.target_y, self.target_z)
            tem_novo = self.novo_comando
            self.novo_comando = False
            return target, tem_novo
    
    def atualizar_game(self, objeto, pos_x, pos_y, score, vidas):
        with self.lock:
            self.game_objeto = objeto
            self.game_pos_x = pos_x
            self.game_pos_y = pos_y
            self.game_score = score
            self.game_vidas = vidas
    
    def obter_game(self):
        with self.lock:
            return {
                "objeto": self.game_objeto,
                "pos_x": self.game_pos_x,
                "pos_y": self.game_pos_y,
                "score": self.game_score,
                "vidas": self.game_vidas
            }
    
    def conectar_game_socket(self):
        """Conecta ao servidor do game e mantém conexão"""
        with self.game_socket_lock:
            if self.game_socket is None:
                try:
                    self.game_socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
                    self.game_socket.connect((GAME_HOST, GAME_PORT))
                    self.game_socket.settimeout(2.0)
                    boas = self.game_socket.recv(1024).decode().strip()
                    print(f"[GAME-CONN] {boas}")
                    return True
                except Exception as e:
                    print(f"[GAME-CONN] Erro ao conectar: {e}")
                    self.game_socket = None
                    return False
            return True
    
    def enviar_comando_game(self, comando):
        """Envia comando ao game e retorna resposta"""
        with self.game_socket_lock:
            if self.game_socket is None:
                return "ERRO: não conectado ao game"
            
            try:
                self.game_socket.send(f"{comando}\n".encode())
                resposta = self.game_socket.recv(1024).decode().strip()
                return resposta
            except Exception as e:
                print(f"[GAME-CONN] Erro ao enviar comando: {e}")
                # Fechar socket com erro
                try:
                    self.game_socket.close()
                except:
                    pass
                self.game_socket = None
                return f"ERRO: {e}"

class CLP:
    def __init__(self, url=OPCUA_URL):
        self.url = url
        self.client = None
        self.target_x_node = None
        self.target_y_node = None
        self.target_z_node = None
        self.drone_x_node = None
        self.drone_y_node = None
        self.drone_z_node = None
    
    def connect(self):
        print(f"[CLP-OPC] Conectando ao servidor: {self.url}")
        
        self.client = Client(self.url)
        self.client.connect()
        print("[CLP-OPC] Conectado!")
        
        root = self.client.get_objects_node()
        
        drone_folder = None
        try:
            drone_folder = root.get_child(["3:Drone"])
        except:
            for node in root.get_children():
                try:
                    name = node.get_browse_name().Name
                    if name.lower() == "drone":
                        drone_folder = node
                        break
                except:
                    pass
        
        if drone_folder is None:
            raise RuntimeError("Pasta 'Drone' não encontrada")
        
        name_to_node = {}
        for var in drone_folder.get_children():
            try:
                var_name = var.get_browse_name().Name
                name_to_node[var_name.lower()] = var
            except:
                pass
        
        self.target_x_node = name_to_node.get("targetx")
        self.target_y_node = name_to_node.get("targety")
        self.target_z_node = name_to_node.get("targetz")
        self.drone_x_node = name_to_node.get("dronex")
        self.drone_y_node = name_to_node.get("droney")
        self.drone_z_node = name_to_node.get("dronez")
        
        if not all([self.target_x_node, self.target_y_node, self.target_z_node,
                    self.drone_x_node, self.drone_y_node, self.drone_z_node]):
            raise RuntimeError("Variáveis não encontradas")
        
        print("[CLP-OPC] Variáveis mapeadas!")
        print("[CLP-OPC] Inicializando targets (0, 0, 1.5)...")
        self.enviar_target(0.0, 0.0, 1.5)
        print("[CLP-OPC] Targets inicializados!")
    
    def ler_posicao_drone(self):
        x = float(self.drone_x_node.get_value())
        y = float(self.drone_y_node.get_value())
        z = float(self.drone_z_node.get_value())
        return (x, y, z)
    
    def enviar_target(self, x, y, z):
        self.target_x_node.set_value(float(x))
        self.target_y_node.set_value(float(y))
        self.target_z_node.set_value(float(z))
    
    def disconnect(self):
        if self.client:
            self.client.disconnect()

def thread_opc(dados, stop_event):
    clp = CLP()
    
    try:
        clp.connect()
        print("[CLP-OPC] Thread iniciada\n")
        
        while not stop_event.is_set():
            pos = clp.ler_posicao_drone()
            dados.atualizar_drone(pos[0], pos[1], pos[2])
            
            target, tem_novo = dados.obter_target()
            if tem_novo:
                clp.enviar_target(target[0], target[1], target[2])
                print(f"[CLP-OPC] Target enviado: ({target[0]:.2f}, {target[1]:.2f}, {target[2]:.2f})")
            
            time.sleep(0.1)
    
    except Exception as e:
        print(f"[CLP-OPC] ERRO: {e}")
    finally:
        clp.disconnect()
        print("[CLP-OPC] Thread encerrada")

def thread_game_client(dados, stop_event):
    """Thread que mantém conexão com o servidor do game"""
    print("[CLP-GAME] Iniciando cliente do jogo...")
    time.sleep(2)  # Aguardar game.py iniciar
    
    while not stop_event.is_set():
        # Tentar conectar se não estiver conectado
        if not dados.conectar_game_socket():
            time.sleep(2)
            continue
        
        try:
            # Pedir status do jogo
            resposta = dados.enviar_comando_game("STATUS")
            
            if resposta.startswith("ERRO"):
                time.sleep(1)
                continue
            
            # Parse: OBJETO=armando POS=2.0,0.0 SCORE=5 VIDAS=3
            partes = resposta.split()
            info = {}
            for p in partes:
                if '=' in p:
                    k, v = p.split('=', 1)
                    info[k] = v
            
            objeto = info.get('OBJETO', 'NONE')
            pos = info.get('POS', '0.0,0.0').split(',')
            pos_x = float(pos[0])
            pos_y = float(pos[1])
            score = int(info.get('SCORE', 0))
            vidas = int(info.get('VIDAS', 3))
            
            dados.atualizar_game(objeto, pos_x, pos_y, score, vidas)
            
            time.sleep(0.5)
        
        except Exception as e:
            print(f"[CLP-GAME] Erro: {e}")
            time.sleep(2)
    
    print("[CLP-GAME] Thread encerrada")

def thread_tcp(dados, stop_event):
    try:
        servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind((TCP_HOST, TCP_PORT))
        servidor.listen(1)
        servidor.settimeout(1.0)
        
        print(f"[CLP-TCP] Servidor em {TCP_HOST}:{TCP_PORT}")
        print(f"[CLP-TCP] Aguardando Supervisório...\n")
        
        conn = None
        
        while not stop_event.is_set():
            if conn is None:
                try:
                    conn, addr = servidor.accept()
                    print(f"[CLP-TCP] Supervisório conectado: {addr}")
                    conn.sendall(b"CLP PRONTO\n")
                except socket.timeout:
                    continue
            
            try:
                conn.settimeout(0.5)
                data = conn.recv(1024)
                
                if not data:
                    print("[CLP-TCP] Supervisório desconectou")
                    conn.close()
                    conn = None
                    continue
                
                comando = data.decode('utf-8').strip()
                print(f"[CLP-TCP] Comando: {comando}")
                
                partes = comando.split()
                
                if partes[0].upper() == "TARGET" and len(partes) == 4:
                    x = float(partes[1])
                    y = float(partes[2])
                    z = float(partes[3])
                    
                    dados.definir_target(x, y, z)
                    resposta = f"OK TARGET {x:.2f} {y:.2f} {z:.2f}\n"
                    conn.sendall(resposta.encode('utf-8'))
                
                elif partes[0].upper() == "STATUS":
                    drone_pos = dados.obter_drone()
                    target_pos, _ = dados.obter_target()
                    game_info = dados.obter_game()
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    resposta = (
                        f"DRONE {drone_pos[0]:.3f} {drone_pos[1]:.3f} {drone_pos[2]:.3f} "
                        f"TARGET {target_pos[0]:.3f} {target_pos[1]:.3f} {target_pos[2]:.3f} "
                        f"TIME {timestamp} "
                        f"GAME_OBJ={game_info['objeto']} "
                        f"GAME_POS={game_info['pos_x']:.3f},{game_info['pos_y']:.3f} "
                        f"SCORE={game_info['score']} "
                        f"VIDAS={game_info['vidas']}\n"
                    )
                    conn.sendall(resposta.encode('utf-8'))
                
                elif partes[0].upper() == "CAPTURAR" and len(partes) == 2:
                    # Encaminhar para o servidor do game COM a posição do drone
                    nome_obj = partes[1].lower()
                    
                    # Garantir que está conectado
                    if not dados.conectar_game_socket():
                        conn.sendall(b"ERRO: game server indisponivel\n")
                        continue
                    
                    # Obter posição atual do drone
                    pos_drone = dados.obter_drone()
                    
                    # Enviar comando com posição do drone
                    cmd = f"CAPTURAR {nome_obj} {pos_drone[0]:.3f} {pos_drone[1]:.3f} {pos_drone[2]:.3f}"
                    print(f"[CLP-TCP] Enviando ao game: {cmd}")
                    resultado = dados.enviar_comando_game(cmd)
                    conn.sendall(f"{resultado}\n".encode('utf-8'))
                
                elif partes[0].upper() == "QUIT":
                    conn.sendall(b"TCHAU\n")
                    conn.close()
                    conn = None
                
                else:
                    conn.sendall(b"ERRO: comando desconhecido\n")
            
            except socket.timeout:
                continue
            except Exception as e:
                print(f"[CLP-TCP] Erro: {e}")
                if conn:
                    conn.close()
                    conn = None
        
        if conn:
            conn.close()
        servidor.close()
        print("[CLP-TCP] Thread encerrada")
    
    except Exception as e:
        print(f"[CLP-TCP] ERRO FATAL: {e}")

def main():
    print("="*60)
    print("CLP - Sistema com Game")
    print("="*60)
    print()
    
    dados = DadosCompartilhados()
    stop_event = threading.Event()
    
    t_opc = threading.Thread(target=thread_opc, args=(dados, stop_event), daemon=True)
    t_game = threading.Thread(target=thread_game_client, args=(dados, stop_event), daemon=True)
    t_tcp = threading.Thread(target=thread_tcp, args=(dados, stop_event), daemon=True)
    
    t_opc.start()
    time.sleep(2)
    t_game.start()
    t_tcp.start()
    
    print("="*60)
    print("SISTEMA RODANDO!")
    print("Pressione Ctrl+C para encerrar")
    print("="*60)
    print()
    
    try:
        while True:
            time.sleep(1)
    except KeyboardInterrupt:
        print("\n\n[MAIN] Encerrando...")
        stop_event.set()
        time.sleep(2)
        print("[MAIN] Encerrado!")

if __name__ == "__main__":
    main()