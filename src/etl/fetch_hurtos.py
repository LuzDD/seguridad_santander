# src/etl/fetch_hurtos.py

from pathlib import Path
import json
import pandas as pd
from sodapy import Socrata

from src.core.config import (
    SOCRATA_DOMAIN,
    DATASET_HURTOS,
    DEPARTAMENTO_FILTRO,
    CHUNK_SIZE,
    APP_TOKEN,
)

DATA_RAW_DIR = Path("data/raw")


def _fetch_all_rows(dataset_id: str, where_clause: str | None = None) -> pd.DataFrame:
    """
    Descarga TODOS los registros de un dataset de datos.gov.co usando paginación.
    Devuelve un DataFrame con todos los datos.
    """
    client = Socrata(SOCRATA_DOMAIN, APP_TOKEN, timeout=60)
    offset = 0
    frames: list[pd.DataFrame] = []

    while True:
        params = {
            "limit": CHUNK_SIZE,
            "offset": offset,
        }
        if where_clause:
            params["where"] = where_clause

        results = client.get(dataset_id, **params)

        if not results:
            break  # no hay más filas

        df_chunk = pd.DataFrame.from_records(results)
        frames.append(df_chunk)

        offset += CHUNK_SIZE
        print(f"{dataset_id}: descargadas {offset} filas (aprox.)...")

    client.close()

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)


def fetch_hurtos_santander() -> pd.DataFrame:
    """
    Descarga el dataset de hurtos filtrado por departamento = SANTANDER.
    Guarda una copia cruda en data/raw/hurtos_raw.json
    y devuelve un DataFrame.
    """
    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)

    where_clause = f"departamento = '{DEPARTAMENTO_FILTRO}'"
    df = _fetch_all_rows(DATASET_HURTOS, where_clause=where_clause)

    # Guardar copia cruda en JSON (lista de dict)
    raw_path = DATA_RAW_DIR / "hurtos_raw.json"
    df.to_dict(orient="records")  # asegura que es serializable

    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(df.to_dict(orient="records"), f, ensure_ascii=False)

    print(f"HURTOS - Filas descargadas: {len(df)}. Guardado en {raw_path}")
    return df


if __name__ == "__main__":
    df_hurtos = fetch_hurtos_santander()
    print(df_hurtos.head())
