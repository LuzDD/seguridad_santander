

from src.etl import fetch_hurtos
from src.etl import fetch_violencia_intrafamiliar
from src.etl import fetch_delitos_sexuales

def main():
    print("=== HURTOS ===")
    df_h = fetch_hurtos.fetch_hurtos_santander()
    print("Columnas:", list(df_h.columns))
    print(df_h.head(5))

    print("\n=== VIOLENCIA INTRAFAMILIAR ===")
    df_vif = fetch_violencia_intrafamiliar.fetch_violencia_intrafamiliar_santander()
    print("Columnas:", list(df_vif.columns))
    print(df_vif.head(5))

    print("\n=== DELITOS SEXUALES ===")
    df_ds = fetch_delitos_sexuales.fetch_delitos_sexuales_santander()
    print("Columnas:", list(df_ds.columns))
    print(df_ds.head(5))

if __name__ == "__main__":
    main()
