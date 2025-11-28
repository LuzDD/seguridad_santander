# src/etl/fetch_delitos_sexuales.py

from pathlib import Path
import json
import pandas as pd
from sodapy import Socrata

from src.core.config import (
    SOCRATA_DOMAIN,
    DATASET_DELITOS_SEXUALES,
    DEPARTAMENTO_FILTRO,
    CHUNK_SIZE,
    APP_TOKEN,
)

DATA_RAW_DIR = Path("data/raw")


def _fetch_all_rows(dataset_id: str, where_clause: str | None = None) -> pd.DataFrame:
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
            break

        df_chunk = pd.DataFrame.from_records(results)
        frames.append(df_chunk)

        offset += CHUNK_SIZE
        print(f"{dataset_id}: descargadas {offset} filas (aprox.)...")

    client.close()

    if not frames:
        return pd.DataFrame()

    return pd.concat(frames, ignore_index=True)


def fetch_delitos_sexuales_santander() -> pd.DataFrame:
  
    DATA_RAW_DIR.mkdir(parents=True, exist_ok=True)

    where_clause = f"departamento = '{DEPARTAMENTO_FILTRO}'"
    df = _fetch_all_rows(DATASET_DELITOS_SEXUALES, where_clause=where_clause)

    raw_path = DATA_RAW_DIR / "delitos_sexuales_raw.json"
    with open(raw_path, "w", encoding="utf-8") as f:
        json.dump(df.to_dict(orient="records"), f, ensure_ascii=False)

    print(
        f"DELITOS SEXUALES - Filas descargadas: {len(df)}. Guardado en {raw_path}"
    )
    return df


if __name__ == "__main__":
    df_ds = fetch_delitos_sexuales_santander()
    print(df_ds.head())
