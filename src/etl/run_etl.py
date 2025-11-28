

from src.etl import fetch_hurtos
from src.etl import fetch_violencia_intrafamiliar
from src.etl import fetch_delitos_sexuales
from src.etl.transformaciones import unificar_tablas


def main():
    print("=== Iniciando ETL de seguridad Santander ===")

    print("\n[1/4] Descargando HURTOS...")
    df_h = fetch_hurtos.fetch_hurtos_santander()
    print(f"Hurtos descargados: {len(df_h)} filas")

    print("\n[2/4] Descargando VIOLENCIA INTRAFAMILIAR...")
    df_vif = fetch_violencia_intrafamiliar.fetch_violencia_intrafamiliar_santander()
    print(f"Violencia intrafamiliar: {len(df_vif)} filas")

    print("\n[3/4] Descargando DELITOS SEXUALES...")
    df_ds = fetch_delitos_sexuales.fetch_delitos_sexuales_santander()
    print(f"Delitos sexuales: {len(df_ds)} filas")

    print("\n[4/4] Limpiando y unificando tablas...")
    df_all = unificar_tablas(df_h, df_vif, df_ds)
    print(f"Tabla analítica final: {len(df_all)} filas")

    print("\n=== ETL terminado ===")


if __name__ == "__main__":
    main()
