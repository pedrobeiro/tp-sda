import time
import random
from coppeliasim_zmqremoteapi_client import RemoteAPIClient

############################
# CONFIG
############################
TRAY_COUNT = 4
SPAWN_INTERVAL = 2.0  # segundos
DISPLAY_TIME = 10.0    # segundos
HIDDEN_POS = [0, 0, -1]
Z_OFFSET = 0.1

############################
# Main
############################
def main():
    # Conectar CoppeliaSim
    client = RemoteAPIClient()
    sim = client.getObject('sim')
    
    # Garantir simulação rodando
    if sim.getSimulationState() != sim.simulation_stopped:
        sim.stopSimulation()
        while sim.getSimulationState() != sim.simulation_stopped:
            time.sleep(0.1)
    sim.startSimulation()
    time.sleep(0.5)
    
    # Obter handles das bandejas
    trays = []
    for i in range(TRAY_COUNT):
        try:
            tray = sim.getObject(f"/genericTray[{i}]")
            trays.append(tray)
        except:
            print(f"[WARN] Bandeja genericTray[{i}] não encontrada")
    
    if not trays:
        print("[ERROR] Nenhuma bandeja encontrada!")
        return
    
    print(f"[GAME] {len(trays)} bandejas encontradas")
    
    # Obter handles dos objetos
    try:
        armando = sim.getObject("/Armando")
        mozelli = sim.getObject("/Mozelli")
        objects = [armando, mozelli]
        object_names = ["Armando", "Mozelli"]
        print("[GAME] Objetos encontrados: Armando, Mozelli")
    except Exception as e:
        print(f"[ERROR] Erro ao buscar objetos: {e}")
        return
    
    # Esconder objetos inicialmente
    for obj in objects:
        sim.setObjectPosition(obj, -1, HIDDEN_POS)
    
    print("[GAME] Jogo iniciado! Objetos aparecerão a cada 10s")
    
    try:
        while True:
            # Aguardar intervalo de spawn
            time.sleep(SPAWN_INTERVAL)
            
            # Selecionar objeto e bandeja aleatórios
            obj_idx = random.randint(0, len(objects) - 1)
            tray_idx = random.randint(0, len(trays) - 1)
            
            selected_obj = objects[obj_idx]
            selected_tray = trays[tray_idx]
            obj_name = object_names[obj_idx]
            
            # Obter posição da bandeja
            tray_pos = sim.getObjectPosition(selected_tray, -1)
            spawn_pos = [tray_pos[0], tray_pos[1], tray_pos[2] + Z_OFFSET]
            
            # Spawnar objeto
            sim.setObjectPosition(selected_obj, -1, spawn_pos)
            print(f"[GAME] {obj_name} apareceu na bandeja {tray_idx}")
            
            # Aguardar tempo de exibição
            time.sleep(DISPLAY_TIME)
            
            # Esconder objeto
            sim.setObjectPosition(selected_obj, -1, HIDDEN_POS)
            print(f"[GAME] {obj_name} removido")
            
    except KeyboardInterrupt:
        print("\n[GAME] Parando jogo...")
    finally:
        # Esconder todos os objetos
        for obj in objects:
            sim.setObjectPosition(obj, -1, HIDDEN_POS)
        try:
            sim.stopSimulation()
        except:
            pass
        print("[GAME] Finalizado.")

if __name__ == "__main__":
    main()