import subprocess
import time
import sys
import os
import signal

def run_app():
    print("🚀 Iniciando RAG System (Backend + Frontend)...")
    
    # Paths
    root_dir = os.path.abspath(os.path.dirname(__file__))
    frontend_dir = os.path.join(root_dir, "frontend")
    
    # Flags para criação de processo no Windows (para poder matar grupo de processos)
    creationflags = 0
    if os.name == 'nt':
        creationflags = subprocess.CREATE_NEW_PROCESS_GROUP
    
    # 1. Iniciar Backend (Flask)
    print("📡 Iniciando Backend na porta 5000...")
    backend_process = subprocess.Popen(
        [sys.executable, "-c", 
         "from src.app import create_app; app = create_app(); app.run(host='0.0.0.0', port=5000, debug=False)"],
        cwd=root_dir,
        stdout=subprocess.PIPE,
        stderr=subprocess.STDOUT,
        text=True,
        bufsize=1,
        universal_newlines=True,
        creationflags=creationflags
    )

    # 2. Iniciar Frontend (Vite)
    print("🎨 Iniciando Frontend na porta 5173...")
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

    def cleanup():
        print("\n\n🛑 Encerrando sistema...")
        
        # Matar processos de forma mais agressiva no Windows
        if os.name == 'nt':
            # Usar taskkill para matar árvore de processos
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
            # Linux/Mac - tentar terminate primeiro, depois kill
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

    # Monitorar outputs (opcional: simplificado aqui)
    print("\n✅ Sistema rodando!")
    print("👉 Backend:  http://localhost:5000")
    print("👉 Frontend: http://localhost:5173")
    print("\nPressione Ctrl+C para encerrar.\n")

    try:
        while True:
            # Verificar se algum processo morreu
            if backend_process.poll() is not None:
                print("❌ Backend parou inesperadamente.")
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
