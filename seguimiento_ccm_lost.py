import gspread
from google.oauth2.service_account import Credentials

# Autenticación
SCOPES = ["https://www.googleapis.com/auth/spreadsheets"]
creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
client = gspread.authorize(creds)

# Configuración de Hojas
ID_LOCAL = "1pNY27z4TuxzqvUHdjxKidO29sbJt5tBZfQDNvBOLh4o"
NOMBRE_PESTAÑA_LOCAL = "Seguimiento"

ID_EXTERNA = "10OuyIzexaTIW-QnZ6Bo-Vkgh6qexjiTySmHDdijA_m8"
NOMBRE_PESTAÑA_EXTERNA = "CCM"


def seguimiento_ccm_lost():
    # 1. Abrir hojas
    ss_local = client.open_by_key(ID_LOCAL)
    hoja_local = ss_local.worksheet(NOMBRE_PESTAÑA_LOCAL)

    ss_externa = client.open_by_key(ID_EXTERNA)
    hoja_externa = ss_externa.worksheet(NOMBRE_PESTAÑA_EXTERNA)

    # 2. Leer encabezados de la fila 1 de la Hoja Local
    encabezados_local = hoja_local.row_values(1)
    encabezados_clean = [str(h).strip().lower() for h in encabezados_local]

    # Buscar índices dinámicos de las columnas (base 1)
    def buscar_columna(nombre):
        nombre_clean = nombre.strip().lower()
        if nombre_clean in encabezados_clean:
            return encabezados_clean.index(nombre_clean) + 1
        return 0

    col_fecha_derivacion = buscar_columna("Fecha de derivación")
    col_folio = buscar_columna("Folio")
    col_derivado = buscar_columna("Derivado")
    col_ccm = buscar_columna("CCM")
    col_determinacion = buscar_columna("Determinación CCM")

    columnas_buscadas = [
        ("Fecha de derivación", col_fecha_derivacion),
        ("Folio", col_folio),
        ("Derivado", col_derivado),
        ("CCM", col_ccm),
        ("Determinación CCM", col_determinacion),
    ]

    faltantes = [nombre for nombre, idx in columnas_buscadas if idx == 0]
    if faltantes:
        print(f"Error: No se encontraron las siguientes columnas en la hoja Local: {', '.join(faltantes)}")
        return

    # Leer Columna E local (Columna 5, Fila 2 en adelante)
    col_e_values = hoja_local.col_values(5)
    col_e = col_e_values[1:] if len(col_e_values) > 1 else []

    if not col_e:
        print("No hay filas para procesar en la Columna E.")
        return

    # 3. Obtener datos de la Hoja Externa (CCM)
    datos_externa = hoja_externa.get_all_values()

    mapa_externo = {}
    if len(datos_externa) > 1:
        for fila in datos_externa[1:]:
            if len(fila) > 3:
                llave_ext = str(fila[3]).strip()  # Columna D (Índice 3)
                if llave_ext and llave_ext not in mapa_externo:
                    verificacion = fila[17] if len(fila) > 17 else ""  # Columna R (Índice 17)
                    fecha = fila[19] if len(fila) > 19 else ""         # Columna T (Índice 19)
                    folio = fila[22] if len(fila) > 22 else ""         # Columna W (Índice 22)
                    comentarios = fila[26] if len(fila) > 26 else ""   # Columna AA (Índice 26)

                    mapa_externo[llave_ext] = {
                        "verificacion": verificacion,
                        "fecha": fecha,
                        "folio": folio,
                        "comentarios": comentarios,
                    }

    # 4. Preparar arreglos independientes para cada columna
    out_fecha = []
    out_folio = []
    out_derivado = []
    out_ccm = []
    out_determinacion = []

    for item in col_e:
        llave_local = str(item).strip() if item is not None else ""

        if llave_local in mapa_externo:
            info = mapa_externo[llave_local]

            out_fecha.append([info["fecha"]])
            out_folio.append([info["folio"]])
            out_ccm.append([info["verificacion"]])
            out_determinacion.append([info["comentarios"]])

            verif_str = str(info["verificacion"]).strip().upper()
            if verif_str in ["TRUE", "SI", "1"]:
                out_derivado.append(["SI"])
            else:
                out_derivado.append(["NO"])
        else:
            out_fecha.append([""])
            out_folio.append([""])
            out_derivado.append(["S/R"])
            out_ccm.append([""])
            out_determinacion.append([""])

    # 5. Escribir resultados en los rangos correspondientes
    num_rows = len(col_e)
    fila_inicio = 2
    fila_fin = fila_inicio + num_rows - 1

    def actualizar_columna(col_idx, valores):
        col_letter = gspread.utils.rowcol_to_a1(1, col_idx)[:-1]
        rango = f"{col_letter}{fila_inicio}:{col_letter}{fila_fin}"
        hoja_local.update(values=valores, range_name=rango)

    actualizar_columna(col_fecha_derivacion, out_fecha)
    actualizar_columna(col_folio, out_folio)
    actualizar_columna(col_derivado, out_derivado)
    actualizar_columna(col_ccm, out_ccm)
    actualizar_columna(col_determinacion, out_determinacion)

    print(f"Se actualizaron {num_rows} filas en Seguimiento CCM Shortage exitosamente.")


if __name__ == "__main__":
    seguimiento_ccm_shortage()
