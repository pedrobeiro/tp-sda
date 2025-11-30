# mes.py
from datetime import datetime
from opcua import Client
import time

CHAINED_ENDPOINT = "opc.tcp://localhost:54000/OPCUA/ChainedServer"

def connect_chained_server(url=CHAINED_ENDPOINT):
    """
    Conecta ao servidor encadeado e retorna o client e os nós das variáveis.
    """
    print(f"[MES] Conectando ao servidor encadeado: {url}")
    client = Client(url)
    client.connect()
    print("[MES] Conectado ao servidor encadeado")

    root = client.get_objects_node()

    drone_folder = None
    for node in root.get_children():
        try:
            if node.get_browse_name().Name.lower() == "drone":
                drone_folder = node
                break
        except:
            pass

    if drone_folder is None:
        raise RuntimeError("Objeto 'Drone' não encontrado no servidor encadeado")

    name_to_node = {}
    for var in drone_folder.get_children():
        try:
            nm = var.get_browse_name().Name
            name_to_node[nm.lower()] = var
        except:
            pass

    dX = name_to_node.get("dronex")
    dY = name_to_node.get("droney")
    dZ = name_to_node.get("dronez")
    tX = name_to_node.get("targetx")
    tY = name_to_node.get("targety")
    tZ = name_to_node.get("targetz")

    if not all([dX, dY, dZ, tX, tY, tZ]):
        found = ", ".join(sorted(name_to_node.keys()))
        raise RuntimeError(
            "Variáveis esperadas não encontradas: "
            f"DroneX, DroneY, DroneZ, TargetX, TargetY, TargetZ. Encontradas: {found}"
        )

    print("[MES] Variáveis mapeadas com sucesso")
    return client, (dX, dY, dZ, tX, tY, tZ)


def main():
    """
    Lê drone/target periodicamente do servidor e salva em mes.txt.
    """
    client, (dX, dY, dZ, tX, tY, tZ) = connect_chained_server()
    print("[MES] Iniciando leitura periódica (Ctrl+C para sair)")

    try:
        while True:
            try:
                drone_x = float(dX.get_value())
                drone_y = float(dY.get_value())
                drone_z = float(dZ.get_value())
                target_x = float(tX.get_value())
                target_y = float(tY.get_value())
                target_z = float(tZ.get_value())
            except Exception as e:
                print(f"[MES] Erro ao ler do servidor: {e}")
                time.sleep(1)
                continue

            timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S.%f")[:-3]

            linha = (
                f"{timestamp}; "
                f"DRONE_X={drone_x:.3f}; DRONE_Y={drone_y:.3f}; DRONE_Z={drone_z:.3f}; "
                f"TARGET_X={target_x:.3f}; TARGET_Y={target_y:.3f}; TARGET_Z={target_z:.3f}\n"
            )

            try:
                with open("mes.txt", "a", encoding="utf-8") as f:
                    f.write(linha)
            except Exception as e:
                print(f"[MES] Erro ao escrever em mes.txt: {e}")

            print("[MES]", linha.strip())
            time.sleep(1)

    except KeyboardInterrupt:
        print("\n[MES] Encerrando...")

    finally:
        try:
            client.disconnect()
        except:
            pass
        print("[MES] Finalizado com sucesso.")


if __name__ == "__main__":
    main()
