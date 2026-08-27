from datetime import datetime
import gspread
from google.oauth2.service_account import Credentials

# Autenticación
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
client = gspread.authorize(creds)

# Configuración de Hoja Principal
# Para Shortage cambia por: "1pNY27z4TuxzqvUHdjxKidO29sbJt5tBZfQDNvBOLh4o"
ID_HOJA_PRINCIPAL = "1tLAyayZkAWJ0XtyQWWILutdQ_8sr7rjf1VsXxcAuL4M"
NOMBRE_PESTAÑA_PRINCIPAL = "Seguimiento"

# 1. Hoja Próximas a pago (Pronto Pago)
EXT_ID_PRONTO_PAGO = "1lso9kt2z3Tx-YZFlRnxAzKhUd7jmAy45PeqTKvBp2Fc"
EXT_SHEET_PRONTO_PAGO = "Extracto 1"

# 2. Hoja Ya Pagadas (Refunded)
EXT_ID_REFUNDED = "1eTsJEzOKZls1nQJzz_-lHVyFwdsKouHB-Hi4G0UHksE"
EXT_SHEET_REFUNDED = "pagado"


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


def limpiar_fecha(valor_fecha):
    """Elimina la hora y deja únicamente la fecha."""
    if not valor_fecha:
        return ""

    s_fecha = str(valor_fecha).strip()

    # Si viene con espacio de hora (ej: "6/09/2026 17:17:21") o 'T' (ISO)
    if " " in s_fecha:
        s_fecha = s_fecha.split(" ")[0]
    elif "T" in s_fecha:
        s_fecha = s_fecha.split("T")[0]

    # Intentar parsear formatos comunes para estandarizar
    formatos = ["%d/%m/%Y", "%m/%d/%Y", "%Y-%m-%d", "%d-%m-%Y", "%Y/%m/%d"]
    for fmt in formatos:
        try:
            dt = datetime.strptime(s_fecha, fmt)
            return dt.strftime("%d/%m/%Y")
        except ValueError:
            continue

    return s_fecha


