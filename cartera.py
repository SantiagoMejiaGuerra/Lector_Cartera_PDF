# --- 1. IMPORTACIÓN DE LIBRERÍAS ---
import streamlit as st
import pandas as pd
import numpy as np
import re
import os
from io import BytesIO
import pdfplumber
from PIL import Image

# --- 2. CONFIGURACIÓN INICIAL DE LA PÁGINA ---
st.set_page_config(
    page_title="ValleSalud | Procesador de Facturas",
    page_icon="✨",
    layout="centered",
    initial_sidebar_state="collapsed"

)
st._config.set_option("theme.base", "Dark")

# --- 3. ESTILOS CSS PERSONALIZADOS (SOLO PARA EL BOTÓN) ---
# Se definen las variables de color necesarias para el estilo del botón.
COLOR_AGUA_MARINA = "#01949C"
COLOR_BLANCO = "#FFFFFF"

# Se inyecta un bloque de CSS únicamente para personalizar el botón.
st.markdown(f"""
<style>
    /* Estilo para el botón principal. */
    .stButton>button {{
        border: 2px solid {COLOR_AGUA_MARINA};
        background-color: transparent;
        color: {COLOR_AGUA_MARINA};
        padding: 14px 28px;
        border-radius: 10px;
        font-weight: 700;
        font-size: 1.1em;
        transition: all 0.3s ease-in-out;
        width: 100%;
        margin-top: 20px;
    }}
    /* Efecto al pasar el mouse sobre el botón. */
    .stButton>button:hover {{
        background-color: {COLOR_AGUA_MARINA};
        color: {COLOR_BLANCO};
        border-color: {COLOR_AGUA_MARINA};
        transform: scale(1.02);
        box-shadow: 0 0 15px {COLOR_AGUA_MARINA};
    }}
    /* Efecto al hacer clic en el botón. */
    .stButton>button:active {{
        transform: scale(0.98);
    }}
</style>
""", unsafe_allow_html=True)

# --- 3. CARGA DE DATOS INICIALES ---
@st.cache_data
def charger_entidades():
    try:
        entidades = pd.read_excel("lista_de_clientes.xlsx", sheet_name="Base Clientes")
        entidades.columns = entidades.columns.str.strip()
        return entidades
    except FileNotFoundError:
        st.error("Error: El archivo 'lista_de_clientes.xlsx' no se encontró. Asegúrate de que esté en la misma carpeta.")
        return pd.DataFrame()
    except Exception as e:
        st.error(f"Error al leer el archivo de clientes: {e}")
        return pd.DataFrame()

df_entidades = charger_entidades()

