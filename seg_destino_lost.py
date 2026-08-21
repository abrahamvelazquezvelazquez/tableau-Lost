import gspread
from google.oauth2.service_account import Credentials

# Autenticación
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
client = gspread.authorize(creds)

# Configuración de Hojas
ID_LOCAL = "1pNY27z4TuxzqvUHdjxKidO29sbJt5tBZfQDNvBOLh4o"
NOMBRE_PESTAÑA_LOCAL = "Seguimiento"

ID_EXTERNA = "1acrZzYBuvEjCQoMqIklzsvIZBfKHSfCo5zMPiNR-h0w"
NOMBRE_PESTAÑA_EXTERNA = "Comentarios_Destino"


def seg_destino_lost():
    # 1. Abrir hojas
    ss_local = client.open_by_key(ID_LOCAL)
    hoja_local = ss_local.worksheet(NOMBRE_PESTAÑA_LOCAL)

    ss_externa = client.open_by_key(ID_EXTERNA)
    hoja_externa = ss_externa.worksheet(NOMBRE_PESTAÑA_EXTERNA)

    # 2. Leer encabezados de la fila 1 local
    encabezados_local = hoja_local.row_values(1)
    encabezados_clean = [str(h).strip().lower() for h in encabezados_local]

    def buscar_columna(nombre):
        nombre_clean = nombre.strip().lower()
        if nombre_clean in encabezados_clean:
            return encabezados_clean.index(nombre_clean) + 1
        return 0

    col_icqa_origen = buscar_columna("Comentario ICQA origen")
    col_icqa_destino = buscar_columna("Comentario ICQA Destino")
    col_comentario_destino = buscar_columna("Comentario Destino")

    if col_icqa_origen == 0 or col_icqa_destino == 0 or col_comentario_destino == 0:
        print("Error: No se encontró una o más columnas objetivo en la hoja Local.")
        return

    # Leer Columna E local (Columna 5, Fila 2 en adelante)
    col_e_values = hoja_local.col_values(5)
    col_e = col_e_values[1:] if len(col_e_values) > 1 else []

    if not col_e:
        print("No hay filas para procesar en la Columna E.")
        return

    # 3. Leer datos de la Hoja Externa (Pending 2.0)
    datos_externa = hoja_externa.get_all_values()

    mapa_externo = {}
    if len(datos_externa) > 1:
        for fila in datos_externa[1:]:
            if len(fila) > 0:
                llave_b = str(fila[0]).strip()  # Columna A (Índice 0)
                if llave_b and llave_b not in mapa_externo:
                    col_c = fila[23] if len(fila) > 23 else ""  # Columna X (Índice 23)
                    col_d = fila[30] if len(fila) > 30 else ""  # Columna AE (Índice 30)

                    mapa_externo[llave_b] = {"c": col_c, "d": col_d}

    # 4. Preparar arreglos de resultados
    datos_icqa_origen = []
    datos_icqa_destino = []
    datos_comentario_destino = []

    for item in col_e:
        llave_b = str(item).strip() if item is not None else ""

        val_origen = ""
        val_destino = ""
        val_comentario_destino = ""

        if llave_b in mapa_externo:
            info = mapa_externo[llave_b]
            val_origen = info["c"]
            val_destino = info["d"]
            val_comentario_destino = ""

        datos_icqa_origen.append([val_origen])
        datos_icqa_destino.append([val_destino])
        datos_comentario_destino.append([val_comentario_destino])

    # 5. Escribir resultados en los rangos correspondientes
    num_rows = len(col_e)
    fila_inicio = 2
    fila_fin = fila_inicio + num_rows - 1

    def actualizar_columna(col_idx, valores):
        col_letter = gspread.utils.rowcol_to_a1(1, col_idx)[:-1]
        rango = f"{col_letter}{fila_inicio}:{col_letter}{fila_fin}"
        hoja_local.update(values=valores, range_name=rango)

    actualizar_columna(col_icqa_origen, datos_icqa_origen)
    actualizar_columna(col_icqa_destino, datos_icqa_destino)
    actualizar_columna(col_comentario_destino, datos_comentario_destino)

    print(f"Se actualizaron {num_rows} filas en Seg Destino Shortage exitosamente.")


if __name__ == "__main__":
    seg_destino_lost()
