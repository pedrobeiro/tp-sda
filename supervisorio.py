import tkinter as tk
from tkinter import ttk, scrolledtext
import socket
import threading
import time
from datetime import datetime

CLP_HOST = "localhost"
CLP_PORT = 5000

class Supervisorio:
    def __init__(self, root):
        self.root = root
        self.root.title("Supervisório - Controle de Drone")
        self.root.geometry("900x700")
        self.root.resizable(False, False)
        
        # Conexão TCP
        self.socket = None
        self.conectado = False
        self.thread_leitura = None
        self.rodando = True
        
        # Dados do drone
        self.drone_x = 0.0
        self.drone_y = 0.0
        self.drone_z = 0.0
        self.target_x = 0.0
        self.target_y = 0.0
        self.target_z = 1.5
        self.ultimo_timestamp = "---"
        
        # Pontos de inspeção (4 bandejas)
        self.pontos_inspecao = [
            ("Bandeja 1 (1, 1)", 1.0, 1.0, 1.5),
            ("Bandeja 2 (-1, -1)", -1.0, -1.0, 1.5),
            ("Bandeja 3 (2, -2)", 2.0, -2.0, 1.5),
            ("Bandeja 4 (-2, 2)", -2.0, 2.0, 1.5)
        ]
        
        # Criar interface
        self.criar_interface()
        
        # Tentar conectar automaticamente
        self.root.after(500, self.conectar)
    
    def criar_interface(self):
        """Cria a interface gráfica"""
        
        # Status
        frame_status = tk.LabelFrame(self.root, text="Status da Conexão", padx=10, pady=10)
        frame_status.pack(fill="x", padx=10, pady=5)
        
        self.label_status = tk.Label(frame_status, text="● DESCONECTADO", 
                                      fg="red", font=("Arial", 12, "bold"))
        self.label_status.pack(side="left")
        
        self.btn_conectar = tk.Button(frame_status, text="Conectar", 
                                       command=self.conectar, bg="lightgreen")
        self.btn_conectar.pack(side="right", padx=5)
        
        self.btn_desconectar = tk.Button(frame_status, text="Desconectar", 
                                          command=self.desconectar, state="disabled")
        self.btn_desconectar.pack(side="right")
        
        # Posiçao
        frame_esquerdo = tk.Frame(self.root)
        frame_esquerdo.pack(side="left", fill="both", expand=True, padx=10, pady=5)
        
        frame_posicao = tk.LabelFrame(frame_esquerdo, text="Posição Atual do Drone", 
                                       padx=10, pady=10)
        frame_posicao.pack(fill="x", pady=5)
        
        # Labels de posição
        tk.Label(frame_posicao, text="X:", font=("Arial", 12)).grid(row=0, column=0, sticky="e", padx=5, pady=5)
        self.label_drone_x = tk.Label(frame_posicao, text="0.000 m", 
                                       font=("Arial", 14, "bold"), fg="blue")
        self.label_drone_x.grid(row=0, column=1, sticky="w", padx=5, pady=5)
        
        tk.Label(frame_posicao, text="Y:", font=("Arial", 12)).grid(row=1, column=0, sticky="e", padx=5, pady=5)
        self.label_drone_y = tk.Label(frame_posicao, text="0.000 m", 
                                       font=("Arial", 14, "bold"), fg="blue")
        self.label_drone_y.grid(row=1, column=1, sticky="w", padx=5, pady=5)
        
        tk.Label(frame_posicao, text="Z:", font=("Arial", 12)).grid(row=2, column=0, sticky="e", padx=5, pady=5)
        self.label_drone_z = tk.Label(frame_posicao, text="0.000 m", 
                                       font=("Arial", 14, "bold"), fg="blue")
        self.label_drone_z.grid(row=2, column=1, sticky="w", padx=5, pady=5)
        
        # TIMESTAMP
        tk.Label(frame_posicao, text="Timestamp:", font=("Arial", 10)).grid(row=3, column=0, sticky="e", padx=5, pady=5)
        self.label_timestamp = tk.Label(frame_posicao, text="---", 
                                         font=("Arial", 10), fg="gray")
        self.label_timestamp.grid(row=3, column=1, sticky="w", padx=5, pady=5)
        
        # Target
        frame_target = tk.LabelFrame(frame_esquerdo, text="Posição Alvo (Target)", 
                                      padx=10, pady=10)
        frame_target.pack(fill="x", pady=5)
        
        tk.Label(frame_target, text="X:", font=("Arial", 10)).grid(row=0, column=0, sticky="e", padx=5, pady=3)
        self.label_target_x = tk.Label(frame_target, text="0.000 m", 
                                        font=("Arial", 12), fg="green")
        self.label_target_x.grid(row=0, column=1, sticky="w", padx=5, pady=3)
        
        tk.Label(frame_target, text="Y:", font=("Arial", 10)).grid(row=1, column=0, sticky="e", padx=5, pady=3)
        self.label_target_y = tk.Label(frame_target, text="0.000 m", 
                                        font=("Arial", 12), fg="green")
        self.label_target_y.grid(row=1, column=1, sticky="w", padx=5, pady=3)
        
        tk.Label(frame_target, text="Z:", font=("Arial", 10)).grid(row=2, column=0, sticky="e", padx=5, pady=3)
        self.label_target_z = tk.Label(frame_target, text="1.500 m", 
                                        font=("Arial", 12), fg="green")
        self.label_target_z.grid(row=2, column=1, sticky="w", padx=5, pady=3)
        
        # Comandos
        frame_direito = tk.Frame(self.root)
        frame_direito.pack(side="right", fill="both", expand=True, padx=10, pady=5)
        
        frame_comandos = tk.LabelFrame(frame_direito, text="Pontos de Inspeção", 
                                        padx=10, pady=10)
        frame_comandos.pack(fill="x", pady=5)
        
        tk.Label(frame_comandos, text="Escolha a bandeja para inspecionar:", 
                 font=("Arial", 10)).pack(pady=5)
        
        # Botões para cada bandeja
        for i, (nome, x, y, z) in enumerate(self.pontos_inspecao):
            btn = tk.Button(frame_comandos, text=nome, 
                           command=lambda x=x, y=y, z=z: self.enviar_target(x, y, z),
                           width=25, height=2, bg="lightblue", font=("Arial", 10))
            btn.pack(pady=5)
        
        # Botão voltar origem
        btn_origem = tk.Button(frame_comandos, text="⌂ Voltar à Origem (0, 0)", 
                               command=lambda: self.enviar_target(0, 0, 1.5),
                               width=25, height=2, bg="lightyellow", font=("Arial", 10, "bold"))
        btn_origem.pack(pady=10)
        
        # Log
        frame_log = tk.LabelFrame(self.root, text="Histórico de Operações (salvo em historiador.txt)", 
                                   padx=10, pady=10)
        frame_log.pack(fill="both", expand=True, padx=10, pady=5)
        
        self.text_log = scrolledtext.ScrolledText(frame_log, height=12, 
                                                   font=("Courier", 9))
        self.text_log.pack(fill="both", expand=True)
        
        # Botão para limpar log
        btn_limpar = tk.Button(frame_log, text="Limpar Log Visual", command=self.limpar_log)
        btn_limpar.pack(pady=5)
    
    def log(self, mensagem):
        """Adiciona mensagem ao log visual e ao arquivo"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]  # Com milissegundos
        linha = f"[{timestamp}] {mensagem}"
        
        # Log visual
        self.text_log.insert(tk.END, linha + "\n")
        self.text_log.see(tk.END)
        
        # Log em arquivo
        try:
            with open("historiador.txt", "a", encoding="utf-8") as f:
                f.write(linha + "\n")
        except Exception as e:
            print(f"Erro ao salvar em historiador.txt: {e}")
    
    def log_posicao_drone(self):
        """Salva posição do drone com timestamp no historiador"""
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        linha = (f"[{timestamp}] POSIÇÃO DRONE: "
                f"X={self.drone_x:.3f}m, Y={self.drone_y:.3f}m, Z={self.drone_z:.3f}m")
        
        try:
            with open("historiador.txt", "a", encoding="utf-8") as f:
                f.write(linha + "\n")
        except Exception as e:
            print(f"Erro ao salvar em historiador.txt: {e}")
    
    def limpar_log(self):
        """Limpa o log visual"""
        self.text_log.delete(1.0, tk.END)
    
    def conectar(self):
        """Conecta ao CLP via TCP/IP"""
        if self.conectado:
            self.log("Já está conectado!")
            return
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((CLP_HOST, CLP_PORT))
            
            # Receber mensagem de boas-vindas
            boas_vindas = self.socket.recv(1024).decode().strip()
            
            self.conectado = True
            self.label_status.config(text="● CONECTADO", fg="green")
            self.btn_conectar.config(state="disabled")
            self.btn_desconectar.config(state="normal")
            
            self.log(f" Conectado ao CLP em {CLP_HOST}:{CLP_PORT}")
            self.log(f"Resposta do CLP: {boas_vindas}")
            
            # Iniciar thread de leitura contínua
            self.rodando = True
            self.thread_leitura = threading.Thread(target=self.thread_ler_status, daemon=True)
            self.thread_leitura.start()
            
        except Exception as e:
            self.log(f"Erro ao conectar: {e}")
            self.conectado = False
    
    def desconectar(self):
        """Desconecta do CLP"""
        if not self.conectado:
            return
        
        try:
            self.rodando = False
            
            if self.socket:
                try:
                    self.socket.send(b"QUIT\n")
                    time.sleep(0.2)
                except:
                    pass
                
                try:
                    self.socket.shutdown(socket.SHUT_RDWR)
                except:
                    pass
                
                self.socket.close()
                self.socket = None
            
            # Aguardar thread encerrar
            if self.thread_leitura and self.thread_leitura.is_alive():
                self.thread_leitura.join(timeout=2.0)
            
            self.conectado = False
            self.label_status.config(text="● DESCONECTADO", fg="red")
            self.btn_conectar.config(state="normal")
            self.btn_desconectar.config(state="disabled")
            
            self.log("Desconectado do CLP")
            
        except Exception as e:
            self.log(f"Erro ao desconectar: {e}")
    
    def enviar_target(self, x, y, z):
        """Envia comando TARGET ao CLP"""
        if not self.conectado:
            self.log("Não conectado")
            return
        
        try:
            comando = f"TARGET {x} {y} {z}\n"
            self.socket.send(comando.encode())
            
            # Receber resposta
            resposta = self.socket.recv(1024).decode().strip()
            
            # Log detalhado com timestamp
            self.log(f"COMANDO ENVIADO: TARGET X={x:.1f}m, Y={y:.1f}m, Z={z:.1f}m")
            self.log(f"Resposta do CLP: {resposta}")
            
            # Atualizar target visual
            self.target_x = x
            self.target_y = y
            self.target_z = z
            self.atualizar_display_target()
            
        except Exception as e:
            self.log(f"Erro ao enviar comando: {e}")
            self.conectado = False
            self.desconectar()
    
    def thread_ler_status(self):
        """Thread que lê STATUS continuamente do CLP"""
        contador = 0
        
        # Configurar timeout no socket
        if self.socket:
            self.socket.settimeout(1.0)
        
        while self.rodando and self.conectado:
            try:
                # Pedir STATUS
                self.socket.send(b"STATUS\n")
                
                # Receber resposta
                resposta = self.socket.recv(1024).decode().strip()
                
                # Parse: "DRONE x y z TARGET x y z TIME timestamp"
                partes = resposta.split()
                if len(partes) >= 10 and partes[0] == "DRONE":
                    self.drone_x = float(partes[1])
                    self.drone_y = float(partes[2])
                    self.drone_z = float(partes[3])
                    
                    if partes[4] == "TARGET":
                        self.target_x = float(partes[5])
                        self.target_y = float(partes[6])
                        self.target_z = float(partes[7])
                    
                    # Extrair timestamp
                    if partes[8] == "TIME":
                        self.ultimo_timestamp = f"{partes[9]} {partes[10]}"
                    
                    # Atualizar display
                    self.root.after(0, self.atualizar_display_drone)
                    self.root.after(0, self.atualizar_display_target)
                    self.root.after(0, self.atualizar_timestamp)
                    
                    # Salvar posição no historiador a cada 5 leituras (2.5s)
                    contador += 1
                    if contador >= 5:
                        self.log_posicao_drone()
                        contador = 0
                
                time.sleep(0.5)
                
            except socket.timeout:
                # Timeout é normal, continua o loop
                continue
            except Exception as e:
                if self.rodando:
                    print(f"[Thread Leitura] Erro: {e}")
                break
        
        print("[Thread Leitura] Encerrada")
    
    def atualizar_display_drone(self):
        """Atualiza labels de posição do drone"""
        self.label_drone_x.config(text=f"{self.drone_x:.3f} m")
        self.label_drone_y.config(text=f"{self.drone_y:.3f} m")
        self.label_drone_z.config(text=f"{self.drone_z:.3f} m")
    
    def atualizar_display_target(self):
        """Atualiza labels de target"""
        self.label_target_x.config(text=f"{self.target_x:.3f} m")
        self.label_target_y.config(text=f"{self.target_y:.3f} m")
        self.label_target_z.config(text=f"{self.target_z:.3f} m")
    
    def atualizar_timestamp(self):
        """Atualiza label de timestamp"""
        self.label_timestamp.config(text=self.ultimo_timestamp)
    

    def fechar(self):
        """Fecha o supervisório"""
        print("[Supervisório] Fechando...")
        self.rodando = False
        self.desconectar()
        
        # Aguardar um pouco antes de destruir
        time.sleep(0.3)
        
        try:
            self.root.quit()
            self.root.destroy()
        except:
            pass

def main():
    root = tk.Tk()
    app = Supervisorio(root)
    
    # Protocolo de fechamento
    root.protocol("WM_DELETE_WINDOW", app.fechar)
    
    root.mainloop()

if __name__ == "__main__":
    main()