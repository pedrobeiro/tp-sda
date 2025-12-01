import time
from opcua import Client, Server

UPSTREAM_URL = "opc.tcp://localhost:53530/OPCUA/SimulationServer"
CHAINED_ENDPOINT = "opc.tcp://0.0.0.0:54000/OPCUA/ChainedServer"
NAMESPACE_URI = "http://ufmg.br/drone/ChainedServer"
DT = 0.2  # 5 Hz


def connect_upstream(url=UPSTREAM_URL):
    """
    Conecta ao servidor upstream e retorna client e nós das variáveis.
    """
    print(f"[CHAINED-CLIENT] Conectando ao servidor upstream: {url}")
    client = Client(url)
    client.connect()
    print("[CHAINED-CLIENT] Conectado ao upstream")

    root = client.get_objects_node()

    drone_folder = None
    try:
        drone_folder = root.get_child(["3:Drone"])
    except Exception:
        for node in root.get_children():
            try:
                if node.get_browse_name().Name.lower() == "drone":
                    drone_folder = node
                    break
            except Exception:
                pass

    if drone_folder is None:
        raise RuntimeError("Pasta 'Drone' não encontrada no servidor upstream")

    name_to_node = {}
    for var in drone_folder.get_children():
        try:
            nm = var.get_browse_name().Name
            name_to_node[nm.lower()] = var
        except Exception:
            pass

    tX = name_to_node.get("targetx")
    tY = name_to_node.get("targety")
    tZ = name_to_node.get("targetz")
    dX = name_to_node.get("dronex")
    dY = name_to_node.get("droney")
    dZ = name_to_node.get("dronez")

    if not all([tX, tY, tZ, dX, dY, dZ]):
        found = ", ".join(sorted(name_to_node.keys()))
        raise RuntimeError(
            "Variáveis esperadas não encontradas no upstream. "
            "Quero TargetX, TargetY, TargetZ, DroneX, DroneY, DroneZ. "
            f"Encontradas: {found}"
        )

    print("[CHAINED-CLIENT] Variáveis mapeadas no upstream")
    return client, (tX, tY, tZ, dX, dY, dZ)


def start_chained_server():
    """
    Inicia o servidor encadeado com objeto Drone e variáveis locais.
    """
    server = Server()
    server.set_endpoint(CHAINED_ENDPOINT)
    server.set_server_name("ChainedDroneServer")

    idx = server.register_namespace(NAMESPACE_URI)
    objects = server.get_objects_node()
    drone_obj = objects.add_object(idx, "Drone")

    var_drone_x = drone_obj.add_variable(idx, "DroneX", 0.0)
    var_drone_y = drone_obj.add_variable(idx, "DroneY", 0.0)
    var_drone_z = drone_obj.add_variable(idx, "DroneZ", 0.0)

    var_target_x = drone_obj.add_variable(idx, "TargetX", 0.0)
    var_target_y = drone_obj.add_variable(idx, "TargetY", 0.0)
    var_target_z = drone_obj.add_variable(idx, "TargetZ", 1.5)

    server.start()
    print(f"[CHAINED-SERVER] Servidor OPC UA encadeado iniciado em {CHAINED_ENDPOINT}")

    return server, {
        "DroneX": var_drone_x,
        "DroneY": var_drone_y,
        "DroneZ": var_drone_z,
        "TargetX": var_target_x,
        "TargetY": var_target_y,
        "TargetZ": var_target_z,
    }


def main():
    """
    Espelha variáveis do upstream para o servidor encadeado em loop.
    """
    upstream_client, (tX, tY, tZ, dX, dY, dZ) = connect_upstream()
    chained_server, local_vars = start_chained_server()

    print("[CHAINED] Iniciando loop de espelhamento (Ctrl+C para sair)")

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
                print(f"[CHAINED-CLIENT] Erro ao ler do upstream: {e}")
                time.sleep(DT)
                continue

            try:
                local_vars["DroneX"].set_value(drone_x)
                local_vars["DroneY"].set_value(drone_y)
                local_vars["DroneZ"].set_value(drone_z)
                local_vars["TargetX"].set_value(target_x)
                local_vars["TargetY"].set_value(target_y)
                local_vars["TargetZ"].set_value(target_z)
            except Exception as e:
                print(f"[CHAINED-SERVER] Erro ao escrever nas variáveis locais: {e}")

            time.sleep(DT)

    except KeyboardInterrupt:
        print("\n[CHAINED] Encerrando...")

    finally:
        try:
            upstream_client.disconnect()
        except Exception:
            pass
        try:
            chained_server.stop()
        except Exception:
            pass

        print("[CHAINED] Finalizado com sucesso.")


if __name__ == "__main__":
    main()