def procesar_pagos_lost():
    ss_principal = client.open_by_key(ID_HOJA_PRINCIPAL)
    sheet = ss_principal.worksheet(NOMBRE_PESTAÑA_PRINCIPAL)

    # Buscar columnas dinámicamente en Fila 1
    headers = sheet.row_values(1)
    if not headers:
        print("La hoja de destino no contiene encabezados.")
        return

    col_piezas_pagadas = 0
    col_usd_pagado = 0
    col_fecha_pago = 0

    for idx, h in enumerate(headers):
        clean_h = " ".join(str(h).split()).lower()
        if clean_h == "piezas pagadas":
            col_piezas_pagadas = idx + 1
        elif clean_h == "usd pagado":
            col_usd_pagado = idx + 1
        elif clean_h == "fecha de pago":
            col_fecha_pago = idx + 1

    if not (col_piezas_pagadas and col_usd_pagado and col_fecha_pago):
        print(
            "Error: No se encontraron las columnas 'Piezas pagadas', 'USD Pagado' y/o 'Fecha de pago'."
        )
        return

    # Leer Claves (Columna E - Índice 5)
    col_e_values = sheet.col_values(5)
    col_e = col_e_values[1:] if len(col_e_values) > 1 else []
    num_rows = len(col_e)

    if num_rows == 0:
        print("No hay filas para procesar en la Columna E.")
        return

    # Leer valores existentes en la hoja destino para no perder datos previos
    c_piezas = sheet.col_values(col_piezas_pagadas)[1:]
    c_usd = sheet.col_values(col_usd_pagado)[1:]
    c_fecha = sheet.col_values(col_fecha_pago)[1:]

    while len(c_piezas) < num_rows:
        c_piezas.append("")
    while len(c_usd) < num_rows:
        c_usd.append("")
    while len(c_fecha) < num_rows:
        c_fecha.append("")

    # -------------------------------------------------------------
    # PASO 1: CARGAR MAPA 1 - PRÓXIMAS A PAGO (Pronto Pago)
    # -------------------------------------------------------------
    mapa_pronto_pago = {}
    try:
        ss_pronto = client.open_by_key(EXT_ID_PRONTO_PAGO)
        sheet_pronto = ss_pronto.worksheet(EXT_SHEET_PRONTO_PAGO)
        data_pronto = sheet_pronto.get_all_values()

        if len(data_pronto) > 1:
            for row in data_pronto[1:]:
                if len(row) >= 2:
                    key = str(row[0]).strip()
                    val_fecha = limpiar_fecha(row[1])
                    if key and val_fecha and key not in mapa_pronto_pago:
                        mapa_pronto_pago[key] = val_fecha
    except Exception as e:
        print(f"Aviso al cargar Pronto Pago: {e}")

    # -------------------------------------------------------------
    # PASO 2: CARGAR MAPA 2 - YA PAGADAS (Refunded)
    # -------------------------------------------------------------
    mapa_refunded = {}
    try:
        ss_ref = client.open_by_key(EXT_ID_REFUNDED)
        sheet_ref = ss_ref.worksheet(EXT_SHEET_REFUNDED)
        data_ref = sheet_ref.get_all_values()

        if len(data_ref) > 1:
            for row in data_ref[1:]:
                if len(row) >= 5:
                    key = str(row[0]).strip()
                    if key and key not in mapa_refunded:
                        mapa_refunded[key] = {
                            "fechaPago": (
                                limpiar_fecha(row[1]) if len(row) > 1 else ""
                            ),
                            "usdPagado": (
                                str(row[2]).strip() if len(row) > 2 else ""
                            ),
                            "piezasPagadas": (
                                str(row[3]).strip() if len(row) > 3 else ""
                            ),
                        }
    except Exception as e:
        print(f"Aviso al cargar Refunded: {e}")

    # -------------------------------------------------------------
    # PASO 3: MEZCLAR DATOS CON LA REGLA DE PRIORIDAD Y CONVERTIR A NÚMERO
    # -------------------------------------------------------------
    output_piezas = []
    output_usd = []
    output_fecha = []

    for i in range(num_rows):
        key = str(col_e[i]).strip()

        val_piezas = c_piezas[i]
        val_usd = c_usd[i]
        val_fecha = limpiar_fecha(c_fecha[i])

        # 1. Aplicar primero Pronto Pago
        if key in mapa_pronto_pago:
            val_fecha = mapa_pronto_pago[key]

        # 2. Aplicar sobreescritura de Ya Pagados
        if key in mapa_refunded:
            ref = mapa_refunded[key]

            if ref["piezasPagadas"] != "":
                val_piezas = ref["piezasPagadas"]
            if ref["usdPagado"] != "":
                val_usd = ref["usdPagado"]
            if ref["fechaPago"] != "":
                val_fecha = ref["fechaPago"]

        # Parsear valores numéricos antes de agregarlos al array de salida
        output_piezas.append([parse_number(val_piezas)])
        output_usd.append([parse_number(val_usd)])
        output_fecha.append([val_fecha])

    # -------------------------------------------------------------
    # PASO 4: ESCRITURA EN HOJA PRINCIPAL (Con USER_ENTERED)
    # -------------------------------------------------------------
    fila_inicio = 2
    fila_fin = fila_inicio + num_rows - 1

    # Piezas Pagadas
    col_letter_p = gspread.utils.rowcol_to_a1(1, col_piezas_pagadas)[:-1]
    sheet.update(
        range_name=f"{col_letter_p}{fila_inicio}:{col_letter_p}{fila_fin}",
        values=output_piezas,
        value_input_option="USER_ENTERED",
    )

    # USD Pagado
    col_letter_u = gspread.utils.rowcol_to_a1(1, col_usd_pagado)[:-1]
    sheet.update(
        range_name=f"{col_letter_u}{fila_inicio}:{col_letter_u}{fila_fin}",
        values=output_usd,
        value_input_option="USER_ENTERED",
    )

    # Fecha de pago
    col_letter_f = gspread.utils.rowcol_to_a1(1, col_fecha_pago)[:-1]
    sheet.update(
        range_name=f"{col_letter_f}{fila_inicio}:{col_letter_f}{fila_fin}",
        values=output_fecha,
        value_input_option="USER_ENTERED",
    )

    print(
        f"Se actualizaron {num_rows} filas de pagos exitosamente sin formato de hora ni apóstrofes."
    )


if __name__ == "__main__":
    procesar_pagos_lost()
