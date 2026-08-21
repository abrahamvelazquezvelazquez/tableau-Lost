import gspread
from google.oauth2.service_account import Credentials

# Autenticación
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive"
]
creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
client = gspread.authorize(creds)

# URL de la hoja principal (Lost)
URL_HOJA_PRINCIPAL = "https://docs.google.com/spreadsheets/d/1tLAyayZkAWJ0XtyQWWILutdQ_8sr7rjf1VsXxcAuL4M/edit?gid=0#gid=0"
NOMBRE_PESTAÑA_PRINCIPAL = "Seguimiento"

# URL de tu hoja propia con el IMPORTRANGE (Tickets ICQA)
URL_HOJA_TC = "https://docs.google.com/spreadsheets/d/1acrZzYBuvEjCQoMqIklzsvIZBfKHSfCo5zMPiNR-h0w/edit?gid=224588725#gid=224588725"
NOMBRE_PESTAÑA_TC = "TC"


def liberacion_mu_lost():
    # 1. Abrir libro principal por URL
    ss_principal = client.open_by_url(URL_HOJA_PRINCIPAL)
    sheet = ss_principal.worksheet(NOMBRE_PESTAÑA_PRINCIPAL)

    # Obtener datos locales de Seguimiento (Columnas I y K -> Columnas 9 y 11)
    col_i = sheet.col_values(9)[1:]
    col_k = sheet.col_values(11)[1:]

    num_rows = max(len(col_i), len(col_k))
    if num_rows == 0:
        print("No hay filas para procesar en la hoja principal.")
        return

    while len(col_i) < num_rows:
        col_i.append("")
    while len(col_k) < num_rows:
        col_k.append("")

    # 2. Abrir hoja de Tickets ICQA por URL
    ss_tc = client.open_by_url(URL_HOJA_TC)
    
    sheet_tc = None
    for ws in ss_tc.worksheets():
        if ws.title.strip().lower() == NOMBRE_PESTAÑA_TC.lower():
            sheet_tc = ws
            break

    if not sheet_tc:
        print(f"Error: No se encontró la pestaña '{NOMBRE_PESTAÑA_TC}'.")
        return

    data_ext = sheet_tc.get_all_values()
    if not data_ext:
        print("La pestaña TC no contiene datos.")
        return

    # 3. Crear mapa de búsqueda basado en la estructura de TC:
    # Clave = ML|IS -> Valor = MU (Col E, índice 4)
    lookup = {}
    for row in data_ext:
        val_mu = str(row[4]).strip() if len(row) > 4 else ""  # Col E
        val_is = str(row[2]).strip() if len(row) > 2 else ""  # Col C
        val_ml = str(row[7]).strip() if len(row) > 7 else ""  # Col H

        if val_ml or val_is:
            key = f"{val_ml}|{val_is}"
            if key not in lookup:
                lookup[key] = val_mu

    # 4. Procesar y preparar la salida
    output = []
    for i in range(num_rows):
        val_i = str(col_i[i]).strip()  # Corresponde a ML en hoja principal
        val_k = str(col_k[i]).strip()  # Corresponde a IS en hoja principal

        key = f"{val_i}|{val_k}"
        output.append([lookup.get(key, "")])

    # 5. Escribir resultados en la Columna F (Columna 6) de Seguimiento
    fila_inicio = 2
    fila_fin = fila_inicio + num_rows - 1

    col_letter = gspread.utils.rowcol_to_a1(1, 6)[:-1]
    range_a1 = f"{col_letter}{fila_inicio}:{col_letter}{fila_fin}"

    sheet.update(values=output, range_name=range_a1)
    print(f"Se actualizaron {num_rows} filas en Liberación MU Lost exitosamente.")


if __name__ == "__main__":
    liberacion_mu_lost()
