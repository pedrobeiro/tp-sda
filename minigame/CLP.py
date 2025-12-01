"""
CLP - Cliente OPC UA + Servidor TCP/IP (VERSÃO SIMPLIFICADA)
Duas threads:
1. Thread OPC: lê DroneX,Y,Z e escreve TargetX,Y,Z
2. Thread TCP: aceita 1 cliente (Supervisório) e troca dados
"""

import time
import socket
import threading
from datetime import datetime
from opcua import Client

OPCUA_URL = "opc.tcp://localhost:53530/OPCUA/SimulationServer"
TCP_HOST = "0.0.0.0"
TCP_PORT = 5000

# variáveis compartilhadas entre as threads (considerando que em um CLP a memória é compartilhada)
class DadosCompartilhados:
    """Dados compartilhados entre Thread OPC e Thread TCP"""
    def __init__(self):
        self.lock = threading.Lock()
        
        # Posição atual do drone (atualizada pela Thread OPC)
        self.drone_x = 0.0
        self.drone_y = 0.0
        self.drone_z = 0.0
        
        # Posição alvo (recebida pela Thread TCP, enviada pela Thread OPC)
        self.target_x = 0.0
        self.target_y = 0.0
        self.target_z = 1.5
        
        # Flag: indica se Thread TCP recebeu novo comando
        self.novo_comando = False
    
    def atualizar_drone(self, x, y, z):
        """Thread OPC chama isso após ler do Prosys"""
        with self.lock:
            self.drone_x = x
            self.drone_y = y
            self.drone_z = z
    
    def obter_drone(self):
        """Thread TCP chama isso para enviar ao Supervisório"""
        with self.lock:
            return (self.drone_x, self.drone_y, self.drone_z)
    
    def definir_target(self, x, y, z):
        """Thread TCP chama isso quando recebe comando do Supervisório"""
        with self.lock:
            self.target_x = x
            self.target_y = y
            self.target_z = z
            self.novo_comando = True
    
    def obter_target(self):
        """Thread OPC chama isso para enviar ao Prosys"""
        with self.lock:
            target = (self.target_x, self.target_y, self.target_z)
            tem_novo = self.novo_comando
            self.novo_comando = False
            return target, tem_novo

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
        """Conecta ao servidor OPC UA e mapeia as variáveis"""
        print(f"[CLP-OPC] Conectando ao servidor: {self.url}")
        
        self.client = Client(self.url)
        self.client.connect()
        print("[CLP-OPC] Conectado!")
        
        root = self.client.get_objects_node()
        
        # Achar pasta Drone
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
        
        # Mapear variáveis
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

        # Escrever valores iniciais (senao o drone pega o último target salvo)
        print("[CLP-OPC] Inicializando targets com posição segura (0, 0, 1.5)...")
        self.enviar_target(0.0, 0.0, 1.5)
        print("[CLP-OPC] Targets inicializados!")
    
    def ler_posicao_drone(self):
        """Lê posição atual do drone do Prosys"""
        x = float(self.drone_x_node.get_value())
        y = float(self.drone_y_node.get_value())
        z = float(self.drone_z_node.get_value())
        return (x, y, z)
    
    def enviar_target(self, x, y, z):
        """Envia target ao Prosys"""
        self.target_x_node.set_value(float(x))
        self.target_y_node.set_value(float(y))
        self.target_z_node.set_value(float(z))
    
    def disconnect(self):
        if self.client:
            self.client.disconnect()

