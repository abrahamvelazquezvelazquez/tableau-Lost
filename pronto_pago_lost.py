import gspread
from google.oauth2.service_account import Credentials

# Autenticación
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
client = gspread.authorize(creds)

# Configuración de Hoja Principal
ID_HOJA_PRINCIPAL = "1tLAyayZkAWJ0XtyQWWILutdQ_8sr7rjf1VsXxcAuL4M"
NOMBRE_PESTAÑA_PRINCIPAL = "Seguimiento"

# Hoja externa para pronto_pago
EXT_ID_PRONTO_PAGO = "1lso9kt2z3Tx-YZFlRnxAzKhUd7jmAy45PeqTKvBp2Fc"
EXT_SHEET_PRONTO_PAGO = "Extracto 1"

# Hoja externa para issues_refunded
EXT_ID_REFUNDED = "1eTsJEzOKZls1nQJzz_-lHVyFwdsKouHB-Hi4G0UHksE"
EXT_SHEET_REFUNDED = "pagado"


def issues_refunded_lost(sheet):
    """SE EJECUTA PRIMERO: Procesa la actualización de Piezas pagadas, USD Pagado y Fecha de pago."""
    headers = sheet.row_values(1)
    if not headers:
        return

    col_piezas_pagadas = 0
    col_usd_pagado = 0
    col_fecha_pago = 0

    for idx, h in enumerate(headers):
        clean_h = str(h).strip().lower()
        if clean_h == "piezas pagadas":
            col_piezas_pagadas = idx + 1
        elif clean_h == "usd pagado":
            col_usd_pagado = idx + 1
        elif clean_h == "fecha de pago":
            col_fecha_pago = idx + 1

    if not (col_piezas_pagadas and col_usd_pagado and col_fecha_pago):
        print(
            "No se encontraron una o más columnas requeridas ('Piezas pagadas', 'USD Pagado', 'Fecha de pago')."
        )
        return

    # Leer valores actuales
    c_piezas = sheet.col_values(col_piezas_pagadas)[1:]
    c_usd = sheet.col_values(col_usd_pagado)[1:]
    c_fecha = sheet.col_values(col_fecha_pago)[1:]

    col_e = sheet.col_values(5)[1:]
    num_rows = len(col_e)

    if num_rows == 0:
        return

    while len(c_piezas) < num_rows:
        c_piezas.append("")
    while len(c_usd) < num_rows:
        c_usd.append("")
    while len(c_fecha) < num_rows:
        c_fecha.append("")

    # Leer datos externos de Refunded / Pagado
    ext_ss = client.open_by_key(EXT_ID_REFUNDED)
    ext_sheet = ext_ss.worksheet(EXT_SHEET_REFUNDED)
    data_ext = ext_sheet.get_all_values()

    lookup = {}
    if len(data_ext) > 1:
        for row in data_ext[1:]:
            if len(row) >= 5:
                key = str(row[0]).strip()
                if key and key not in lookup:
                    lookup[key] = {
                        "fechaPago": row[2] if len(row) > 2 else "",
                        "usdPagado": row[3] if len(row) > 3 else "",
                        "piezasPagadas": row[4] if len(row) > 4 else "",
                    }

    output_piezas = []
    output_usd = []
    output_fecha = []

    for i in range(num_rows):
        key = str(col_e[i]).strip()

        if key in lookup:
            match = lookup[key]

            val_piezas = (
                match["piezasPagadas"]
                if str(match["piezasPagadas"]).strip() != ""
                else c_piezas[i]
            )
            val_usd = (
                match["usdPagado"]
                if str(match["usdPagado"]).strip() != ""
                else c_usd[i]
            )
            val_fecha = (
                match["fechaPago"]
                if str(match["fechaPago"]).strip() != ""
                else c_fecha[i]
            )

            output_piezas.append([val_piezas])
            output_usd.append([val_usd])
            output_fecha.append([val_fecha])
        else:
            output_piezas.append([c_piezas[i]])
            output_usd.append([c_usd[i]])
            output_fecha.append([c_fecha[i]])

    fila_inicio = 2
    fila_fin = fila_inicio + num_rows - 1

    # Rango Piezas Pagadas
    col_letter_p = gspread.utils.rowcol_to_a1(1, col_piezas_pagadas)[:-1]
    sheet.update(
        values=output_piezas,
        range_name=f"{col_letter_p}{fila_inicio}:{col_letter_p}{fila_fin}",
    )

    # Rango USD Pagado
    col_letter_u = gspread.utils.rowcol_to_a1(1, col_usd_pagado)[:-1]
    sheet.update(
        values=output_usd,
        range_name=f"{col_letter_u}{fila_inicio}:{col_letter_u}{fila_fin}",
    )

    # Rango Fecha de pago
    col_letter_f = gspread.utils.rowcol_to_a1(1, col_fecha_pago)[:-1]
    sheet.update(
        values=output_fecha,
        range_name=f"{col_letter_f}{fila_inicio}:{col_letter_f}{fila_fin}",
    )

    print("1/2 Issues Refunded Lost ejecutado correctamente.")


def pronto_pago_lost(sheet):
    """SE EJECUTA DESPUÉS: Complementa la Fecha de pago sin sobreescribir celdas ya llenas."""
    headers = sheet.row_values(1)
    if not headers:
        return

    target_header_index = -1
    for idx, h in enumerate(headers):
        if str(h).strip().lower() == "fecha de pago":
            target_header_index = idx + 1
            break

    if target_header_index == -1:
        print("No se encontró la columna 'Fecha de pago'.")
        return

    col_fecha_values = sheet.col_values(target_header_index)
    current_target_values = (
        col_fecha_values[1:] if len(col_fecha_values) > 1 else []
    )

    col_e_values = sheet.col_values(5)
    col_e = col_e_values[1:] if len(col_e_values) > 1 else []

    if not col_e:
        return

    while len(current_target_values) < len(col_e):
        current_target_values.append("")

    ext_ss = client.open_by_key(EXT_ID_PRONTO_PAGO)
    ext_sheet = ext_ss.worksheet(EXT_SHEET_PRONTO_PAGO)
    data_ext = ext_sheet.get_all_values()

    lookup = {}
    if len(data_ext) > 1:
        for row in data_ext[1:]:
            if len(row) >= 2:
                key = str(row[0]).strip()
                if key and key not in lookup:
                    lookup[key] = row[1]

    output = []
    for i, item in enumerate(col_e):
        key = str(item).strip()
        current_val = current_target_values[i]

        if key in lookup and str(lookup[key]).strip() != "":
            output.append([lookup[key] if str(current_val).strip() == "" else current_val])
        else:
            output.append([current_val])

    fila_inicio = 2
    fila_fin = fila_inicio + len(output) - 1
    col_letter = gspread.utils.rowcol_to_a1(1, target_header_index)[:-1]
    range_a1 = f"{col_letter}{fila_inicio}:{col_letter}{fila_fin}"

    sheet.update(values=output, range_name=range_a1)
    print("2/2 Pronto Pago Lost ejecutado correctamente.")


def main():
    ss_principal = client.open_by_key(ID_HOJA_PRINCIPAL)
    sheet = ss_principal.worksheet(NOMBRE_PESTAÑA_PRINCIPAL)

    issues_refunded_lost(sheet)
    pronto_pago_lost(sheet)


if __name__ == "__main__":
    main()
