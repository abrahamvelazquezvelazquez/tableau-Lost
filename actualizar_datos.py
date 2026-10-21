import json
import pandas as pd

# ID de tu hoja de Google Sheets y pestaña
SPREADSHEET_ID = '1tLAyayZkAWJ0XtyQWWILutdQ_8sr7rjf1VsXxcAuL4M'
SHEET_NAME = 'Seguimiento'

# URL de exportación en CSV directo de Google Sheets
url = f'https://docs.google.com/spreadsheets/d/{SPREADSHEET_ID}/gviz/tq?tqx=out:csv&sheet={SHEET_NAME}'

try:
    print("Descargando datos desde Google Sheets...")
    df = pd.read_csv(url)
    
    # Limpieza básica de columnas
    df.fillna('', inplace=True)
    
    # Convertir a estructura JSON
    datos_dict = df.to_dict(orient='records')
    
    # Guardar en un archivo JavaScript para el Dashboard
    with open('datos.js', 'w', encoding='utf-8') as f:
        f.write(f'const DATOS_TABLERO = {json.dumps(datos_dict, ensure_ascii=False, indent=2)};')
        
    print("¡Archivo datos.js actualizado exitosamente!")

except Exception as e:
    print(f"Error al descargar datos: {e}")
