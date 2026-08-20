import gspread
from google.oauth2.service_account import Credentials

# Autenticación
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
client = gspread.authorize(creds)

# 1. Configuración de Hojas
ID_LOCAL = "1tLAyayZkAWJ0XtyQWWILutdQ_8sr7rjf1VsXxcAuL4M"
NOMBRE_PESTAÑA_LOCAL = "Seguimiento"

ID_EXTERNO = "1ystFU2UpZJ6-hFwEwF6itSx6AJg5o5mJ_FDKHUd-mic"
NOMBRE_HOJA_ORIGEN = "Extracto 1"


def datos_tableau_lost():
    # Abrir hojas
    ss_actual = client.open_by_key(ID_LOCAL)
    hoja_destino = ss_actual.worksheet(NOMBRE_PESTAÑA_LOCAL)

    ss_origen = client.open_by_key(ID_EXTERNO)
    hoja_origen = ss_origen.worksheet(NOMBRE_HOJA_ORIGEN)

    # 2. Obtener datos de origen
    datos_origen = hoja_origen.get_all_values()
    if len(datos_origen) <= 1:
        print("Extracto 1: La hoja de origen no contiene datos suficientes.")
        return

    filas_origen = datos_origen[1:]  # Omitir fila de encabezados

    # 3. Leer encabezados de la hoja destino (Fila 1)
    encabezados_destino = hoja_destino.row_values(1)
    ultima_columna_destino = len(encabezados_destino)

    if ultima_columna_destino == 0:
        print("La hoja de destino no contiene encabezados.")
        return

    # Crear mapa de encabezados destino -> índice base 0
    mapa_columnas = {}
    for idx, titulo in enumerate(encabezados_destino):
        mapa_columnas[str(titulo).strip().lower()] = idx

    # 4. Definir reglas de mapeo: [Índice Columna Origen] -> "Nombre Encabezado Destino"
    mapeo = [
        {"de": 0, "tituloDestino": "Fecha de LT"},
        {"de": 1, "tituloDestino": "Issue"},
        {"de": 2, "tituloDestino": "Meli"},
        {"de": 3, "tituloDestino": "Título"},
        {"de": 4, "tituloDestino": "Ubicación"},
        {"de": 5, "tituloDestino": "Qty inicial"},
        {"de": 6, "tituloDestino": "Categoria"},
        {"de": 7, "tituloDestino": "HV"},
        {"de": 8, "tituloDestino": "Seller"},
        {"de": 9, "tituloDestino": "USD Inicial"},
    ]

    # 5. Obtener los IDs de "Issue" existentes para evitar duplicados
    col_issue_indice = mapa_columnas.get("issue")
    if col_issue_indice is None:
        print("Error: No se encontró el encabezado 'Issue' en la primera fila de la hoja de destino.")
        return

    col_issue_values = hoja_destino.col_values(col_issue_indice + 1)
    # Convertir todos los IDs existentes a strings limpios dentro de un set para búsqueda rápida O(1)
    ids_destino = set(str(v).strip() for v in col_issue_values)

    # 6. Procesar filas nuevas no duplicadas
    nuevas_filas = []

    for fila in filas_origen:
        if len(fila) <= 1:
            continue

        valor_b = str(fila[1]).strip()  # Columna B (Issue) de la hoja externa

        if valor_b and valor_b not in ids_destino:
            nueva_fila = [""] * ultima_columna_destino

            for regla in mapeo:
                de_idx = regla["de"]
                idx_col_dest = mapa_columnas.get(regla["tituloDestino"].lower())

                if idx_col_dest is not None and de_idx < len(fila):
                    nueva_fila[idx_col_dest] = fila[de_idx]

            nuevas_filas.append(nueva_fila)
            ids_destino.add(valor_b)  # Añadir al set para evitar duplicados en la misma corrida

    # 7. Insertar nuevas filas en la hoja destino
    if nuevas_filas:
        hoja_destino.append_rows(
            nuevas_filas,
            value_input_option="USER_ENTERED",
            insert_data_option="INSERT_ROWS",
        )
        print(f"Extracto 1: Se agregaron {len(nuevas_filas)} nuevas filas.")
    else:
        print("Extracto 1: No se encontraron datos nuevos para importar.")


if __name__ == "__main__":
    datos_tableau_lost()
