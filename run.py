import subprocess
import sys
import time
import webbrowser
from pathlib import Path

def main():
    # Paths
    api_path = Path("api")
    frontend_path = Path("frontend")
    
    # Iniciar la API
    print("Iniciando API...")
    api_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--reload"],
        cwd=api_path
    )
    
    # Esperar a que la API esté lista
    time.sleep(5)
    
    # Iniciar Streamlit
    print("Iniciando aplicación Streamlit...")
    frontend_process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", "app.py"],
        cwd=frontend_path
    )
    
    # Abrir el navegador
    webbrowser.open("http://localhost:8501")
    
    try:
        # Mantener el script corriendo
        api_process.wait()
        frontend_process.wait()
    except KeyboardInterrupt:
        print("\nDeteniendo servicios...")
        api_process.terminate()
        frontend_process.terminate()
        sys.exit(0)

if __name__ == "__main__":
    main()