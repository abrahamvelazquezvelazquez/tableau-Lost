from collections import defaultdict
import gspread
from google.oauth2.service_account import Credentials

# Autenticación
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
client = gspread.authorize(creds)

# 1. Configuración de Hojas (Asegúrate de poner aquí el ID de la hoja principal de Lost si es distinto)
ID_HOJA_PRINCIPAL = "1tLAyayZkAWJ0XtyQWWILutdQ_8sr7rjf1VsXxcAuL4M"
NOMBRE_PESTAÑA_PRINCIPAL = "Seguimiento"

ID_HOJA_EXTERNA = "14a5V1g1TiEA3_fuBCUS0nLZ_QTSHQeGTfbw0anKvgMc"
NOMBRE_HOJA_EXTERNA = "Extracto 1"


def pad(val, length):
    s = str(val) if val is not None else ""
    return s.ljust(length)


def buscar_cg_lost():
    ss_principal = client.open_by_key(ID_HOJA_PRINCIPAL)
    hoja_origen = ss_principal.worksheet(NOMBRE_PESTAÑA_PRINCIPAL)

    ss_externa = client.open_by_key(ID_HOJA_EXTERNA)
    hoja_externa = ss_externa.worksheet(NOMBRE_HOJA_EXTERNA)

    datos_ext = hoja_externa.get_all_values()
    if len(datos_ext) <= 1:
        print("La hoja externa no contiene datos.")
        return

    # 1. Procesar y consolidar datos externos
    mapa_externo = defaultdict(dict)

    for fila in datos_ext[1:]:
        if len(fila) < 7:
            continue

        llave_busqueda = str(fila[4]).strip()  # Columna E (Índice 4)
        if llave_busqueda:
            aging = fila[0]  # Columna A
            site = fila[3]   # Columna D
            tipo = fila[5]   # Columna F

            try:
                piezas = float(fila[6])  # Columna G
            except ValueError:
                piezas = 0.0

            sub_llave = f"{aging}|{site}|{tipo}"

            if sub_llave not in mapa_externo[llave_busqueda]:
                mapa_externo[llave_busqueda][sub_llave] = {
                    "aging": aging,
                    "site": site,
                    "tipo": tipo,
                    "totalPiezas": piezas,
                }
            else:
                mapa_externo[llave_busqueda][sub_llave]["totalPiezas"] += piezas

    # 2. Leer valores de la Columna I en la hoja principal (Columna 9, Fila 2 en adelante)
    col_i_values = hoja_origen.col_values(9)
    rango_origen = col_i_values[1:] if len(col_i_values) > 1 else []

    if not rango_origen:
        print("No hay filas para procesar en la Columna I.")
        return

    resultados_ak = []

    # 3. Construir líneas formateadas
    for valor in rango_origen:
        valor_busqueda = str(valor).strip()

        if valor_busqueda in mapa_externo:
            grupo = mapa_externo[valor_busqueda]
            lineas = []

            for d in grupo.values():
                col_a = pad(d["aging"], 3)
                col_d = pad(d["site"], 6)
                col_f = pad(d["tipo"], 7)

                p_val = d["totalPiezas"]
                p_str = (
                    str(int(p_val)) if p_val.is_integer() else str(round(p_val, 2))
                )
                col_g = pad(p_str, 3)

                lineas.append(f"{col_a} {col_d} {col_f} {col_g}")

            resultados_ak.append(["\n".join(lineas)])
        else:
            resultados_ak.append([""])

    # 4. Buscar columna de destino por encabezado
    primera_fila = hoja_origen.row_values(1)
    columna_destino = 0

    texto_buscado = "Conciliación Global\nAging / Site / Tipo / Piezas"

    # Búsqueda exacta y flexible
    for idx, celda in enumerate(primera_fila):
        celda_str = str(celda)
        if (
            celda_str.replace("\r\n", "\n").replace("\r", "\n").strip()
            == texto_buscado.strip()
        ):
            columna_destino = idx + 1
            break

    if columna_destino == 0:
        for idx, celda in enumerate(primera_fila):
            celda_norm = " ".join(str(celda).split()).lower()
            if (
                "conciliación global" in celda_norm
                and "aging / site / tipo / piezas" in celda_norm
            ):
                columna_destino = idx + 1
                break

    if columna_destino == 0:
        print("Error: No se encontró la columna de destino con el encabezado indicado.")
        return

    # 5. Escribir resultados
    fila_inicio = 2
    fila_fin = fila_inicio + len(resultados_ak) - 1

    col_letter = gspread.utils.rowcol_to_a1(1, columna_destino)[:-1]
    rango_a1 = f"{col_letter}{fila_inicio}:{col_letter}{fila_fin}"

    hoja_origen.update(values=resultados_ak, range_name=rango_a1)
    print(f"Se actualizaron {len(resultados_ak)} filas en Buscar CG Lost exitosamente.")


if __name__ == "__main__":
    buscar_cg_lost()