# --- 4. DEFINICIÓN DE FUNCIONES DE PROCESAMIENTO POR ENTIDAD ---
def procesar_axa(archivos, nit, selection_entidad, plan_entidad):
    data = []
    for archivo in archivos:
        df = pd.read_excel(archivo)
        
        columnas_originales = ["Fecha de Pago", "N° Factura", "Valor Pagado Antes de Imp.", "Valor Pagado Despues de Imp."]
        columnas_alt = ["No. FACTURA", "FECHA DE PAGO", "VALOR PAGADO DESPUES DE IMPUESTO ", "VALOR PAGADO ANTES DE IMPUESTO "]
        columnas_alternativas = ["FECHA_PAGO", "N° Factura", "Valor Pagado Antes de Imp.", "Valor Pagado Despues de Imp.", "RTE_FUENTE", "RETE_ICA", "RETE_IVA"]
        
        if all(col in df.columns for col in columnas_originales):
            df = df[columnas_originales]
            df["Retención"] = df["Valor Pagado Antes de Imp."] - df["Valor Pagado Despues de Imp."]
            df["Rete. Servicios"] = round(df["Valor Pagado Antes de Imp."] * 0.02)
            df["ICA"] = df["Retención"] - df["Rete. Servicios"]
            df["IVA"] = 0
            df["VR. FACTURA"] = df["Valor Pagado Antes de Imp."]
            df["VR. BRUTO"] = df["Valor Pagado Antes de Imp."]
            df["DIFERENCIA"] = df["VR. FACTURA"] - df["VR. BRUTO"]
            
        elif all(col in df.columns for col in columnas_alt):
            df = df[columnas_alt].rename(columns={
                "FECHA DE PAGO": "Fecha de Pago",
                "No. FACTURA": "N° Factura",
                "VALOR PAGADO DESPUES DE IMPUESTO ": "Valor Pagado Despues de Imp.",
                "VALOR PAGADO ANTES DE IMPUESTO ":"Valor Pagado Antes de Imp."
            })
            df["Retención"] = df["Valor Pagado Antes de Imp."] - df["Valor Pagado Despues de Imp."]
            df["Rete. Servicios"] = round(df["Valor Pagado Antes de Imp."] * 0.02)
            df["ICA"] = df["Retención"] - df["Rete. Servicios"]
            df["IVA"] = 0
            df["VR. FACTURA"] = df["Valor Pagado Antes de Imp."]
            df["VR. BRUTO"] = df["Valor Pagado Antes de Imp."]
            df["DIFERENCIA"] = df["VR. FACTURA"] - df["VR. BRUTO"]
            
        elif all(col in df.columns for col in columnas_alternativas):
            df["Retención"] = df["Valor Pagado Antes de Imp."] - df["Valor Pagado Despues de Imp."]
            df["VR. FACTURA"] = df["Valor Pagado Antes de Imp."]
            df["VR. BRUTO"] = df["Valor Pagado Antes de Imp."]
            df["DIFERENCIA"] = df["VR. FACTURA"] - df["VR. BRUTO"]
            df = df[columnas_alternativas].rename(columns={
                "FECHA_PAGO": "Fecha de Pago",
                "RTE_FUENTE":"Rete. Servicios",
                "RETE_ICA":"ICA",
                "RETE_IVA":"IVA"
            })
        else:
            st.warning(f"Archivo Excel {archivo.name} no tiene una estructura de columnas reconocida para AXA.")
            continue
        
        df["NIT"] = nit
        df["PLAN"] = plan_entidad
        df["ASEGURADORA"] = selection_entidad
        df["CASO"] = ""
        df["Archivo"] = archivo.name
        df["SEDE"] = ""
        
        df = df.rename(columns={
            "Fecha de Pago": "FECHA",
            "N° Factura": "APLICA A FV",
            "Rete. Servicios": "(-) RETEF",
            "ICA":"(-) ICA",
            "Retención": "SUMA RETENCIONES",
            "Valor Pagado Despues de Imp.": "VR. RECAUDO"
        })
        
        columnas_ordenadas=["SEDE","FECHA", "NIT", "ASEGURADORA", "PLAN", "CASO", "APLICA A FV", "VR. FACTURA", "VR. BRUTO", "(-) RETEF", "(-) ICA", "IVA", "SUMA RETENCIONES", "VR. RECAUDO", "DIFERENCIA","Archivo"]
        df = df.reindex(columns=columnas_ordenadas, fill_value="")
        data.append(df)
    return pd.concat(data, ignore_index=True) if data else pd.DataFrame()

def procesar_adres(archivos, nit, selection_entidad, plan_entidad):
    data = []
    for archivo in archivos:
        adres = pd.read_excel(archivo, sheet_name="Hoja1",header=5)
        adres = adres.drop(columns=[col for col in adres.columns if "Unnamed" in col], errors='ignore')
        adres= adres[["Numero Paquete", "Factura", "Valor Reclamado", "Valor aprobado", "Valor glosado","Servicios médicos", "Honorarios", "Compras"]]
        adres["Retencion"] = (adres["Servicios médicos"]*0.02) + (adres["Honorarios"]*0.11) + (adres["Compras"] * 0.025)
        adres["Neto"] = adres["Valor aprobado"] - adres["Retencion"]
        
        adres["NIT"] = nit
        adres["PLAN"] = plan_entidad
        adres["ASEGURADORA"] = selection_entidad
        adres["FECHA"] = ""
        adres["CASO"] = ""
        adres["(-) RETEF"] = 0
        adres["(-) ICA"] = 0
        adres["IVA"] = 0
        adres["Archivo"] = archivo.name
        adres["SEDE"] = ""
        adres["DIFERENCIA"] = adres["Valor Reclamado"] - adres["Valor aprobado"]
        
        adres=adres.rename(columns={
            "Factura": "APLICA A FV",
            "Valor Reclamado": "VR. FACTURA",
            "Valor aprobado": "VR. BRUTO",
            "Retencion": "SUMA RETENCIONES",
            "Neto": "VR. RECAUDADO"
        })
        
        columnas_ordenadas =["SEDE","FECHA", "NIT", "ASEGURADORA", "PLAN", "CASO", "APLICA A FV", "VR. FACTURA", "VR. BRUTO", "(-) RETEF", "(-) ICA", "IVA", "SUMA RETENCIONES", "VR. RECAUDADO", "DIFERENCIA", "Archivo"]
        adres = adres.reindex(columns=columnas_ordenadas, fill_value="")
        data.append(adres)
    return pd.concat(data, ignore_index=True)

