# src/etl/cargar_sqlite.py

from pathlib import Path
import pandas as pd

from src.core.database import get_connection


#
CSV_ANALITICA = Path("data/processed/tabla_analitica_delitos.csv")


def crear_tabla_riesgo(conn):
    """
    Crea la tabla de resultados del modelo de riesgo (vacía).
    El modelo de ML luego INSERTará aquí.
    """
    conn.execute("DROP TABLE IF EXISTS riesgo_municipio_mes;")
    conn.execute(
        """
        CREATE TABLE riesgo_municipio_mes (
            id                INTEGER PRIMARY KEY AUTOINCREMENT,
            municipio         TEXT,
            anio              INTEGER,
            mes               INTEGER,
            categoria         TEXT,   -- HURTO / VIF / SEXUALES / TOTAL
            riesgo_score      REAL,   -- 0-1
            nivel_riesgo      TEXT,   -- BAJO / MEDIO / ALTO
            delitos_observados INTEGER,
            delitos_esperados REAL
        );
        """
    )

    conn.commit()


def main():
    print("=== Cargando datos en SQLite ===")

    if not CSV_ANALITICA.exists():
        raise FileNotFoundError(f"No se encontró el archivo {CSV_ANALITICA}. "
                                "Primero ejecuta el ETL (run_etl).")

    # 1. Leer CSV analítico
    df = pd.read_csv(CSV_ANALITICA)
    print(f"Filas en tabla_analitica_delitos.csv: {len(df)}")
    print(f"Columnas: {list(df.columns)}")

    # 2. Conectar a la base de datos
    conn = get_connection()

    # 3. Guardar tabla de hechos: DELITOS_ANALITICA
    print("\n[1/3] Cargando tabla DELITOS_ANALITICA...")
    df.to_sql("delitos_analitica", conn, if_exists="replace", index=False)
    print("Tabla delitos_analitica creada/reemplazada en SQLite.")

    # 4. Crear tabla MUNICIPIOS a partir de los municipios únicos
    print("\n[2/3] Creando tabla MUNICIPIOS...")

    # usamos solo las columnas que identifican el municipio
    cols_mun = ["municipio"]
    
    if "es_zona_metro" in df.columns:
        cols_mun.append("es_zona_metro")
        df_mun = df[cols_mun].drop_duplicates()
    else:
        df_mun = df[["municipio"]].drop_duplicates()
        df_mun["es_zona_metro"] = 0  
    df_mun["poblacion"] = None
    df_mun["region"] = None

    df_mun = df_mun[["municipio", "poblacion", "region", "es_zona_metro"]]

    df_mun = df_mun.sort_values("municipio")

    df_mun.to_sql("municipios", conn, if_exists="replace", index=False)
    print(f"Tabla municipios creada con {len(df_mun)} registros.")

    # 5. Crear tabla vacía de riesgo (para el modelo de ML)
    print("\n[3/3] Creando tabla RIESGO_MUNICIPIO_MES (vacía)...")
    crear_tabla_riesgo(conn)
    print("Tabla riesgo_municipio_mes lista para usar.")

    conn.close()
    print("\n=== Carga en SQLite terminada ===")


if __name__ == "__main__":
    main()
