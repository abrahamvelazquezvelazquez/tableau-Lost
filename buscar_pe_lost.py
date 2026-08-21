from collections import defaultdict
import gspread
from google.oauth2.service_account import Credentials

# Autenticación
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
client = gspread.authorize(creds)

# Configuración de Hojas
ID_HOJA_PRINCIPAL = "1tLAyayZkAWJ0XtyQWWILutdQ_8sr7rjf1VsXxcAuL4M"
NOMBRE_PESTAÑA_PRINCIPAL = "Seguimiento"

# Tu hoja propia con el IMPORTRANGE
ID_HOJA_EXTERNA = "1acrZzYBuvEjCQoMqIklzsvIZBfKHSfCo5zMPiNR-h0w"
NOMBRE_HOJA_EXTERNA = "PE"


def buscar_pe_lost():
    ss_principal = client.open_by_key(ID_HOJA_PRINCIPAL)
    hoja_origen = ss_principal.worksheet(NOMBRE_PESTAÑA_PRINCIPAL)

    ss_externa = client.open_by_key(ID_HOJA_EXTERNA)
    hoja_externa = ss_externa.worksheet(NOMBRE_HOJA_EXTERNA)

    datos_ext = hoja_externa.get_all_values()
    if len(datos_ext) <= 1:
        print("La hoja externa no contiene datos.")
        return

    # 1. Procesar y consolidar datos de la pestaña PE
    mapa_externo = defaultdict(dict)

    for fila in datos_ext[1:]:
        if len(fila) < 6:
            continue

        llave_busqueda = str(fila[1]).strip()  # Columna A: ISSUE ID (Índice 0)
        if llave_busqueda:
            reg_date = ""  # En la pestaña PE no hay columna de fecha de registro
            status = fila[2] if len(fila) > 2 else ""      # Columna C: INCONSISTENCIA (Índice 2)
            type_inc = fila[3] if len(fila) > 3 else ""    # Columna D: TIPO_DE_INCONSISTENCIA (Índice 3)
            site = fila[4] if len(fila) > 4 else ""        # Columna E: DESTINO (Índice 4)
            handed = fila[9] if len(fila) > 9 else ""      # Columna J: DESTINO FC (Índice 9)

            try:
                fdqty = float(fila[5]) if len(fila) > 5 else 0.0  # Columna F: CANTIDAD_DE_PIEZAS (Índice 5)
            except ValueError:
                fdqty = 0.0

            sub_llave = f"{site}|{handed}|{type_inc}"

            if sub_llave not in mapa_externo[llave_busqueda]:
                mapa_externo[llave_busqueda][sub_llave] = {
                    "regDate": reg_date,
                    "site": site,
                    "handed": handed,
                    "status": status,
                    "type": type_inc,
                    "totalQTY": fdqty,
                }
            else:
                mapa_externo[llave_busqueda][sub_llave]["totalQTY"] += fdqty

    # 2. Leer llaves de búsqueda de la Columna I en la hoja principal (Columna 9, Fila 2 en adelante)
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

                col_date = str(d["regDate"]).ljust(9)
                col_site = str(d["site"]).ljust(7)
                col_handed = str(d["handed"]).ljust(10)
                col_qty = qty_str.ljust(4)
                col_status = str(d["status"]).ljust(10)
                col_type = str(d["type"])

                lineas.append(
                    f"{col_date} {col_site} {col_handed} {col_qty} {col_status} {col_type}"
                )

            paste_r.append(["\n".join(lineas)])
        else:
            paste_r.append([""])

    # 4. Buscar columna de destino por su encabezado en Fila 1
    encabezado_buscado = (
        "Fecha entrega / Site / Entregó / Piezas / Estado / Tipo inconsistencia"
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
    fila_inicio = 2
    fila_fin = fila_inicio + len(paste_r) - 1

    col_letter = gspread.utils.rowcol_to_a1(1, columna_destino)[:-1]
    range_a1 = f"{col_letter}{fila_inicio}:{col_letter}{fila_fin}"

    hoja_origen.update(values=paste_r, range_name=range_a1)
    print(f"Se actualizaron {len(paste_r)} filas en Buscar PE Shortage exitosamente.")


if __name__ == "__main__":
    buscar_pe_lost()