def procesar_previsora(archivos, nit,selection_entidad, plan_entidad):
    data = []
    for archivo in archivos:
        df_init = pd.read_excel(archivo, header = None, nrows=10)
        
        if (df_init == "RECLAMANTE:").any().any():
            df = pd.read_excel(archivo, header=4)
            fecha_transferencia = df.loc[df['RECLAMANTE:'] == "FECHA DE TRANSFERENCIA O DE CHEQUE:", df.columns[1]].values[0]
            df["fecha_transferencia"] = pd.NA
            df.at[3, "fecha_transferencia"] = "FECHA TRANSFERENCIA"
            df.loc[4:, "fecha_transferencia"] = fecha_transferencia
            df.columns = df.iloc[3]
            df = df.iloc[4:].reset_index(drop=True)
            df = df[["FECHA TRANSFERENCIA","N°. Doc. de cobro", " Valor Reclamado", "Valor pagado", "Valor Objetado", "I.V.A.", "Retención en la fuente", "I.C.A. - ImP. Ind y Ccio"]]
            df.dropna(inplace= True)
            
            df["NIT"] = nit
            df["PLAN"] = plan_entidad
            df["ASEGURADORA"] = selection_entidad
            df["CASO"] = ""
            df["Archivo"] = archivo.name
            df["SUMA RETENCIONES"] = df["Retención en la fuente"] + df["I.C.A. - ImP. Ind y Ccio"]
            df["VR. RECAUDADO"] = df["Valor pagado"] - df["SUMA RETENCIONES"]
            df["SEDE"] = ""
            df["DIFERENCIA"] = df[" Valor Reclamado"] - df["Valor pagado"]
            
            df = df.rename(columns={
                "FECHA TRANSFERENCIA": "FECHA",
                "N°. Doc. de cobro":"APLICA A FV",
                "I.V.A": "IVA",
                "Retención en la fuente":"(-) RETEF",
                "I.C.A. - ImP. Ind y Ccio": "(-) ICA",
                " Valor Reclamado": "VR. FACTURA",
                "Valor pagado": "VR. BRUTO"
            })
        else :
            df = pd.read_excel(archivo)
            df = df[["Fecha", "Factura", "Valor_Factura", "Este_Pago", "ImpValorIVA", "ImpValorReteICA", "ImpValorReteFuente"]]
            
            df["NIT"] = nit
            df["PLAN"] = plan_entidad
            df["ASEGURADORA"] = selection_entidad
            df["CASO"] = ""
            df["Archivo"] = archivo.name
            df["SUMA RETENCIONES"] = df["ImpValorReteFuente"] + df["ImpValorReteICA"]
            df["VR. RECAUDADO"] = df["Este_Pago"] - df["SUMA RETENCIONES"]
            df["SEDE"] = ""
            df["DIFERENCIA"] = df["Valor_Factura"] - df["Este_Pago"]
            
            df =df.rename(columns={
                "Fecha":"FECHA",
                "Factura": "APLICA A FV",
                "ImpValorIVA": "IVA",
                "ImpValorReteICA": "(-) ICA",
                "ImpValorReteFuente": "(-) RETEF",
                "Este_Pago": "VR. BRUTO",
                "Valor_Factura": "VR. FACTURA"
            })
            
        columnas_ordenadas =["SEDE","FECHA", "NIT", "ASEGURADORA", "PLAN", "CASO", "APLICA A FV", "VR. FACTURA", "VR. BRUTO", "(-) RETEF", "(-) ICA", "IVA", "SUMA RETENCIONES", "VR. RECAUDADO", "DIFERENCIA", "Archivo"]
        df = df.reindex(columns=columnas_ordenadas, fill_value="")
        data.append(df)
    return pd.concat(data, ignore_index=True)

