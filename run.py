import subprocess
import sys
import os
import time
import webbrowser
from pathlib import Path

os.environ["PYTHONPATH"] = str(Path(".").resolve())

def main():
    # Paths
    api_path = Path("api")
    frontend_path = Path("frontend")
    
    # Iniciar la API
    print("Iniciando API...")
    api_process = subprocess.Popen(
        [sys.executable, "-m", "uvicorn", "main:app", "--reload"],
        cwd=str(api_path)  # Cambiar al directorio de la API
    )
    
    # Esperar a que la API esté lista
    time.sleep(5)
    
    # Iniciar Streamlit
    print("Iniciando aplicación Streamlit...")
    frontend_process = subprocess.Popen(
        [sys.executable, "-m", "streamlit", "run", str(frontend_path / "app.py")],  # Especificar el archivo directamente
        cwd="."  # Asegurar que el directorio raíz sea el contexto
    )
    
    
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
