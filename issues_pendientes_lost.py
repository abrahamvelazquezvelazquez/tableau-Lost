import gspread
from google.oauth2.service_account import Credentials

# Autenticación
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
client = gspread.authorize(creds)

# Configuración de Hojas (ID de Lost)
ID_HOJA_PRINCIPAL = "1tLAyayZkAWJ0XtyQWWILutdQ_8sr7rjf1VsXxcAuL4M"
NOMBRE_PESTAÑA_PRINCIPAL = "Seguimiento"

EXTERNAL_ID = "1eTsJEzOKZls1nQJzz_-lHVyFwdsKouHB-Hi4G0UHksE"
EXTERNAL_SHEET_NAME = "Extracto 1"


def parse_number(val):
    """Convierte un valor de texto a float o int si es numérico

    para evitar el apóstrofe (') al escribir en Google Sheets.
    """
    if val is None or str(val).strip() == "":
        return ""
    try:
        # Elimina comas de separadores de miles o espacios si existieran
        clean_val = str(val).replace(",", "").strip()
        num = float(clean_val)
        return int(num) if num.is_integer() else num
    except ValueError:
        # Si no se puede convertir a número (ej. texto), devuelve el valor original
        return val


def issues_pendientes_lost():
    # 1. Abrir hoja principal y seleccionar pestaña
    ss_principal = client.open_by_key(ID_HOJA_PRINCIPAL)
    sheet = ss_principal.worksheet(NOMBRE_PESTAÑA_PRINCIPAL)

    # Buscar índices de columnas 'MXN Pending' y 'Qty pending' en la fila 1
    encabezados = sheet.row_values(1)
    col_mxn_index = 0
    col_qty_index = 0

    for idx, header in enumerate(encabezados):
        clean_header = " ".join(str(header).split()).lower()
        if clean_header == "mxn pending":
            col_mxn_index = idx + 1
        elif clean_header == "qty pending":
            col_qty_index = idx + 1

    if col_mxn_index == 0 or col_qty_index == 0:
        print(
            "Error: No se encontró uno o ambos encabezados ('MXN Pending', 'Qty pending') en la fila 1."
        )
        return

    # Leer Columna E local (Columna 5) desde la fila 2
    col_e_values = sheet.col_values(5)
    col_i = col_e_values[1:] if len(col_e_values) > 1 else []

    if not col_i:
        print("No hay filas para procesar en la Columna E.")
        return

    # 2. Abrir hoja externa y leer datos
    ext_ss = client.open_by_key(EXTERNAL_ID)
    ext_sheet = ext_ss.worksheet(EXTERNAL_SHEET_NAME)
    data_ext = ext_sheet.get_all_values()

    if len(data_ext) <= 1:
        print("La hoja externa no contiene datos.")
        return

    # Crear mapa de búsqueda
    lookup = {}
    for row in data_ext[1:]:
        if len(row) > 3:
            key = str(row[3]).strip()  # Columna D externa
            if key and key not in lookup:
                col_e_ext = row[5] if len(row) > 5 else ""  # Columna F externa
                col_f_ext = row[6] if len(row) > 6 else ""  # Columna G externa
                lookup[key] = {"colE": col_e_ext, "colF": col_f_ext}

    # 3. Preparar arreglos de resultados parseando números
    output_mxn = []
    output_qty = []

    for item in col_i:
        key = str(item).strip() if item is not None else ""

        if key in lookup:
            match = lookup[key]
            output_mxn.append([parse_number(match["colF"])])
            output_qty.append([parse_number(match["colE"])])
        else:
            output_mxn.append([""])
            output_qty.append([""])

    # 4. Escribir resultados en las columnas correspondientes
    num_rows = len(col_i)
    fila_inicio = 2
    fila_fin = fila_inicio + num_rows - 1

    # MXN Pending
    col_letter_mxn = gspread.utils.rowcol_to_a1(1, col_mxn_index)[:-1]
    range_mxn = f"{col_letter_mxn}{fila_inicio}:{col_letter_mxn}{fila_fin}"
    sheet.update(
        range_name=range_mxn,
        values=output_mxn,
        value_input_option="USER_ENTERED",
    )

    # Qty pending
    col_letter_qty = gspread.utils.rowcol_to_a1(1, col_qty_index)[:-1]
    range_qty = f"{col_letter_qty}{fila_inicio}:{col_letter_qty}{fila_fin}"
    sheet.update(
        range_name=range_qty,
        values=output_qty,
        value_input_option="USER_ENTERED",
    )

    print(
        f"Se actualizaron {num_rows} filas en 'MXN Pending' y 'Qty pending' de Issues Pendientes Lost exitosamente."
    )


if __name__ == "__main__":
    issues_pendientes_lost()
