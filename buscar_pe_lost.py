from collections import defaultdict
from datetime import datetime
import re
import gspread
from google.oauth2.service_account import Credentials

# Autenticación
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets",
    "https://www.googleapis.com/auth/drive",
]
creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
client = gspread.authorize(creds)

# 1. Configuración de Hoja Principal (Lost)
URL_HOJA_PRINCIPAL = "https://docs.google.com/spreadsheets/d/1tLAyayZkAWJ0XtyQWWILutdQ_8sr7rjf1VsXxcAuL4M/edit?gid=0#gid=0"
NOMBRE_PESTAÑA_PRINCIPAL = "Seguimiento"

# 2. Configuración de Hoja Externa con la pestaña PE (Tickets ICQA)
URL_HOJA_EXTERNA = "https://docs.google.com/spreadsheets/d/1acrZzYBuvEjCQoMqIklzsvIZBfKHSfCo5zMPiNR-h0w/edit?gid=1973520692#gid=1973520692"
NOMBRE_HOJA_EXTERNA = "PE"


def formatear_fecha(valor_fecha):
    """Limpia y formatea las fechas a dd/mm/YYYY ignorando completamente la hora."""
    if not valor_fecha:
        return ""

    s_fecha = str(valor_fecha).strip()

    # 1. Intentar analizar con varios formatos de fecha (con y sin hora)
    formatos = [
        "%d/%m/%Y %H:%M:%S",    # 13/8/2026 18:49:52 o 01/08/2026 21:04:24
        "%d/%m/%Y %I:%M:%S %p", # 13/8/2026 06:49:52 PM
        "%d/%m/%Y",             # 13/8/2026
        "%Y-%m-%d %H:%M:%S",    # 2026-08-13 18:49:52
        "%Y-%m-%d",             # 2026-08-13
        "%Y/%m/%d",             # 2026/08/13
        "%d-%m-%Y",             # 13-08-2026
    ]

    for fmt in formatos:
        try:
            dt = datetime.strptime(s_fecha, fmt)
            return dt.strftime("%d/%m/%Y")  # Devuelve la fecha formateada sin hora (ej: 01/08/2026)
        except ValueError:
            continue

    # 2. Respaldo (Fallback): Extraer únicamente la fecha mediante expresiones regulares
    match = re.search(r"(\d{1,4}[/-]\d{1,2}[/-]\d{1,4})", s_fecha)
    if match:
        fecha_corta = match.group(1)
        partes = re.split(r"[/-]", fecha_corta)
        if len(partes) == 3:
            # Si el primer elemento es el día/mes
            if len(partes[0]) <= 2 and len(partes[2]) == 4:
                dia, mes, anio = partes[0].zfill(2), partes[1].zfill(2), partes[2]
                return f"{dia}/{mes}/{anio}"
            # Si el año viene al inicio (YYYY-MM-DD)
            elif len(partes[0]) == 4:
                anio, mes, dia = partes[0], partes[1].zfill(2), partes[2].zfill(2)
                return f"{dia}/{mes}/{anio}"

    return s_fecha.split(" ")[0].split("T")[0]


