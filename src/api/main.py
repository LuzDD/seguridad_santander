from pathlib import Path
from typing import List, Optional

import sqlite3
from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

BASE_DIR = Path(__file__).resolve().parents[2]
DB_PATH = BASE_DIR / "db" / "seguridad_santander.db"

app = FastAPI(title="API Seguridad Santander")

app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)

def query_db(sql: str, params: tuple = ()) -> List[dict]:
    conn = sqlite3.connect(DB_PATH)
    conn.row_factory = sqlite3.Row
    cur = conn.cursor()
    cur.execute(sql, params)
    rows = cur.fetchall()
    conn.close()
    return [dict(r) for r in rows]


# === APP FASTAPI ===
app = FastAPI(
    title="API Seguridad Santander",
    version="0.1.0",
    description="API para consumir los datos procesados y el modelo de riesgo."
)

# CORS para que el front pueda consumir la API desde otra URL
app.add_middleware(
    CORSMiddleware,
    allow_origins=["*"],       # en producción se restringe
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.get("/")
def root():
    """Ping básico para saber que la API está viva."""
    return {
        "message": "API Seguridad Santander OK",
        "endpoints": [
            "/municipios",
            "/delitos",
            "/riesgo",
            "/resumen_delitos",
        ],
    }


# ---------- ENDPOINTS PRINCIPALES ----------

@app.get("/municipios")
def get_municipios():
    """
    Lista de municipios (para combos y unión con el GeoJSON).
    """
    sql = """
        SELECT
            municipio,
            region,
            es_zona_metro
        FROM municipios
        ORDER BY municipio;
    """
    return query_db(sql)


@app.get("/delitos")
def get_delitos(
    municipio: Optional[str] = None,
    categoria: Optional[str] = None,   # HURTO / VIF / SEXUALES
    anio: Optional[int] = None,
    mes: Optional[int] = None,
    genero: Optional[str] = None,
    grupo_etario: Optional[str] = None,
    limit: int = 500,
    offset: int = 0,
):
    """
    Datos agregados de delitos_analitica con filtros.
    Se agrupa por municipio/año/mes/categoría/género/grupo_etario.
    """

    filtros = []
    params: list = []

    if municipio:
        filtros.append("municipio = ?")
        params.append(municipio)

    if categoria:
        filtros.append("categoria = ?")
        params.append(categoria)

    if anio:
        filtros.append("anio = ?")
        params.append(anio)

    if mes:
        filtros.append("mes = ?")
        params.append(mes)

    if genero:
        filtros.append("genero = ?")
        params.append(genero)

    if grupo_etario:
        filtros.append("grupo_etario = ?")
        params.append(grupo_etario)

    where_clause = "WHERE " + " AND ".join(filtros) if filtros else ""

    sql = f"""
        SELECT
            municipio,
            anio,
            mes,
            categoria,
            genero,
            grupo_etario,
            SUM(cantidad) AS cantidad
        FROM delitos_analitica
        {where_clause}
        GROUP BY municipio, anio, mes, categoria, genero, grupo_etario
        ORDER BY anio, mes, municipio
        LIMIT ? OFFSET ?;
    """

    params.extend([limit, offset])
    return query_db(sql, tuple(params))


@app.get("/riesgo")
def get_riesgo(
    municipio: Optional[str] = None,
    categoria: Optional[str] = None,   # HURTO / VIF / SEXUALES
    anio: Optional[int] = None,
    mes: Optional[int] = None,
    limit: int = 500,
    offset: int = 0,
):
    """
    Nivel de riesgo por municipio/mes/categoría calculado por el modelo.
    Datos vienen de la tabla riesgo_municipio_mes, que llena el script de ML.
    """

    filtros = []
    params: list = []

    if municipio:
        filtros.append("municipio = ?")
        params.append(municipio)

    if categoria:
        filtros.append("categoria = ?")
        params.append(categoria)

    if anio:
        filtros.append("anio = ?")
        params.append(anio)

    if mes:
        filtros.append("mes = ?")
        params.append(mes)

    where_clause = "WHERE " + " AND ".join(filtros) if filtros else ""

    sql = f"""
        SELECT
            municipio,
            anio,
            mes,
            categoria,
            riesgo_score,
            nivel_riesgo,
            delitos_observados,
            delitos_esperados
        FROM riesgo_municipio_mes
        {where_clause}
        ORDER BY anio, mes, municipio
        LIMIT ? OFFSET ?;
    """

    params.extend([limit, offset])
    return query_db(sql, tuple(params))


@app.get("/resumen_delitos")
def resumen_delitos(
    categoria: str,          # HURTO / VIF / SEXUALES
    anio: int,
    municipio: Optional[str] = None,
):
    """
    Resumen anual por municipio para una categoría:
      - total de delitos en el año
      - arma más frecuente y número de casos con esa arma

    Se apoya en la tabla delitos_analitica (datos limpios).
    """

    filtros_mun = ""
    params: list = [categoria, anio]

    if municipio:
        filtros_mun = "AND municipio = ?"
        params.append(municipio)

    sql = f"""
        WITH base AS (
            SELECT
                municipio,
                anio,
                categoria,
                arma_categoria,
                SUM(cantidad) AS total_casos
            FROM delitos_analitica
            WHERE categoria = ?
              AND anio = ?
              {filtros_mun}
            GROUP BY municipio, anio, categoria, arma_categoria
        ),
        agregados AS (
            SELECT
                municipio,
                anio,
                categoria,
                SUM(total_casos) AS total_anual
            FROM base
            GROUP BY municipio, anio, categoria
        ),
        arma_principal AS (
            SELECT
                b.municipio,
                b.arma_categoria,
                b.total_casos,
                ROW_NUMBER() OVER (
                    PARTITION BY b.municipio
                    ORDER BY b.total_casos DESC
                ) AS rn
            FROM base b
        )
        SELECT
            a.municipio,
            a.anio,
            a.categoria,
            a.total_anual AS total_delitos_anio,
            ap.arma_categoria AS arma_mas_frecuente,
            ap.total_casos AS casos_con_esa_arma
        FROM agregados a
        LEFT JOIN arma_principal ap
               ON a.municipio = ap.municipio
              AND ap.rn = 1
        ORDER BY a.total_anual DESC;
    """

    return query_db(sql, tuple(params))