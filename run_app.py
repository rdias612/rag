import subprocess
import time
import sys
import os
import signal
import re

# Portas usadas pela aplicação
BACKEND_PORT = 5000
FRONTEND_PORT = 5173

def kill_process_on_port(port: int) -> bool:
    """Mata processos usando uma porta específica (Windows)."""
    if os.name != 'nt':
        # Linux/Mac
        try:
            result = subprocess.run(
                f"lsof -ti:{port} | xargs kill -9",
                shell=True, capture_output=True
            )
            return result.returncode == 0
        except:
            return False
    
    # Windows - encontrar PIDs usando netstat
    try:
        result = subprocess.run(
            ['netstat', '-ano'], 
            capture_output=True, text=True
        )
        
        pids_killed = set()
        for line in result.stdout.split('\n'):
            if f':{port}' in line and 'LISTENING' in line:
                # Extrair PID (último número na linha)
                parts = line.split()
                if parts:
                    pid = parts[-1]
                    if pid.isdigit() and pid not in pids_killed:
                        try:
                            subprocess.run(
                                ['taskkill', '/F', '/T', '/PID', pid],
                                capture_output=True
                            )
                            pids_killed.add(pid)
                            print(f"   ✓ Processo {pid} na porta {port} encerrado")
                        except:
                            pass
        
        return len(pids_killed) > 0
    except Exception as e:
        print(f"   ⚠ Erro ao verificar porta {port}: {e}")
        return False


def cleanup_ports():
    """Limpa as portas antes de iniciar."""
    print("🔍 Verificando portas...")
    
    killed_backend = kill_process_on_port(BACKEND_PORT)
    killed_frontend = kill_process_on_port(FRONTEND_PORT)
    
    if killed_backend or killed_frontend:
        print("   ⏳ Aguardando liberação das portas...")
        time.sleep(2)
    else:
        print("   ✓ Portas livres")


def install_dependencies():
    """Instala as dependências do projeto."""
    print("📦 Verificando dependências...")
    try:
        subprocess.run(
            [sys.executable, "-m", "pip", "install", "-r", "requirements.txt"],
            check=True,
            capture_output=True
        )
        print("   ✓ Dependências verificadas/instaladas")
    except Exception as e:
        print(f"   ⚠ Erro ao verificar dependências: {e}")


def run_app():
    print("🚀 Iniciando RAG System (Backend + Frontend)...\n")
    
    # Instalar dependências
    install_dependencies()
    
    # Limpar portas antes de iniciar
    cleanup_ports()
    print()
    
    # Paths
    root_dir = os.path.abspath(os.path.dirname(__file__))
    frontend_dir = os.path.join(root_dir, "frontend")
    
    # Flags para criação de processo no Windows
    creationflags = 0
    if os.name == 'nt':
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
    
    # 1. Iniciar Backend (Flask)
    print(f"📡 Iniciando Backend na porta {BACKEND_PORT}...")
    backend_process = subprocess.Popen(
        [sys.executable, "-c", 
         f"from src.app import create_app; app = create_app(); app.run(host='0.0.0.0', port={BACKEND_PORT}, debug=False, threaded=True)"],
        cwd=root_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
        creationflags=creationflags
    )

    # 2. Iniciar Frontend (Vite)
    print(f"🎨 Iniciando Frontend na porta {FRONTEND_PORT}...")
    frontend_process = subprocess.Popen(
        ["npm.cmd" if os.name == 'nt' else "npm", "run", "dev"],
        cwd=frontend_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
        creationflags=creationflags
    )

    # Funções para ler e imprimir logs
    def stream_logs(process, name):
        for line in iter(process.stdout.readline, ''):
            if line:
                print(f"[{name}] {line.strip()}")

    import threading
    threading.Thread(target=stream_logs, args=(backend_process, "BACKEND"), daemon=True).start()
    threading.Thread(target=stream_logs, args=(frontend_process, "FRONTEND"), daemon=True).start()

    def cleanup():
        print("\n\n🛑 Encerrando sistema...")
        
        if os.name == 'nt':
            try:
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(backend_process.pid)], 
                             capture_output=True)
            except:
                pass
            try:
                subprocess.run(['taskkill', '/F', '/T', '/PID', str(frontend_process.pid)], 
                             capture_output=True)
            except:
                pass
        else:
            try:
                backend_process.terminate()
                frontend_process.terminate()
                time.sleep(0.5)
                backend_process.kill()
                frontend_process.kill()
            except:
                pass
        
        print("✅ Sistema encerrado.")

    def signal_handler(sig, frame):
        cleanup()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)
    if os.name == 'nt':
        signal.signal(signal.SIGBREAK, signal_handler)

    # Aguardar um pouco para os processos iniciarem
    time.sleep(5)

    print(f"\n✅ Sistema rodando!")
    print(f"👉 Backend:  http://localhost:{BACKEND_PORT}")
    print(f"👉 Frontend: http://localhost:{FRONTEND_PORT}")
    print("\nPressione Ctrl+C para encerrar.\n")

    try:
        while True:
            if backend_process.poll() is not None:
                print("❌ Backend parou inesperadamente.")
                # Tentar ler o erro final
                stderr_output = backend_process.stdout.read()
                if stderr_output:
                    print(f"Erro do Backend:\n{stderr_output}")
                cleanup()
                break
            if frontend_process.poll() is not None:
                print("❌ Frontend parou inesperadamente.")
                cleanup()
                break
            time.sleep(1)
    except KeyboardInterrupt:
        cleanup()
        sys.exit(0)

if __name__ == "__main__":
    run_app()
