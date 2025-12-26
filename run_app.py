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
        universal_newlines=True
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
        universal_newlines=True
    )

    def signal_handler(sig, frame):
        print("\n\n🛑 Encerrando sistema...")
        backend_process.terminate()
        frontend_process.terminate()
        sys.exit(0)

    signal.signal(signal.SIGINT, signal_handler)

    # Monitorar outputs (opcional: simplificado aqui)
    print("\n✅ Sistema rodando!")
    print("👉 Backend:  http://localhost:5000")
    print("👉 Frontend: http://localhost:5173")
    print("\nPressione Ctrl+C para encerrar.\n")

    try:
        while True:
            # Ler linhas do backend se quiser debugar no terminal
            # line = backend_process.stdout.readline()
            # if line: print(f"[BACKEND] {line.strip()}")
            
            # Verificar se algum processo morreu
            if backend_process.poll() is not None:
                print("❌ Backend parou inesperadamente.")
                break
            if frontend_process.poll() is not None:
                print("❌ Frontend parou inesperadamente.")
                break
            time.sleep(1)
    except KeyboardInterrupt:
        signal_handler(None, None)

if __name__ == "__main__":
    run_app()