def procesar_mundial(archivos, nit, selection_entidad, plan_entidad):
    data = []
    for archivo in archivos:
        df = pd.read_excel(archivo, header=5)
        df = df[["FECHA PAGO", "FACTURA", "VALOR RECLAMADO", "VALOR APROBADO", "Rete-Fuente", "ICA"]]
        df["SUMA RETENCIONES"] = df["Rete-Fuente"] + df["ICA"]
        df["VR. RECAUDADO"] = df["VALOR APROBADO"] - df["SUMA RETENCIONES"]
        df["NIT"] = nit
        df["PLAN"] = plan_entidad
        df["ASEGURADORA"] = selection_entidad
        df["CASO"] = ""
        df["Archivo"] = archivo.name
        df["IVA"] = 0
        df["SEDE"] = ""
        df["DIFERENCIA"] = df["VALOR RECLAMADO"] - df["VALOR APROBADO"]
        df = df.rename(columns={
            "FECHA PAGO": "FECHA",
            "FACTURA":"APLICA A FV",
            "VALOR RECLAMADO":"VR. FACTURA",
            "VALOR APROBADO":"VR. BRUTO",
            "Rete-Fuente":"(-) RETEF",
            "ICA": "(-) ICA",
            })
        columnas_ordenadas=["SEDE", "FECHA", "NIT", "ASEGURADORA", "PLAN", "CASO", "APLICA A FV", "VR. FACTURA", "VR. BRUTO", "(-) RETEF", "(-) ICA", "IVA", "SUMA RETENCIONES", "VR. RECAUDADO", "DIFERENCIA", "Archivo"]
        df = df.reindex(columns=columnas_ordenadas, fill_value="")
        data.append(df)
    return pd.concat(data, ignore_index=True)

def procesar_sura(archivos, nit, selection_entidad, plan_entidad):
    data = []
    columns_requires= ["Factura", "Fecha Consignacion", "Vlr Factura", "Vlr Orden de Pago", "RteFete", "RteICA", "RteIVA", "Vlr Consignado"]
    column_name_mapping = {
            "Fecha Consignacion":"FECHA",
            "Factura":"APLICA A FV",
            "Vlr Factura":"VR. FACTURA",
            "RteFete": "(-) RETEF",
            "RteICA": "(-) ICA",
            "RteIVA":"IVA",
            "Vlr Consignado":"VR. RECAUDADO"
        }
    for archivo in archivos:
        if archivo.name.lower().endswith("csv"):
            df = pd.read_csv(archivo, encoding='latin-1', sep=";", header=1, index_col=False)
        else: 
            archivo.seek(0)
            df = pd.read_excel(archivo, header=None)
            header_row = None
            for idx, row in df.iterrows():
                clean_row= [str(cell).strip().lower() for cell in row.fillna('')]
                if 'expediente' in clean_row:
                    header_row = idx
                    break
            if header_row is None:
                header_row = df.dropna(how='all').index[0]
            archivo.seek(0)
            df = pd.read_excel(archivo, header=header_row)
        df.columns = df.columns.astype(str).str.strip()
        missing_cols = [col for col in columns_requires if col not in df.columns]
        if missing_cols:
            st.error(f"Archivo {archivo.name}: Faltan columnas: {', '.join(missing_cols)}")
            st.write("Columnas encontradas:", df.columns.tolist())
            continue
        df = df.rename(columns=column_name_mapping)
        df["SUMA RETENCIONES"] = df["(-) RETEF"].fillna(0) + df["(-) ICA"].fillna(0)
        df["NIT"] = nit
        df["PLAN"] = plan_entidad
        df["ASEGURADORA"] = selection_entidad
        df["CASO"] = ""
        df["ARCHIVOS"] = archivo.name
        df["FECHA"] = pd.to_datetime(df["FECHA"], format="%Y%m%d").dt.date
        df["VR. BRUTO"] = df["VR. FACTURA"]
        df["SEDE"] = ""
        df["DIFERENCIA"] = df["VR. FACTURA"] - df["VR. BRUTO"]
        columnas_ordenadas = ["SEDE","FECHA", "NIT", "ASEGURADORA", "PLAN", "CASO", "APLICA A FV", "VR. FACTURA", "VR. BRUTO", "(-) RETEF", "(-) ICA", "IVA", "SUMA RETENCIONES", "VR. RECAUDADO", "DIFERENCIA", "ARCHIVOS"]
        data.append(df[columnas_ordenadas])
    return pd.concat(data, ignore_index=True) if data else pd.DataFrame()