def buscar_pe_lost():
    # Abrir Hoja Principal
    ss_principal = client.open_by_url(URL_HOJA_PRINCIPAL)
    hoja_origen = ss_principal.worksheet(NOMBRE_PESTAÑA_PRINCIPAL)

    # Intentar abrir la pestaña PE (de la hoja externa por URL o del libro principal)
    data_ext = []
    try:
        ss_externa = client.open_by_url(URL_HOJA_EXTERNA)
        hoja_externa = ss_externa.worksheet(NOMBRE_HOJA_EXTERNA)
        data_ext = hoja_externa.get_all_values()
    except Exception as e:
        print(f"Aviso al acceder a hoja externa PE: {e}. Intentando abrir desde hoja principal...")
        try:
            hoja_externa = ss_principal.worksheet(NOMBRE_HOJA_EXTERNA)
            data_ext = hoja_externa.get_all_values()
        except Exception as e2:
            print(f"Error final: No se encontró la pestaña PE: {e2}")
            return

    if len(data_ext) <= 1:
        print("La pestaña PE no contiene datos.")
        return

    # 1. Procesar y consolidar datos de la pestaña PE
    mapa_externo = defaultdict(dict)

    for fila in data_ext[1:]:
        if len(fila) <= 1:
            continue

        llave_busqueda = str(fila[1]).strip()  # Columna B: ISSUE ID (Índice 1)
        if llave_busqueda:
            reg_date = formatear_fecha(fila[13]) if len(fila) > 13 else ""  # Columna N (Índice 13)
            status = fila[16] if len(fila) > 16 else ""      # Columna Q (Índice 16)
            type_inc = fila[17] if len(fila) > 17 else ""    # Columna R (Índice 17)
            site = fila[4] if len(fila) > 4 else ""        # Columna E (Índice 4)
            envio = fila[15] if len(fila) > 15 else ""     # Columna P (Índice 15)
            folio = fila[14] if len(fila) > 14 else ""     # Columna O (Índice 14)

            try:
                fdqty = float(fila[5]) if len(fila) > 5 else 0.0  # Columna F (Índice 5)
            except ValueError:
                fdqty = 0.0

            sub_llave = f"{site}|{envio}|{type_inc}"

            if sub_llave not in mapa_externo[llave_busqueda]:
                mapa_externo[llave_busqueda][sub_llave] = {
                    "regDate": reg_date,
                    "site": site,
                    "envio": envio,
                    "status": status,
                    "type": type_inc,
                    "totalQTY": fdqty,
                    "folio": folio,
                }
            else:
                mapa_externo[llave_busqueda][sub_llave]["totalQTY"] += fdqty

    # 2. Leer llaves de la Columna I en la hoja principal (Columna 9, Fila 2 en adelante)
    col_i_values = hoja_origen.col_values(9)
    issue_keys = col_i_values[1:] if len(col_i_values) > 1 else []

    if not issue_keys:
        print("No hay filas para procesar en la Columna I.")
        return

    # 3. Construir resultados alineados
    paste_r = []
    for key in issue_keys:
        valor_busqueda = str(key).strip()

        if valor_busqueda in mapa_externo:
            lineas = []
            for d in mapa_externo[valor_busqueda].values():
                p_val = d["totalQTY"]
                qty_str = (
                    str(int(p_val)) if p_val.is_integer() else str(round(p_val, 2))
                )

                col_date = str(d["regDate"]).ljust(13)
                col_site = str(d["site"]).ljust(9)
                col_qty = qty_str.ljust(5)
                col_status = str(d["status"]).ljust(9)
                col_type = str(d["type"]).ljust(11)
                col_envio = str(d["envio"]).ljust(13)
                col_folio = str(d["folio"]).ljust(18)

                lineas.append(
                    f"{col_date} {col_site} {col_qty} {col_status} {col_type} {col_envio} {col_folio}"
                )

            paste_r.append(["\n".join(lineas)])
        else:
            paste_r.append([""])

    # 4. Buscar columna de destino por su encabezado en Fila 1
    encabezado_buscado = (
        "Fecha entrega / Site / Piezas / Estado / Tipo inconsistencia / Fecha envio / Folio"
    )
    encabezados = hoja_origen.row_values(1)

    columna_destino = 0
    for idx, header in enumerate(encabezados):
        if " ".join(str(header).split()).lower() == " ".join(encabezado_buscado.split()).lower():
            columna_destino = idx + 1
            break

    if columna_destino == 0:
        print(f"Error: No se encontró la columna con el encabezado: '{encabezado_buscado}'.")
        return

    # 5. Escritura de resultados
    num_rows = len(issue_keys)
    fila_inicio = 2
    fila_fin = fila_inicio + num_rows - 1

    col_letter = gspread.utils.rowcol_to_a1(1, columna_destino)[:-1]
    range_a1 = f"{col_letter}{fila_inicio}:{col_letter}{fila_fin}"

    hoja_origen.update(values=paste_r, range_name=range_a1)
    print(f"Se actualizaron {num_rows} filas en Buscar PE Lost exitosamente.")


if __name__ == "__main__":
    buscar_pe_lost()
