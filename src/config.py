import os
from dotenv import load_dotenv

def load_config(key: str):
    # Cargar las variables desde el archivo .env
    load_dotenv()

    return os.getenv(key)