def procesar_liberty(archivos, nit, selection_entidad, plan_entidad):
    data = []
    for archivo in archivos:
        nombre_archivo = archivo.name
        if nombre_archivo.lower().endswith(('.xls', '.xlsx')):
            df = pd.read_excel(archivo)
        elif nombre_archivo.lower().endswith('.csv'):
            df = pd.read_csv(archivo)
        else:
            continue
        if nombre_archivo.lower().endswith('.csv'):
            rename_columns = {"Fecha_Pago": "FECHA GIRO", "No_Factura": "NRO FACTURA", "Valor_Pagado": "VALOR PAGADO", "Valor_Ret":"VALOR RETEFUENTE", "Valor_Base":"VALOR LIQUIDADO"}
        else:
            rename_columns = {"FECHA GIRO": "FECHA GIRO" ,"NRO FACTURA": "NRO FACTURA", "VALOR LIQUIDADO": "VALOR LIQUIDADO", "VALOR RETEFUENTE":"VALOR RETEFUENTE", "VALOR PAGADO" : "VALOR PAGADO"}
        df.rename(columns=rename_columns, inplace=True)
        df["NIT"] = nit
        df["PLAN"] = plan_entidad
        df["ASEGURADORA"] = selection_entidad
        df["CASO"] = ""
        df["VR. BRUTO"] = df["VALOR LIQUIDADO"]
        df["IVA"] = 0
        df["(-) ICA"] = 0
        df["SUMA RETENCIONES"] = df["VALOR RETEFUENTE"] + df["(-) ICA"]
        df["ARCHIVO"] = archivo.name
        df["SEDE"] = ""
        df["DIFERENCIA"] = df["VALOR LIQUIDADO"] - df["VR. BRUTO"]
        df = df.rename(columns={
            "FECHA GIRO": "FECHA",
            "NRO FACTURA":"APLICA A FV",
            "VALOR LIQUIDADO":"VR. FACTURA",
            "VALOR RETEFUENTE":"(-) RETEF",
            "VALOR PAGADO":"VR. RECAUDADO"
        })
        columnas_ordenadas = ["SEDE","FECHA", "NIT", "ASEGURADORA", "PLAN", "CASO", "APLICA A FV", "VR. FACTURA", "VR. BRUTO", "(-) RETEF", "(-) ICA", "IVA", "SUMA RETENCIONES", "VR. RECAUDADO", "DIFERENCIA","ARCHIVO"]
        df = df.reindex(columns=columnas_ordenadas, fill_value="")
        data.append(df)
    return pd.concat(data, ignore_index=True)

def procesar_bolivar(archivos, nit, selection_entidad, plan_entidad):
    data = []
    for archivo in archivos:
        nombre_archivo = archivo.name
        if nombre_archivo.lower().endswith(('.xls', '.xlsx')):
            df = pd.read_excel(archivo)
        elif nombre_archivo.lower().endswith('.csv'):
            df = pd.read_csv(archivo, encoding='latin-1', sep=";")
            df["Valor pago"] = (df["Valor pago"].astype(str).str.replace("$", "", regex=False).str.replace(",", "", regex=False).astype(float).round(0).astype(int))
            split_data = df["Detalles"].str.split(n=1, expand=True)
            df["Detalle"] = split_data[0]
        else:
            continue
        if nombre_archivo.lower().endswith('.csv'):
            columnas = ["Fecha de Pago", "Rte. ICA", "Rte Fuente", "Valor pago", "Detalle"]
        else:
            columnas = ["Fecha de Pago", "Detalle", "Rte. ICA", "Rte Fuente", "Valor pago"]
        df = df[columnas]
        df["NIT"]=nit
        df["PLAN"]=plan_entidad
        df["ASEGURADORA"] =selection_entidad
        df["CASO"] = ""
        df["VR. FACTURA"] = 0
        df["IVA"] = 0
        df["ARCHIVO"] = archivo.name
        df["VR. BRUTO"] = df["Valor pago"] / 0.98
        df["(-) RETEF"] = round(df["VR. BRUTO"] * 0.02)
        df["SUMA RETENCIONES"] = df["(-) RETEF"] + df["Rte. ICA"]
        df["SEDE"] = ""
        df["DIFERENCIA"] = df["VR. FACTURA"] - df["VR. BRUTO"]
        df = df.rename(columns={
            "Fecha de Pago":"FECHA",
            "Detalle":"APLICA A FV",
            "Valor pago":"VR. RECAUDADO",
            "Rte. ICA":"(-) ICA",
        })
        columnas_ordenadas=["SEDE","FECHA", "NIT", "ASEGURADORA", "PLAN","CASO", "APLICA A FV", "VR. FACTURA","VR. BRUTO", "(-) RETEF", "(-) ICA", "IVA", "SUMA RETENCIONES", "VR. RECAUDADO", "DIFERENCIA", "ARCHIVO"]
        df = df.reindex(columns=columnas_ordenadas, fill_value="")
        data.append(df)
    return pd.concat(data, ignore_index=True)

