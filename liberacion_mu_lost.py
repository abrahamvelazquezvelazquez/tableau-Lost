import gspread
from google.oauth2.service_account import Credentials

# Autenticación
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
client = gspread.authorize(creds)

# 1. URL de la Hoja Principal (Lost)
URL_HOJA_PRINCIPAL = "https://docs.google.com/spreadsheets/d/1tLAyayZkAWJ0XtyQWWILutdQ_8sr7rjf1VsXxcAuL4M/edit?gid=0#gid=0"
NOMBRE_PESTAÑA_PRINCIPAL = "Seguimiento"

# 2. URL de la Hoja Externa (Tickets ICQA con la pestaña TC)
URL_HOJA_TC = "https://docs.google.com/spreadsheets/d/1acrZzYBuvEjCQoMqIklzsvIZBfKHSfCo5zMPiNR-h0w/edit?gid=224588725#gid=224588725"
NOMBRE_PESTAÑA_TC = "TC"


def liberacion_mu_lost():
    # Abrir Hoja Principal por URL
    ss_principal = client.open_by_url(URL_HOJA_PRINCIPAL)
    sheet = ss_principal.worksheet(NOMBRE_PESTAÑA_PRINCIPAL)

    # Buscar índices de columnas en Fila 1 de Seguimiento
    encabezados = sheet.row_values(1)
    col_key_idx = 0
    col_inbound_idx = 0

    for idx, header in enumerate(encabezados):
        clean_header = " ".join(str(header).split()).lower()
        if clean_header == "key":
            col_key_idx = idx + 1
        elif clean_header == "inbound":
            col_inbound_idx = idx + 1

    if col_key_idx == 0 or col_inbound_idx == 0:
        print("Error: No se encontró la columna 'Key' o 'Inbound' en la Fila 1 de Seguimiento.")
        return

    # Leer claves locales
    keys_locales = sheet.col_values(col_key_idx)[1:]
    if not keys_locales:
        print("No hay datos en la columna Key para procesar.")
        return

    # Abrir Hoja Externa por URL y seleccionar la pestaña TC
    ss_tc = client.open_by_url(URL_HOJA_TC)
    sheet_tc = ss_tc.worksheet(NOMBRE_PESTAÑA_TC)
    data_ext = sheet_tc.get_all_values()

    if not data_ext:
        print("La pestaña TC no contiene datos.")
        return

    # Mapeo: Columna A (Índice 0) -> Columna C (Índice 2)
    lookup = {}
    for row in data_ext:
        if len(row) > 10:
            llave_ext = str(row[10]).strip()
            val_c = str(row[2]).strip() if len(row) > 2 else ""

            if llave_ext and llave_ext not in lookup:
                lookup[llave_ext] = val_c

    # Cruzar datos
    output_inbound = []
    for item in keys_locales:
        key_val = str(item).strip() if item is not None else ""
        output_inbound.append([lookup.get(key_val, "")])

    # Escribir en la columna "Inbound"
    num_rows = len(keys_locales)
    fila_inicio = 2
    fila_fin = fila_inicio + num_rows - 1

    col_letter = gspread.utils.rowcol_to_a1(1, col_inbound_idx)[:-1]
    range_a1 = f"{col_letter}{fila_inicio}:{col_letter}{fila_fin}"

    sheet.update(values=output_inbound, range_name=range_a1)
    print(f"Se actualizaron {num_rows} filas en la columna Inbound de Liberación MU Lost exitosamente.")


if __name__ == "__main__":
    liberacion_mu_lost()
