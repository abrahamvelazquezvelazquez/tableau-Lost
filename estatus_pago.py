import gspread
from google.oauth2.service_account import Credentials

# Autenticación
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
client = gspread.authorize(creds)

# Configuración de la Hoja Principal
ID_HOJA_PRINCIPAL = "1tLAyayZkAWJ0XtyQWWILutdQ_8sr7rjf1VsXxcAuL4M"
NOMBRE_PESTAÑA_PRINCIPAL = "Seguimiento"


def parse_float(val):
    """Convierte celdas numéricas o de texto a float. Devuelve 0.0 si es nulo o inválido."""
    if val is None:
        return 0.0
    s_val = str(val).strip().replace(",", "")
    if s_val == "" or s_val.lower() == "none" or s_val.lower() == "null":
        return 0.0
    try:
        return float(s_val)
    except ValueError:
        return 0.0


def actualizar_estatus():
    ss_principal = client.open_by_key(ID_HOJA_PRINCIPAL)
    sheet = ss_principal.worksheet(NOMBRE_PESTAÑA_PRINCIPAL)

    # 1. Leer encabezados de la fila 1
    headers = sheet.row_values(1)
    if not headers:
        print("La hoja no contiene encabezados.")
        return

    col_qty_pending = 0
    col_piezas_pagadas = 0
    col_estatus = 0

    for idx, h in enumerate(headers):
        clean_h = " ".join(str(h).split()).lower()
        if clean_h == "qty pending":
            col_qty_pending = idx + 1
        elif clean_h == "piezas pagadas":
            col_piezas_pagadas = idx + 1
        elif clean_h == "estatus":
            col_estatus = idx + 1

    if not (col_qty_pending and col_piezas_pagadas and col_estatus):
        print(
            f"Error: No se encontraron las columnas requeridas. "
            f"(Qty pending: {col_qty_pending}, Piezas pagadas: {col_piezas_pagadas}, Estatus: {col_estatus})"
        )
        return

    # 2. Leer valores de las columnas desde la fila 2
    vals_qty = sheet.col_values(col_qty_pending)[1:]
    vals_pagadas = sheet.col_values(col_piezas_pagadas)[1:]
    vals_estatus_actual = sheet.col_values(col_estatus)[1:]

    num_rows = max(len(vals_qty), len(vals_pagadas), len(vals_estatus_actual))
    if num_rows == 0:
        print("No hay filas para procesar.")
        return

    # Alinear longitudes de las listas
    while len(vals_qty) < num_rows:
        vals_qty.append("")
    while len(vals_pagadas) < num_rows:
        vals_pagadas.append("")
    while len(vals_estatus_actual) < num_rows:
        vals_estatus_actual.append("")

    # 3. Calcular el valor de Estatus solo para las filas "PENDIENTE"
    output_estatus = []
    filas_modificadas = 0

    for i in range(num_rows):
        current_status = str(vals_estatus_actual[i]).strip()

        # Solo se recalculan las filas cuyo estatus actual sea "PENDIENTE"
        if current_status.upper() == "PENDIENTE":
            val_qty = parse_float(vals_qty[i])
            val_pagadas = parse_float(vals_pagadas[i])

            if val_qty >= 1:
                estatus_str = "PENDIENTE"
            else:
                # Qty pending es 0 o vacío
                if val_pagadas >= 1:
                    estatus_str = "PAGADA"
                else:
                    estatus_str = "CONCILIADA"

            if estatus_str != current_status:
                filas_modificadas += 1

            output_estatus.append([estatus_str])
        else:
            # Si dice cualquier otra cosa (PAGADA, CONCILIADA, etc.), se conserva exactamente igual
            output_estatus.append([current_status])

    # 4. Escribir masivamente en la columna Estatus
    fila_inicio = 2
    fila_fin = fila_inicio + num_rows - 1

    col_letter = gspread.utils.rowcol_to_a1(1, col_estatus)[:-1]
    range_a1 = f"{col_letter}{fila_inicio}:{col_letter}{fila_fin}"

    sheet.update(values=output_estatus, range_name=range_a1)
    print(
        f"Proceso finalizado: se revisaron {num_rows} filas. "
        f"Se cambiaron {filas_modificadas} filas que estaban en 'PENDIENTE'."
    )


if __name__ == "__main__":
    actualizar_estatus()
