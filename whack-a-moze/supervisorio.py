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
        self.root.title("Supervisório - Controle de Drone + Game")
        self.root.geometry("900x800")
        self.root.resizable(True, True)
        
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
        
        # Dados do game
        self.game_objeto = "NONE"
        self.game_pos_x = 0.0
        self.game_pos_y = 0.0
        self.game_score = 0
        self.game_vidas = 3
        
        # Pontos de inspeção
        self.pontos_inspecao = [
            ("Bandeja 1 (2.0, 0.0)", 2.0, 0.0, 1.5),
            ("Bandeja 2 (0, -2.0)", 0, -2.0, 1.5),
            ("Bandeja 3 (-2.0, 0.0)", -2.0, 0.0, 1.5),
            ("Bandeja 4 (0.0, 2.0)", 0.0, 2.0, 1.5)
        ]
        
        self.criar_interface()
        self.root.after(500, self.conectar)

    ###########################################################################
    # INTERFACE
    ###########################################################################
    def criar_interface(self):
        # STATUS
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

        # Coluna esquerda
        frame_esq = tk.Frame(self.root)
        frame_esq.pack(side="left", fill="both", expand=True, padx=10, pady=5)

        ###########################################################################
        # POSIÇÃO DO DRONE
        ###########################################################################
        frame_pos = tk.LabelFrame(frame_esq, text="Posição Atual do Drone", padx=10, pady=10)
        frame_pos.pack(fill="x", pady=5)

        tk.Label(frame_pos, text="X:", font=("Arial", 12)).grid(row=0, column=0)
        self.label_drone_x = tk.Label(frame_pos, text="0.000 m", font=("Arial", 14, "bold"), fg="blue")
        self.label_drone_x.grid(row=0, column=1)

        tk.Label(frame_pos, text="Y:", font=("Arial", 12)).grid(row=1, column=0)
        self.label_drone_y = tk.Label(frame_pos, text="0.000 m", font=("Arial", 14, "bold"), fg="blue")
        self.label_drone_y.grid(row=1, column=1)

        tk.Label(frame_pos, text="Z:", font=("Arial", 12)).grid(row=2, column=0)
        self.label_drone_z = tk.Label(frame_pos, text="0.000 m", font=("Arial", 14, "bold"), fg="blue")
        self.label_drone_z.grid(row=2, column=1)

        tk.Label(frame_pos, text="Timestamp:", font=("Arial", 10)).grid(row=3, column=0)
        self.label_timestamp = tk.Label(frame_pos, text="---", font=("Arial", 10), fg="gray")
        self.label_timestamp.grid(row=3, column=1)

        ###########################################################################
        # GAME STATUS
        ###########################################################################
        frame_game = tk.LabelFrame(frame_esq, text="Status do Jogo", padx=10, pady=10)
        frame_game.pack(fill="x", pady=5)

        tk.Label(frame_game, text="Score:", font=("Arial", 12, "bold")).grid(row=0, column=0, sticky="w")
        self.label_score = tk.Label(frame_game, text="0", font=("Arial", 20, "bold"), fg="green")
        self.label_score.grid(row=0, column=1, padx=10)

        tk.Label(frame_game, text="Vidas:", font=("Arial", 12, "bold")).grid(row=1, column=0, sticky="w")
        self.label_vidas = tk.Label(frame_game, text="3", font=("Arial", 20, "bold"), fg="red")
        self.label_vidas.grid(row=1, column=1, padx=10)

        tk.Label(frame_game, text="Objeto Ativo:", font=("Arial", 11)).grid(row=2, column=0, sticky="w")
        self.label_objeto = tk.Label(frame_game, text="NONE", font=("Arial", 14, "bold"), fg="orange")
        self.label_objeto.grid(row=2, column=1, padx=10)

        tk.Label(frame_game, text="Posição Objeto:", font=("Arial", 10)).grid(row=3, column=0, sticky="w")
        self.label_obj_pos = tk.Label(frame_game, text="(0.0, 0.0)", font=("Arial", 10), fg="gray")
        self.label_obj_pos.grid(row=3, column=1, padx=10)

        ###########################################################################
        # BOTÕES DE CAPTURA
        ###########################################################################
        frame_captura = tk.LabelFrame(frame_esq, text="Capturar Objeto", padx=10, pady=10)
        frame_captura.pack(fill="x", pady=5)

        tk.Button(frame_captura, text="🎯 CAPTURAR ARMANDO", 
                  command=lambda: self.capturar("armando"),
                  width=25, height=2, bg="#FFB6C1", font=("Arial", 11, "bold")).pack(pady=5)

        tk.Button(frame_captura, text="🎯 CAPTURAR MOZELLI", 
                  command=lambda: self.capturar("mozelli"),
                  width=25, height=2, bg="#87CEEB", font=("Arial", 11, "bold")).pack(pady=5)

        ###########################################################################
        # TARGET
        ###########################################################################
        frame_tg = tk.LabelFrame(frame_esq, text="Posição Alvo (Target)", padx=10, pady=10)
        frame_tg.pack(fill="x", pady=5)

        def ajustar_target(eixo, delta):
            if eixo == "x":
                self.target_x += delta
            elif eixo == "y":
                self.target_y += delta
            elif eixo == "z":
                self.target_z += delta
            self.atualizar_display_target()

        def atualizar_valor(entry, eixo):
            try:
                val = float(entry.get())
                setattr(self, f"target_{eixo}", val)
                self.atualizar_display_target()
            except:
                pass

        def enviar_manual():
            self.enviar_target(self.target_x, self.target_y, self.target_z)

        for i, eixo in enumerate(["x", "y", "z"]):
            tk.Label(frame_tg, text=eixo.upper()+":", font=("Arial", 12)).grid(row=i, column=0, padx=4)

            label_valor = tk.Label(frame_tg, text=f"{getattr(self,'target_'+eixo):.3f}",
                                   font=("Arial", 16, "bold"), fg="green")
            label_valor.grid(row=i, column=1, padx=10)
            setattr(self, f"label_target_{eixo}", label_valor)

            frame_setas = tk.Frame(frame_tg)
            frame_setas.grid(row=i, column=2, padx=10)

            tk.Button(frame_setas, text="▲", width=3,
                      command=lambda ex=eixo: ajustar_target(ex, +0.1)).pack()
            tk.Button(frame_setas, text="▼", width=3,
                      command=lambda ex=eixo: ajustar_target(ex, -0.1)).pack()

            entry = tk.Entry(frame_tg, width=7, font=("Arial", 12))
            entry.grid(row=i, column=3, padx=3)
            entry.insert(0, f"{getattr(self,'target_'+eixo):.2f}")

            tk.Button(frame_tg, text=">", width=2,
                      command=lambda e=entry, ex=eixo: atualizar_valor(e, ex)).grid(row=i, column=4, padx=2)

        tk.Button(frame_tg, text="Enviar Target", bg="lightgreen", width=20,
                  command=enviar_manual).grid(row=3, column=0, columnspan=5, pady=10)

        ###########################################################################
        # BANDEJAS
        ###########################################################################
        frame_dir = tk.Frame(self.root)
        frame_dir.pack(side="right", fill="both", expand=True, padx=10, pady=5)

        frame_cmd = tk.LabelFrame(frame_dir, text="Pontos de Inspeção", padx=10, pady=10)
        frame_cmd.pack(fill="x", pady=5)

        tk.Label(frame_cmd, text="Escolha a bandeja:", font=("Arial", 10)).pack(pady=5)

        for nome, x, y, z in self.pontos_inspecao:
            tk.Button(frame_cmd, text=nome,
                      command=lambda x=x, y=y, z=z: self.enviar_target(x, y, z),
                      width=25, height=2, bg="lightblue").pack(pady=5)

        tk.Button(frame_cmd, text="⌂ Voltar à Origem (0,0)",
                  command=lambda: self.enviar_target(0,0,1.5),
                  width=25, height=2, bg="lightyellow").pack(pady=10)

        ###########################################################################
        # LOG
        ###########################################################################
        frame_log = tk.LabelFrame(self.root, text="Histórico (historiador.txt)", padx=10, pady=10)
        frame_log.pack(fill="both", expand=True, padx=10, pady=5)

        self.text_log = scrolledtext.ScrolledText(frame_log, height=10, font=("Courier", 9))
        self.text_log.pack(fill="both", expand=True)

        tk.Button(frame_log, text="Limpar Log Visual",
                  command=self.limpar_log).pack(pady=5)

    ###########################################################################
    # LOG / HISTÓRICO
    ###########################################################################
    def log(self, mensagem):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        linha = f"[{timestamp}] {mensagem}"
        self.text_log.insert(tk.END, linha + "\n")
        self.text_log.see(tk.END)

        try:
            with open("historiador.txt", "a", encoding="utf-8") as f:
                f.write(linha + "\n")
        except:
            pass

    def log_posicao_drone(self):
        timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]
        linha = f"[{timestamp}] POSIÇÃO DRONE: X={self.drone_x:.3f}, Y={self.drone_y:.3f}, Z={self.drone_z:.3f}"

        try:
            with open("historiador.txt", "a", encoding="utf-8") as f:
                f.write(linha + "\n")
        except:
            pass

    def limpar_log(self):
        self.text_log.delete(1.0, tk.END)

    ###########################################################################
    # TCP/IP
    ###########################################################################
    def conectar(self):
        if self.conectado:
            self.log("Já conectado")
            return
        
        try:
            self.socket = socket.socket(socket.AF_INET, socket.SOCK_STREAM)
            self.socket.connect((CLP_HOST, CLP_PORT))

            boas = self.socket.recv(1024).decode().strip()

            self.conectado = True
            self.label_status.config(text="● CONECTADO", fg="green")
            self.btn_conectar.config(state="disabled")
            self.btn_desconectar.config(state="normal")

            self.log(f"Conectado ao CLP ({CLP_HOST}:{CLP_PORT})")
            self.log(f"CLP: {boas}")

            self.rodando = True
            self.thread_leitura = threading.Thread(target=self.thread_ler_status, daemon=True)
            self.thread_leitura.start()

        except Exception as e:
            self.log(f"Erro ao conectar: {e}")

    def desconectar(self):
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

            if self.thread_leitura and self.thread_leitura.is_alive():
                self.thread_leitura.join(timeout=2)

            self.conectado = False
            self.label_status.config(text="● DESCONECTADO", fg="red")
            self.btn_conectar.config(state="normal")
            self.btn_desconectar.config(state="disabled")

            self.log("Desconectado do CLP")
        
        except Exception as e:
            self.log(f"Erro ao desconectar: {e}")

    ###########################################################################
    # TARGET SEND
    ###########################################################################
    def enviar_target(self, x, y, z):
        if not self.conectado:
            self.log("Não conectado")
            return
        
        try:
            comando = f"TARGET {x} {y} {z}\n"
            self.socket.send(comando.encode())

            resposta = self.socket.recv(1024).decode().strip()

            self.log(f"COMANDO ENVIADO: TARGET X={x:.2f}, Y={y:.2f}, Z={z:.2f}")
            self.log(f"Resposta: {resposta}")

            self.target_x = x
            self.target_y = y
            self.target_z = z
            self.atualizar_display_target()

        except Exception as e:
            self.log(f"Erro ao enviar: {e}")
            self.desconectar()

    ###########################################################################
    # CAPTURA
    ###########################################################################
    def capturar(self, nome_objeto):
        if not self.conectado:
            self.log("Não conectado")
            return
        
        try:
            comando = f"CAPTURAR {nome_objeto}\n"
            self.socket.send(comando.encode())

            resposta = self.socket.recv(1024).decode().strip()
            
            self.log(f"CAPTURA: {nome_objeto.upper()}")
            self.log(f"Resultado: {resposta}")

            # Parse da resposta
            if resposta.startswith("OK CAPTURADO"):
                self.log("✓ CAPTURA BEM-SUCEDIDA!")
            elif "SEM_OBJETO" in resposta:
                self.log("✗ ERRO: Nenhum objeto ativo!")
            elif "OBJETO_ERRADO" in resposta:
                self.log("✗ ERRO: Objeto errado!")
            elif "LONGE" in resposta:
                self.log("✗ ERRO: Drone longe do objeto!")

        except Exception as e:
            self.log(f"Erro ao capturar: {e}")
            self.desconectar()

    ###########################################################################
    # STATUS THREAD
    ###########################################################################
    def thread_ler_status(self):
        contador = 0
        
        if self.socket:
            self.socket.settimeout(1.0)

        while self.rodando and self.conectado:
            try:
                self.socket.send(b"STATUS\n")
                resposta = self.socket.recv(1024).decode().strip()

                partes = resposta.split()
                if len(partes) >= 10 and partes[0] == "DRONE":
                    # Parse posição drone
                    self.drone_x = float(partes[1])
                    self.drone_y = float(partes[2])
                    self.drone_z = float(partes[3])

                    # Parse timestamp
                    if "TIME" in partes:
                        idx = partes.index("TIME")
                        self.ultimo_timestamp = f"{partes[idx+1]} {partes[idx+2]}"

                    # Parse game info
                    for p in partes:
                        if p.startswith("GAME_OBJ="):
                            self.game_objeto = p.split('=')[1]
                        elif p.startswith("GAME_POS="):
                            pos = p.split('=')[1].split(',')
                            self.game_pos_x = float(pos[0])
                            self.game_pos_y = float(pos[1])
                        elif p.startswith("SCORE="):
                            self.game_score = int(p.split('=')[1])
                        elif p.startswith("VIDAS="):
                            self.game_vidas = int(p.split('=')[1])

                    self.root.after(0, self.atualizar_display_drone)
                    self.root.after(0, self.atualizar_display_game)
                    self.root.after(0, self.atualizar_timestamp)

                    contador += 1
                    if contador >= 5:
                        self.log_posicao_drone()
                        contador = 0

                time.sleep(0.5)

            except socket.timeout:
                continue
            except Exception as e:
                if self.rodando:
                    print(f"[Thread Leitura] Erro: {e}")
                break
        
        print("[Thread Leitura] Encerrada")

    ###########################################################################
    # ATUALIZAÇÃO DO DISPLAY
    ###########################################################################
    def atualizar_display_drone(self):
        self.label_drone_x.config(text=f"{self.drone_x:.3f} m")
        self.label_drone_y.config(text=f"{self.drone_y:.3f} m")
        self.label_drone_z.config(text=f"{self.drone_z:.3f} m")

    def atualizar_display_target(self):
        self.label_target_x.config(text=f"{self.target_x:.3f}")
        self.label_target_y.config(text=f"{self.target_y:.3f}")
        self.label_target_z.config(text=f"{self.target_z:.3f}")

    def atualizar_display_game(self):
        self.label_score.config(text=str(self.game_score))
        self.label_vidas.config(text=str(self.game_vidas))
        self.label_objeto.config(text=self.game_objeto)
        self.label_obj_pos.config(text=f"({self.game_pos_x:.2f}, {self.game_pos_y:.2f})")

    def atualizar_timestamp(self):
        self.label_timestamp.config(text=self.ultimo_timestamp)

    ###########################################################################
    # FECHAR
    ###########################################################################
    def fechar(self):
        self.rodando = False
        self.desconectar()
        time.sleep(0.3)
        try:
            self.root.quit()
            self.root.destroy()
        except:
            pass

def main():
    root = tk.Tk()
    app = Supervisorio(root)
    root.protocol("WM_DELETE_WINDOW", app.fechar)
    root.mainloop()

if __name__ == "__main__":
    main()