def procesar_nueva_eps(archivos, nit, selection_entidad, plan_entidad):
    data = []
    for archivo in archivos:
        df = pd.read_excel(archivo)
        df = df[["Fecha Legalización", "Número Factura", "Valor Aplicación"]]
        df["NIT"] = nit
        df["PLAN"] = plan_entidad
        df["ASEGURADORA"] = selection_entidad
        df["CASO"] = ""
        df["(-) RETEF"] = df["Valor Aplicación"] * 0.02
    return pd.DataFrame(data)

def procesar_seg_estado(archivos, nit, selection_entidad, plan_entidad):
    data = []
    for pdf_file in archivos:
        try:
            with pdfplumber.open(pdf_file) as pdf:
                total_text = ""
                for i, pagina in enumerate(pdf.pages[:2]):
                    text = pagina.extract_text() or ""
                    total_text += f"\n{text}"
                    if i == 0 and not re.search(r"www\.sis\.co[\.,]", text, re.IGNORECASE):
                        break
                facturas = []
                if re.search(r"www\.sis\.co[\.,]", total_text, re.IGNORECASE):
                    fecha_doc = None
                    fecha = r"""(?:Bogotá, D\.C\.,\s*)?(\d{1,2}\s+de\s+[a-z]+\s+de\s+\d{4})|(Fecha\s*[^:]*:\s*(\d{2}-\d{2}-\d{4}))|(\b\d{1,2}[/-]\d{1,2}[/-]\d{4}\b)"""
                    match_fecha = re.search(fecha, total_text, re.IGNORECASE | re.VERBOSE)
                    if match_fecha:
                        try:
                            if match_fecha.group(1):
                                day, month, year = re.match(r"(\d{1,2})\s+de\s+(\w+)\s+de\s+(\d{4})", match_fecha.group(1)).groups()
                                meses = {'enero': '01', 'febrero': '02', 'marzo': '03', 'abril': '04', 'mayo': '05', 'junio': '06', 'julio': '07', 'agosto': '08', 'septiembre': '09', 'octubre': '10', 'noviembre': '11', 'diciembre': '12'}
                                fecha_doc = f"{day.zfill(2)}/{meses[month.lower()]}/{year}"
                            elif match_fecha.group(3):
                                day, month, year = match_fecha.group(3).split('-')
                                fecha_doc = f"{day}/{month}/{year}"
                            elif match_fecha.group(4):
                                separador = '/' if '/' in match_fecha.group(4) else '-'
                                day, month, year = match_fecha.group(4).split(separador)
                                fecha_doc = f"{day}/{month}/{year}"
                        except Exception as e:
                            print(f"Error procesando fecha : {str(e)}")
                    matches = re.findall(r"(\d{5,8})\s+\$\s*([\d.,]+)\s+\$\s*([\d.,]+)", total_text)
                    for match in matches:
                        try:
                            valor_bruto = float(match[1].replace(".", "").replace(",", "."))
                            valor_neto = float(match[2].replace(".", "").replace(",", "."))
                            facturas.append({
                                "SEDE": "", "FECHA": fecha_doc, "NIT":nit, "ASEGURADORA": selection_entidad, "PLAN": plan_entidad, "CASO": "", "APLICA FV": match[0], "VR. FACTURA": 0, "VR. BRUTO":valor_bruto, "(-) RETEF": round(valor_bruto * 0.02, 2), "(-) ICA":round(valor_bruto * 0.0066), "IVA": 0, "SUMA RETENCIONES":round((valor_bruto *0.02) + (valor_bruto * 0.0066)), "VR. RECAUDADO": valor_neto, "DIFERENCIA": 0 - valor_bruto, "Archivo": pdf_file.name
                            })
                        except Exception as e:
                            print(f"Error en factura {match}: {str(e)}")
                    data.extend(facturas)
        except Exception as e:
            print(f"Error procesando {pdf_file.name}: {str(e)}")
            continue
    return pd.DataFrame(data) if data else pd.DataFrame()

