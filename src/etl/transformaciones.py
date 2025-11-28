from pathlib import Path
import pandas as pd

PROCESSED_DIR = Path("data/processed")
PROCESSED_DIR.mkdir(parents=True, exist_ok=True)

# Columnas finales de la tabla analítica (>= 20 variables)
COLUMNAS_ANALITICAS = [
    "departamento",
    "municipio",
    "fecha_hecho",
    "anio",
    "mes",
    "dia",
    "trimestre",
    "anio_mes",
    "dia_semana",
    "es_fin_de_semana",
    "genero",
    "es_mujer",
    "grupo_etario",
    "grupo_edad_simple",
    "armas_medios",
    "arma_categoria",
    "categoria",
    "subtipo_delito",
    "cantidad",
    "es_zona_metro",
]


# ---------- Helpers comunes ----------

def _estandarizar_campos_base(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpieza básica común a los tres datasets:
    - Normaliza texto
    - Convierte fecha y crea variables de tiempo
    - Convierte numéricos
    - Crea variables derivadas (arma_categoria, grupo_edad_simple, es_mujer, es_zona_metro)
    - Filtra solo departamento SANTANDER (por seguridad)
    """
    df = df.copy()

    # Normalizar texto en campos clave
    for col in ["departamento", "municipio", "armas_medios", "genero", "grupo_etario"]:
        if col in df.columns:
            df[col] = (
                df[col]
                .astype("string")
                .str.strip()
                .str.upper()
            )

    # Filtrar solo SANTANDER (por si llega algo de otros deptos)
    if "departamento" in df.columns:
        df = df[df["departamento"] == "SANTANDER"]

    # fecha_hecho -> datetime (formato colombiano: día/mes/año)
    if "fecha_hecho" in df.columns:
        df["fecha_hecho"] = pd.to_datetime(
            df["fecha_hecho"], errors="coerce", dayfirst=True
        )
        df = df.dropna(subset=["fecha_hecho"])

        df["anio"] = df["fecha_hecho"].dt.year
        df["mes"] = df["fecha_hecho"].dt.month
        df["dia"] = df["fecha_hecho"].dt.day
        df["trimestre"] = df["fecha_hecho"].dt.quarter
        df["anio_mes"] = df["fecha_hecho"].dt.to_period("M").astype(str)
        df["dia_semana"] = df["fecha_hecho"].dt.dayofweek  # 0=lunes, 6=domingo
        df["es_fin_de_semana"] = df["dia_semana"].isin([5, 6]).astype("int8")
    else:
        # Si no existiera, creamos columnas vacías para no romper
        for col in ["anio", "mes", "dia", "trimestre", "anio_mes",
                    "dia_semana", "es_fin_de_semana"]:
            df[col] = pd.NA

    # cantidad numérica
    if "cantidad" in df.columns:
        df["cantidad"] = (
            pd.to_numeric(df["cantidad"], errors="coerce")
            .fillna(0)
            .astype(int)
        )

    # Clasificación de arma
    if "armas_medios" in df.columns:
        def categorizar_arma(v: str) -> str:
            if not isinstance(v, str):
                return "NO_REPORTADO"
            v = v.upper()
            if "ARMA DE FUEGO" in v:
                return "ARMA_DE_FUEGO"
            if "BLANCA" in v or "CORTOPUNZANTE" in v:
                return "ARMA_BLANCA"
            if "CONTUNDENTE" in v:
                return "ARMA_CONTUNDENTE"
            if "EXPLOSIVO" in v or "DINAMITA" in v:
                return "EXPLOSIVO"
            if "SIN EMPLEO DE ARMAS" in v:
                return "SIN_ARMA"
            if "NO REPORTADO" in v:
                return "NO_REPORTADO"
            return "OTRAS"

        df["arma_categoria"] = df["armas_medios"].apply(categorizar_arma)
    else:
        df["arma_categoria"] = pd.NA

    # Grupo etario simplificado
    if "grupo_etario" in df.columns:
        def simplificar_edad(v: str) -> str:
            if not isinstance(v, str):
                return "NO_REPORTADO"
            v = v.upper()
            if "MENORES" in v or "ADOLESC" in v:
                return "MENOR_EDAD"
            if "ADULTOS" in v:
                return "ADULTO"
            if "NO REPORTADO" in v:
                return "NO_REPORTADO"
            return "OTRO"

        df["grupo_edad_simple"] = df["grupo_etario"].apply(simplificar_edad)
    else:
        df["grupo_edad_simple"] = pd.NA

    # es_mujer: 1 mujer, 0 hombre, -1 no reportado
    if "genero" in df.columns:
        def calc_es_mujer(g: str) -> int:
            if not isinstance(g, str):
                return -1
            g = g.upper()
            if "FEMENINO" in g:
                return 1
            if "MASCULINO" in g:
                return 0
            return -1

        df["es_mujer"] = df["genero"].apply(calc_es_mujer).astype("int8")
    else:
        df["es_mujer"] = -1

    # es_zona_metro: área metropolitana de Bucaramanga
    if "municipio" in df.columns:
        def es_metro(m: str) -> int:
            if not isinstance(m, str):
                return 0
            u = m.upper()
            return int(
                ("BUCARAMANGA" in u)
                or ("FLORIDABLANCA" in u)
                or ("GIRÓN" in u)
                or ("GIRON" in u)
                or ("PIEDECUESTA" in u)
                or ("LEBRIJA" in u)
            )

        df["es_zona_metro"] = df["municipio"].apply(es_metro).astype("int8")
    else:
        df["es_zona_metro"] = 0

    return df


def _asegurar_columnas_finales(df: pd.DataFrame) -> pd.DataFrame:
    """
    Se asegura de que todas las columnas de COLUMNAS_ANALITICAS existan.
    Si falta alguna, la crea con NA.
    """
    for col in COLUMNAS_ANALITICAS:
        if col not in df.columns:
            df[col] = pd.NA
    return df[COLUMNAS_ANALITICAS].copy()


# ---------- Limpieza específica por tipo de delito ----------

def limpiar_hurtos(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia el dataset de hurtos y lo deja con el esquema analítico común.
    """
    df = _estandarizar_campos_base(df)

    df["categoria"] = "HURTO"
    # tipo_de_hurto viene solo en este dataset
    if "tipo_de_hurto" in df.columns:
        df["subtipo_delito"] = (
            df["tipo_de_hurto"]
            .astype("string")
            .str.strip()
            .str.upper()
        )
    else:
        df["subtipo_delito"] = "HURTO"

    df_limpio = _asegurar_columnas_finales(df)
    df_limpio.to_csv(PROCESSED_DIR / "hurtos_limpio.csv", index=False)
    return df_limpio


def limpiar_violencia_intrafamiliar(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia el dataset de violencia intrafamiliar.
    No trae columna 'delito', todo el conjunto es violencia intrafamiliar.
    """
    df = _estandarizar_campos_base(df)

    df["categoria"] = "VIOLENCIA_INTRAFAMILIAR"
    df["subtipo_delito"] = "VIOLENCIA_INTRAFAMILIAR"

    df_limpio = _asegurar_columnas_finales(df)
    df_limpio.to_csv(
        PROCESSED_DIR / "violencia_intrafamiliar_limpio.csv", index=False
    )
    return df_limpio


def limpiar_delitos_sexuales(df: pd.DataFrame) -> pd.DataFrame:
    """
    Limpia el dataset de delitos sexuales.
    La columna de detalle es 'delito'.
    """
    df = _estandarizar_campos_base(df)

    df["categoria"] = "DELITOS_SEXUALES"
    if "delito" in df.columns:
        df["subtipo_delito"] = (
            df["delito"]
            .astype("string")
            .str.strip()
            .str.upper()
        )
    else:
        df["subtipo_delito"] = "DELITO_SEXUAL"

    df_limpio = _asegurar_columnas_finales(df)
    df_limpio.to_csv(
        PROCESSED_DIR / "delitos_sexuales_limpio.csv", index=False
    )
    return df_limpio


# ---------- Unificación ----------

def unificar_tablas(df_h: pd.DataFrame,
                    df_vif: pd.DataFrame,
                    df_ds: pd.DataFrame) -> pd.DataFrame:
    """
    Aplica la limpieza específica a cada dataset y los concatena
    en una sola tabla analítica.
    """
    df_h_l = limpiar_hurtos(df_h)
    df_vif_l = limpiar_violencia_intrafamiliar(df_vif)
    df_ds_l = limpiar_delitos_sexuales(df_ds)

    df_all = pd.concat([df_h_l, df_vif_l, df_ds_l], ignore_index=True)

    salida = PROCESSED_DIR / "tabla_analitica_delitos.csv"
    df_all.to_csv(salida, index=False)
    print(f"Tabla analítica guardada en {salida} con {len(df_all)} filas")

    return df_all
