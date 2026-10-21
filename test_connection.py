import gspread
import pandas as pd
from google.oauth2.service_account import Credentials

# Permisos necesarios para lectura en Google Drive y Google Sheets
SCOPES = [
    "https://www.googleapis.com/auth/spreadsheets.readonly",
    "https://www.googleapis.com/auth/drive.readonly"
]

def test_google_sheet_connection():
    try:
        # 1. Cargar credenciales desde el JSON
        print("🔑 Cargando credenciales desde credentials.json...")
        creds = Credentials.from_service_account_file("credentials.json", scopes=SCOPES)
        client = gspread.authorize(creds)
        print("✅ Autenticación exitosa con la cuenta de servicio.")

        # 2. Abrir la hoja por su ID
        sheet_id = "1tLAyayZkAWJ0XtyQWWILutdQ_8sr7rjf1VsXxcAuL4M"
        print(f"📊 Abriendo el documento con ID: {sheet_id}...")
        spreadsheet = client.open_by_key(sheet_id)
        
        # 3. Obtener la primera pestaña
        sheet = spreadsheet.sheet1
        print(f"📄 Conectado a la pestaña: '{sheet.title}'")

        # 4. Leer los primeros registros
        data = sheet.get_all_records()
        
        if not data:
            print("⚠️ El documento está vacío o no contiene registros en formato de tabla con encabezados.")
            return

        df = pd.DataFrame(data)
        
        print("\n🎉 ¡CONEXIÓN EXITOSA!")
        print(f"• Filas obtenidas: {len(df)}")
        print(f"• Columnas detectadas: {list(df.columns)}")
        print("\n--- Primeras 3 filas de la hoja ---")
        print(df.head(3))

    except FileNotFoundError:
        print("\n❌ ERROR: No se encontró el archivo 'credentials.json' en la carpeta actual.")
    except gspread.exceptions.APIError as e:
        print(f"\n❌ ERROR DE API (Google): {e}")
        print("👉 Verifica que las APIs 'Google Sheets API' y 'Google Drive API' estén habilitadas en Google Cloud.")
    except gspread.exceptions.SpreadsheetNotFound:
        print("\n❌ ERROR DE PERMISOS: No se encontró la hoja o la cuenta de servicio no tiene acceso.")
        print("👉 Asegúrate de compartir el documento con: credentials@proyecto-cp-501416.iam.gserviceaccount.com")
    except Exception as e:
        print(f"\n❌ Ocurrió un error inesperado: {e}")

if __name__ == "__main__":
    test_google_sheet_connection()