def procesar_equidad(archivos, nit, selection_entidad, plan_entidad):
    data = []
    for pdf_file in archivos:
        try:
            with pdfplumber.open(pdf_file) as pdf:
                total_text = "\n".join([page.extract_text() or "" for page in pdf.pages])
                fecha_match = re.search(r"Fecha:\s*(\d{2}\.\d{2}\.\d{4})", total_text)
                fecha = fecha_match.group(1).replace(".", "/") if fecha_match else "Fecha no Econtrada"
                patron_facturas = r"""(\d{10})\D+(\d{4})\D+(\w{2})\D+(\d+)\D+(\d+)\D+(\d+)\D+(\S+)\D+(\d+)\D+([-\d.,]+)"""
                facturas = re.findall(patron_facturas, total_text, re.VERBOSE)
                for factura in facturas:
                    try:
                        neto_str= factura[8].replace(".","").replace(",", ".").replace("-", "")
                        neto_pagar = float(neto_str)
                        bruto = neto_pagar / 0.98 if 0.98 !=0 else 0
                        data.append({
                            "SEDE": "", "FECHA": fecha, "NIT": nit, "ASEGURADORA":selection_entidad, "PLAN": plan_entidad, "CASO":"", "APLICA FV": factura[7], "VR. FACTURA": 0, "VR. BRUTO": bruto, "(-) RETEF": round(bruto * 0.02), "(-) ICA":0, "IVA": 0, "SUMA RETENCIONES": round(bruto * 0.02), "VR. RECAUDADO": neto_pagar, "DIFERENCIA": 0 - bruto, "Archivo": pdf_file.name
                        })
                    except Exception as e:
                        print(f"Error procesando factura {factura}: {str(e)}")
        except Exception as e:
            print(f"Error procesando {pdf_file.name}: {str(e)}")
    return pd.DataFrame(data) if data else pd.DataFrame()

# --- 6. DICCIONARIO DE MAPEADO ---
funcion_procesamiento = {
    "AXA COLPATRIA SEGUROS SA": procesar_axa,
    "AXA COLPATRIA SEGUROS DE VIDA SA": procesar_axa,
    "AXA COLPATRIA MEDICINA PREPAGADA": procesar_axa,
    "ADMINISTRADORA DE LOS RECURSOS DEL SISTEMA GENERAL DE SEGURIDAD SOCIAL EN SALUD - ADRES":procesar_adres,
    "LA PREVISORA SA COMPAÑÍA DE SEGUROS":procesar_previsora,
    "FIDEICOMISOS PATRIMONIOS AUTÓNOMOS FIDUCIARIA LA PREVISORA S.A.": procesar_previsora,
    "LA PREVISORA S A COMPANIA DE SEGURO": procesar_previsora,
    "COMPAÑIA MUNDIAL DE SEGUROS SA": procesar_mundial,
    "SEGUROS GENERALES SURAMERICANA SA": procesar_sura,
    "EPS SURAMERICANA SA": procesar_sura,
    "EPS Y MEDICINA PREPAGADA SURAMETICANA S A":procesar_sura,
    "SEGUROS DE VIDA SURAMERICANA SA": procesar_sura,
    "LIBERTY SEGUROS SA": procesar_liberty,
    "LIBERTY SEGUROS DE VIDA SA": procesar_liberty,
    "SEGUROS COMERCIALES BOLIVAR": procesar_bolivar,
    "ARL SEGUROS BOLIVAR":procesar_bolivar,
    "SEGUROS DEL ESTADO SA":procesar_seg_estado,
    "SEGUROS DE VIDA DEL ESTADO S A":procesar_seg_estado,
    "LA EQUIDAD SEGUROS GENERALES":procesar_equidad,
    "LA EQUIDAD SEGUROS DE VIDA ORGANISMO CORPORATIVO": procesar_equidad
}

