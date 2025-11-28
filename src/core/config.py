import os

# Dominio de Socrata para datos.gov.co
SOCRATA_DOMAIN = "www.datos.gov.co"

# IDs de los datasets en dato
DATASET_HURTOS = "d4fr-sbn2"
DATASET_VIOLENCIA_INTRAFAMILIAR = "vuyt-mqpw"
DATASET_DELITOS_SEXUALES = "fpe5-yrmw"
# Filtro solo departamento de Santander
DEPARTAMENTO_FILTRO = "SANTANDER"

# Tamaño de página para paginar resultado
CHUNK_SIZE = 50000

# Token de aplicación 
APP_TOKEN = os.getenv("DATOSGOV_APP_TOKEN", None)