# THREAD 1: Cliente OPC
def thread_opc(dados, stop_event):
    """
    Thread que gerencia comunicação OPC UA
    - Lê DroneX,Y,Z do Prosys (10 Hz)
    - Escreve TargetX,Y,Z no Prosys quando há novo comando
    """
    clp = CLP()
    
    try:
        clp.connect()
        print("[CLP-OPC] Thread iniciada\n")
        
        while not stop_event.is_set():
            # 1. Ler posição do drone do Prosys
            pos = clp.ler_posicao_drone()
            dados.atualizar_drone(pos[0], pos[1], pos[2])
            
            # 2. Verificar se há novo target (vindo do TCP)
            target, tem_novo = dados.obter_target()
            if tem_novo:
                clp.enviar_target(target[0], target[1], target[2])
                print(f"[CLP-OPC] Target enviado: ({target[0]:.2f}, {target[1]:.2f}, {target[2]:.2f})")
            
            time.sleep(0.1)  # 10 Hz
    
    except Exception as e:
        print(f"[CLP-OPC] ERRO: {e}")
    finally:
        clp.disconnect()
        print("[CLP-OPC] Thread encerrada")

# THREAD 2: Servidor TCP
def thread_tcp(dados, stop_event):
    """
    Thread que gerencia servidor TCP/IP
    - Aceita 1 cliente (Supervisório)
    - Recebe comandos TARGET
    - Envia telemetria STATUS
    """
    try:
        # Criar servidor TCP
        servidor = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
        servidor.setsockopt(socket.SOL_SOCKET, socket.SO_REUSEADDR, 1)
        servidor.bind((TCP_HOST, TCP_PORT))
        servidor.listen(1)  # Aceita apenas 1 cliente
        servidor.settimeout(1.0)
        
        print(f"[CLP-TCP] Servidor escutando em {TCP_HOST}:{TCP_PORT}")
        print(f"[CLP-TCP] Aguardando Supervisório conectar...\n")
        
        conn = None
        
        while not stop_event.is_set():
            # Aceitar conexão do Supervisório
            if conn is None:
                try:
                    conn, addr = servidor.accept()
                    print(f"[CLP-TCP] Supervisório conectado: {addr}")
                    conn.sendall(b"CLP PRONTO\n")
                except socket.timeout:
                    continue
            
            # Processar comandos do Supervisório
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
                    # Supervisório enviou: TARGET x y z
                    x = float(partes[1])
                    y = float(partes[2])
                    z = float(partes[3])
                    
                    dados.definir_target(x, y, z)
                    resposta = f"OK TARGET {x:.2f} {y:.2f} {z:.2f}\n"
                    conn.sendall(resposta.encode('utf-8'))
                
                elif partes[0].upper() == "STATUS":
                    # Supervisório pediu: STATUS
                    drone_pos = dados.obter_drone()
                    target_pos, _ = dados.obter_target()
                    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
                    
                    resposta = (
                        f"DRONE {drone_pos[0]:.3f} {drone_pos[1]:.3f} {drone_pos[2]:.3f} "
                        f"TARGET {target_pos[0]:.3f} {target_pos[1]:.3f} {target_pos[2]:.3f} "
                        f"TIME {timestamp}\n"
                    )
                    conn.sendall(resposta.encode('utf-8'))
                
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

############################
# MAIN
############################
def main():
    print("="*60)
    print("CLP - Sistema Simplificado (OPC + TCP)")
    print("="*60)
    print()
    
    # Dados compartilhados entre as 2 threads
    dados = DadosCompartilhados()
    stop_event = threading.Event()
    
    # Criar e iniciar as 2 threads
    t_opc = threading.Thread(target=thread_opc, args=(dados, stop_event), daemon=True)
    t_tcp = threading.Thread(target=thread_tcp, args=(dados, stop_event), daemon=True)
    
    t_opc.start()
    time.sleep(2)  # Aguardar OPC conectar
    t_tcp.start()
    
    print("="*60)
    print("SISTEMA RODANDO!")
    print("Pressione Ctrl+C para encerrar")
    print("="*60)
    print()
    
    try:
        # Manter programa rodando
        while True:
            time.sleep(1)
    
    except KeyboardInterrupt:
        print("\n\n[MAIN] Encerrando sistema...")
        stop_event.set()
        time.sleep(2)
        print("[MAIN] Sistema encerrado!")

if __name__ == "__main__":
    main()