# --- 7. CONSTRUCCIÓN DE LA INTERFAZ DE USUARIO (UI) ---
with st.container():
    col1, col2, col3 = st.columns([1, 2, 1])
    with col2:
        try:
            logo = Image.open("LOGO_RED_SLOGM-02.png")
            st.image(logo, use_container_width=True)
        except FileNotFoundError:
            st.warning("Logo 'LOGO_RED_SLOGM-02.png' no encontrado.")

st.title("Plataforma de Procesamiento de Facturas")
st.markdown("<p style='text-align: center; color: #AAAAAA;'>Una solución inteligente para la gestión de cartera de ValleSalud</p>", unsafe_allow_html=True)

with st.container(border=True):
    st.header("1. Configuración del Proceso")

    if not df_entidades.empty:
        planes_dispo = df_entidades["Plan"].unique().tolist()
        entidades_dispo = df_entidades["Razon Social"].unique().tolist()

        selection_plan = st.selectbox("Selecciona el Plan:", ["Todos"] + planes_dispo, key="select_plan")

        if selection_plan != "Todos":
            entidades_filtradas = df_entidades[df_entidades["Plan"] == selection_plan]["Razon Social"].unique().tolist()
        else:
            entidades_filtradas = entidades_dispo
        
        selection_entidad = st.selectbox("Seleccione la Entidad:", ["Seleccionar..."] + entidades_filtradas, key="select_entidad")

        nit = None
        plan_entidad = None
        if selection_entidad != "Seleccionar...":
            info_entidad = df_entidades[df_entidades["Razon Social"] == selection_entidad].iloc[0]
            nit = info_entidad["Nit"]
            plan_entidad = info_entidad["Plan"]
            st.info(f"**NIT seleccionado:** {nit} | **Plan:** {plan_entidad}")
    else:
        st.warning("No se pudieron cargar las entidades. La selección está deshabilitada.")
        selection_entidad = "Seleccionar..."

with st.container(border=True):
    st.header("2. Carga y Procesamiento")

    file_upload = st.file_uploader(
        "Arrastra o selecciona los archivos a procesar (PDF, XLSX, CSV)",
        type=["pdf", "xlsx", "csv", "xls"],
        accept_multiple_files=True
    )

    df_final = None
    
    if st.button("✨ ¡Iniciar Procesamiento!", key="procesar"):
        if file_upload and selection_entidad != "Seleccionar..." and selection_entidad in funcion_procesamiento:
            with st.spinner(f"Analizando y procesando {len(file_upload)} archivos. ¡Un momento!"):
                df_final = funcion_procesamiento[selection_entidad](file_upload, nit, selection_entidad, plan_entidad)
            
            if df_final is not None and not df_final.empty:
                st.balloons()
                st.success("¡Proceso completado con éxito!")
            else:
                st.warning("El procesamiento finalizó, pero no se generaron datos. Revisa los archivos y la selección.")

        elif not file_upload:
            st.error("Por favor, carga al menos un archivo.")
        elif selection_entidad == "Seleccionar...":
            st.error("Por favor, selecciona una entidad específica.")
        else:
            st.error(f"No hay una función de procesamiento definida para '{selection_entidad}'.")

if df_final is not None and not df_final.empty:
    with st.container(border=True):
        st.header("3. Resultados")
        st.dataframe(df_final, use_container_width=True)

        output = BytesIO()
        with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
            df_final.to_excel(writer, index=False, sheet_name='Procesado')
        
        st.download_button(
            label="📥 Descargar Reporte en Excel",
            data=output.getvalue(),
            file_name=f'reporte_{selection_entidad.replace(" ", "_")}.xlsx',
            mime='application/vnd.openxmlformats-officedocument.spreadsheetml.sheet'
        )

# --- 8. PIE DE PÁGINA ---
st.markdown("---")
st.markdown("<p style='text-align: center; color: #555555; font-size: 0.8em;'>© Copyright 2025 ValleSalud </p>", unsafe_allow_html=True)
