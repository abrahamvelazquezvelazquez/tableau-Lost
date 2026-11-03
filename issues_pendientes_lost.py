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
        clean_val = str(val).replace(",", "").strip()
        num = float(clean_val)
        return int(num) if num.is_integer() else num
    except ValueError:
        return val


def issues_pendientes_lost():
    # 1. Abrir hoja principal y seleccionar pestaña
    ss_principal = client.open_by_key(ID_HOJA_PRINCIPAL)
    sheet = ss_principal.worksheet(NOMBRE_PESTAÑA_PRINCIPAL)

    # Buscar índices de columnas 'MXN Pending', 'Qty pending' y 'Estatus' en la fila 1
    encabezados = sheet.row_values(1)
    col_mxn_index = 0
    col_qty_index = 0
    col_estatus_index = 0

    for idx, header in enumerate(encabezados):
        clean_header = " ".join(str(header).split()).lower()
        if clean_header == "mxn pending":
            col_mxn_index = idx + 1
        elif clean_header == "qty pending":
            col_qty_index = idx + 1
        elif clean_header in ["estatus", "status"]:
            col_estatus_index = idx + 1

    # Validar que existan todos los encabezados requeridos
    faltantes = []
    if col_mxn_index == 0:
        faltantes.append("'MXN Pending'")
    if col_qty_index == 0:
        faltantes.append("'Qty pending'")
    if col_estatus_index == 0:
        faltantes.append("'Estatus'")

    if faltantes:
        print(f"Error: No se encontró(aron) el/los encabezado(s): {', '.join(faltantes)} en la fila 1.")
        return

    # Leer Columna E (Columna 5: Issue IDs) desde la fila 2
    col_e_values = sheet.col_values(5)
    col_i = col_e_values[1:] if len(col_e_values) > 1 else []

    if not col_i:
        print("No hay filas para procesar en la Columna E.")
        return

    num_rows = len(col_i)
    fila_inicio = 2
    fila_fin = fila_inicio + num_rows - 1

    # Leer la columna dinámica de Estatus
    col_estatus_values = sheet.col_values(col_estatus_index)
    estatus_list = col_estatus_values[1:] if len(col_estatus_values) > 1 else []

    # Leer los valores existentes en las columnas destino para no sobreescribir lo ya procesado
    col_letter_mxn = gspread.utils.rowcol_to_a1(1, col_mxn_index)[:-1]
    col_letter_qty = gspread.utils.rowcol_to_a1(1, col_qty_index)[:-1]

    existing_mxn_raw = sheet.get(f"{col_letter_mxn}{fila_inicio}:{col_letter_mxn}{fila_fin}")
    existing_qty_raw = sheet.get(f"{col_letter_qty}{fila_inicio}:{col_letter_qty}{fila_fin}")

    # Normalizar listas de valores existentes para que tengan la misma longitud que col_i
    current_mxn = [row[0] if row else "" for row in existing_mxn_raw]
    current_mxn += [""] * (num_rows - len(current_mxn))

    current_qty = [row[0] if row else "" for row in existing_qty_raw]
    current_qty += [""] * (num_rows - len(current_qty))

    # 2. Abrir hoja externa y generar lookup table
    ext_ss = client.open_by_key(EXTERNAL_ID)
    ext_sheet = ext_ss.worksheet(EXTERNAL_SHEET_NAME)
    data_ext = ext_sheet.get_all_values()

    if len(data_ext) <= 1:
        print("La hoja externa no contiene datos.")
        return

    lookup = {}
    for row in data_ext[1:]:
        if len(row) > 3:
            key = str(row[3]).strip()  # Columna D externa
            if key and key not in lookup:
                col_e_ext = row[5] if len(row) > 5 else ""  # Columna F externa
                col_f_ext = row[6] if len(row) > 6 else ""  # Columna G externa
                lookup[key] = {"colE": col_e_ext, "colF": col_f_ext}

    # 3. Procesar resultados respetando los datos existentes
    output_mxn = []
    output_qty = []
    pendientes_procesados = 0

    for idx, item in enumerate(col_i):
        # Tomar el estatus de la columna identificada dinámicamente
        status = str(estatus_list[idx]).strip().upper() if idx < len(estatus_list) else ""

        if status == "PENDIENTE":
            pendientes_procesados += 1
            key = str(item).strip() if item is not None else ""

            if key in lookup:
                match = lookup[key]
                output_mxn.append([parse_number(match["colF"])])
                output_qty.append([parse_number(match["colE"])])
            else:
                # Si está pendiente pero aún no se encuentra en el extracto,
                # mantiene el contenido actual que ya tenía la celda
                output_mxn.append([current_mxn[idx]])
                output_qty.append([current_qty[idx]])
        else:
            # Si no es "PENDIENTE", conserva exactamente el valor previo
            output_mxn.append([current_mxn[idx]])
            output_qty.append([current_qty[idx]])

    # 4. Actualizar columnas completas en
