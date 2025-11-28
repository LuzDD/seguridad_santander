# src/ml/train_model.py

from pathlib import Path
import sqlite3

import numpy as np
import pandas as pd

from sklearn.ensemble import RandomForestRegressor
from sklearn.linear_model import LinearRegression
from sklearn.model_selection import train_test_split
from sklearn.metrics import mean_absolute_error, r2_score


# Ruta a la base de datos SQLite (db/seguridad_santander.db)
BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "db" / "seguridad_santander.db"


# ============================================================
# 1. Cargar datos agregados desde delitos_analitica
# ============================================================

def cargar_datos_agrupados() -> pd.DataFrame:
    """
    Lee delitos_analitica y agrupa por municipio / año / mes / categoría.

    Salida:
        municipio, anio, mes, categoria, delitos_observados
    """
    conn = sqlite3.connect(DB_PATH)

    query = """
    SELECT
        municipio,
        anio,
        mes,
        categoria,
        SUM(cantidad) AS delitos_observados
    FROM delitos_analitica
    GROUP BY
        municipio, anio, mes, categoria
    ORDER BY
        municipio, categoria, anio, mes;
    """

    df = pd.read_sql_query(query, conn)
    conn.close()
    return df


# ============================================================
# 2. Crear features para el modelo
# ============================================================

def crear_features(df: pd.DataFrame) -> pd.DataFrame:
    """
    Crea variables para el modelo (delitos del mes anterior, etc.).

    - Ordena por municipio/categoría y tiempo
    - Calcula delitos_prev_mes por grupo
    - Elimina filas sin histórico
    """

    df = df.sort_values(["municipio", "categoria", "anio", "mes"])

    # Delitos del mes anterior por municipio y categoría
    df["delitos_prev_mes"] = (
        df.groupby(["municipio", "categoria"])["delitos_observados"]
          .shift(1)
    )

    # Eliminamos las filas donde no hay histórico (primer mes)
    df = df.dropna(subset=["delitos_prev_mes"]).reset_index(drop=True)

    # Aseguramos tipo numérico
    df["delitos_prev_mes"] = df["delitos_prev_mes"].astype(float)
    df["mes"] = df["mes"].astype(int)

    return df


# ============================================================
# 3. Entrenar y COMPARAR modelos
# ============================================================

def entrenar_modelos(df_feat: pd.DataFrame):
    """
    Entrena dos modelos:
      - Regresión Lineal (baseline)
      - Random Forest (modelo avanzado)

    Devuelve el mejor modelo según MAE, junto con su nombre y métricas.
    """

    X = df_feat[["mes", "delitos_prev_mes"]]
    y = df_feat["delitos_observados"].astype(float)

    X_train, X_test, y_train, y_test = train_test_split(
        X, y, test_size=0.2, random_state=42
    )

    # ----- Modelo base: Regresión Lineal -----
    lr = LinearRegression()
    lr.fit(X_train, y_train)

    y_pred_lr = lr.predict(X_test)
    mae_lr = mean_absolute_error(y_test, y_pred_lr)
    r2_lr = r2_score(y_test, y_pred_lr)

    # ----- Modelo avanzado: Random Forest -----
    rf = RandomForestRegressor(
        n_estimators=200,
        random_state=42,
        n_jobs=-1,
    )
    rf.fit(X_train, y_train)

    y_pred_rf = rf.predict(X_test)
    mae_rf = mean_absolute_error(y_test, y_pred_rf)
    r2_rf = r2_score(y_test, y_pred_rf)

    print("=== Evaluación modelos de riesgo ===")
    print(f"LinearRegression  -> MAE: {mae_lr:.2f}  R²: {r2_lr:.3f}")
    print(f"RandomForest      -> MAE: {mae_rf:.2f}  R²: {r2_rf:.3f}")

    # Elegimos el modelo con mejor MAE (más bajo)
    if mae_rf <= mae_lr:
        print(">> Modelo seleccionado: RandomForest (mejor MAE)")
        modelo = rf
        nombre = "RandomForestRegressor"
        mae, r2 = mae_rf, r2_rf
    else:
        print(">> Modelo seleccionado: LinearRegression (mejor MAE)")
        modelo = lr
        nombre = "LinearRegression"
        mae, r2 = mae_lr, r2_lr

    print(f"Modelo final: {nombre}  |  MAE={mae:.2f}  R²={r2:.3f}")
    return modelo, nombre, mae, r2


# ============================================================
# 4. Calcular riesgo usando el modelo elegido
# ============================================================

def calcular_riesgo(df_feat: pd.DataFrame, model):
    """
    Aplica el modelo y construye la tabla de riesgo municipio/mes.

    Agrega:
      - delitos_esperados (predicción del modelo)
      - riesgo_score (observados / esperados)
      - nivel_riesgo (BAJO / MEDIO / ALTO)
    """

    X = df_feat[["mes", "delitos_prev_mes"]]
    df_feat["delitos_esperados"] = model.predict(X)

    # Evitar divisiones por cero
    df_feat["delitos_esperados"] = df_feat["delitos_esperados"].clip(lower=0.1)

    # Score de riesgo: observados / esperados
    df_feat["riesgo_score"] = (
        df_feat["delitos_observados"] / df_feat["delitos_esperados"]
    )

    # Clasificamos en BAJO / MEDIO / ALTO según cuantiles
    q1 = df_feat["riesgo_score"].quantile(0.33)
    q2 = df_feat["riesgo_score"].quantile(0.66)

    def clasificar(score):
        if score <= q1:
            return "BAJO"
        elif score <= q2:
            return "MEDIO"
        else:
            return "ALTO"

    df_feat["nivel_riesgo"] = df_feat["riesgo_score"].apply(clasificar)

    # Preparamos solo las columnas que van a SQLite
    df_out = df_feat[
        [
            "municipio",
            "anio",
            "mes",
            "categoria",
            "riesgo_score",
            "nivel_riesgo",
            "delitos_observados",
            "delitos_esperados",
        ]
    ].copy()

    return df_out


# ============================================================
# 5. Guardar resultados en SQLite
# ============================================================

def guardar_en_sqlite(df_riesgo: pd.DataFrame):
    """
    Vacía y rellena la tabla riesgo_municipio_mes en SQLite.
    """

    conn = sqlite3.connect(DB_PATH)
    cur = conn.cursor()

    # Vaciamos la tabla pero mantenemos el esquema (id AUTOINCREMENT)
    cur.execute("DELETE FROM riesgo_municipio_mes;")

    # Insertamos sin la columna id, SQLite la genera sola
    df_riesgo.to_sql(
        "riesgo_municipio_mes",
        conn,
        if_exists="append",
        index=False,
    )

    conn.commit()
    conn.close()

    print(f"Filas insertadas en riesgo_municipio_mes: {len(df_riesgo)}")


# ============================================================
# 6. Orquestador
# ============================================================

def main():
    print("=== Entrenando modelos de riesgo por municipio/mes ===")

    df_raw = cargar_datos_agrupados()
    print(f"Filas agrupadas: {len(df_raw)}")

    df_feat = crear_features(df_raw)
    print(f"Filas con histórico (features): {len(df_feat)}")

    modelo, nombre_modelo, mae, r2 = entrenar_modelos(df_feat)

    df_riesgo = calcular_riesgo(df_feat, modelo)

    guardar_en_sqlite(df_riesgo)

    print("=== Proceso de ML terminado ===")


if __name__ == "__main__":
    main()

