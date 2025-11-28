
from pathlib import Path
import sqlite3

#  archivo de base de datos
DB_PATH = Path("db/seguridad_santander.db")


def get_connection() -> sqlite3.Connection:
    
    # Asegura que la carpeta db exista
    DB_PATH.parent.mkdir(parents=True, exist_ok=True)
    conn = sqlite3.connect(DB_PATH)
    return conn
