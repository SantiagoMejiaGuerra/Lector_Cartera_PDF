import pdfplumber
import streamlit as st
import pandas as pd
import re
from io import BytesIO

@st.cache_data
def charger_entidades():
    entidades = pd.read_excel("lista_de_clientes.xlsx", sheet_name="Base Clientes")
    return entidades

df_entidades = charger_entidades()

st.image("LOGO_RED_SLOGM-02.png", width=300, use_container_width=True)
st.title("Procesador de Facturas y Excel")

planes_dispo= df_entidades["Plan"].unique().tolist()
entidades_dispo= df_entidades["Razon Social "].unique().tolist()

#Selección del plan
selection_plan = st.selectbox("Selecciona el plan:", 
                            ["Todos"] + planes_dispo,
                            key = "select_plan")

if selection_plan != "Todos":
    entidades_filtradas= df_entidades[df_entidades["Plan"] == selection_plan]["Razon Social "].unique().tolist()
else:
    entidades_filtradas = df_entidades["Razon Social "].unique().tolist()

#Selección de la entidad
selection_entidad = st.selectbox("Seleccione una entidad:",
                        ["Todas"] + entidades_filtradas,
                        key= "select_entidad")

if selection_entidad !="Todas":
    planes_filtrados = df_entidades[df_entidades["Razon Social "] == selection_entidad]["Plan"].unique().tolist()
else:
    planes_filtrados = planes_dispo

if selection_entidad != "Todas":
    info_entidad = df_entidades[df_entidades["Razon Social "] == selection_entidad].iloc[0]
    nit =df_entidades[df_entidades["Razon Social "] == selection_entidad]["Nit"].iloc[0]
    plan_entidad = info_entidad["Plan"]
else:
    nit = ""
    plan_entidad = ""

#EXCEL SECTION
def procesar_axa(archivos, nit, selection_entidad, plan_entidad):
    data = []
    for archivo in archivos:
        df = pd.read_excel(archivo)
        df = df[["Fecha de Pago", "N° Factura", "Valor Pagado Antes de Imp.", "Valor Pagado Despues de Imp."]]
        df["Retención"] = df["Valor Pagado Antes de Imp."] - df["Valor Pagado Despues de Imp."]
        df["Rete. Servicios"] = df["Valor Pagado Antes de Imp."] * 0.02
        df["ICA"] = df["Retención"] - df["Rete. Servicios"]
        
        df["NIT"] = nit
        df["PLAN"] = plan_entidad
        df["ASEGURADORA"] = selection_entidad
        df["CASO"] = ""
        df["IVA"] = 0
        df["VR. FACTURA"] = df["Valor Pagado Antes de Imp."]
        df["VR. BRUTO TOMADO POR ASEGURADORA"] = df["Valor Pagado Antes de Imp."]
        df["Archivo"] = archivo.name
        
        df = df.rename(columns={
            "Fecha de Pago": "FECHA",
            "N° Factura": "APLICA A FV",
            "Rete. Servicios": "(-) RETEF",
            "ICA":"(-) ICA",
            "Retención": "SUMA RETENCIONES",
            "Valor Pagado Despues de Imp.": "VR. RECAUDO"
        })
        
        columnas_ordenadas=["FECHA", "NIT","PLAN", "ASEGURADORA", "CASO", "APLICA A FV",
                            "VR. FACTURA", "VR. BRUTO TOMADO POR ASEGURADORA", "(-) RETEF",
                            "(-) ICA", "IVA", "SUMA RETENCIONES", "VR. RECAUDO", "Archivo"]
        
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
        
        adres=adres.rename(columns={
            "Factura": "APLICA A FV",
            "Valor Reclamado": "VR. FACTURA",
            "Valor aprobado": "VR. BRUTO TOMADO POR ASEGURADORA",
            "Retencion": "SUMA RETENCIONES",
            "Neto": "VR. RECAUDADO"
        })
        
        columnas_ordenadas =["FECHA", "NIT", "PLAN", "ASEGURADORA", "CASO", "APLICA A FV",
                            "VR. FACTURA", "VR. BRUTO TOMADO POR ASEGURADORA", "(-) RETEF", 
                            "(-) ICA", "IVA", "SUMA RETENCIONES", "VR. RECAUDADO", "Archivo"]
        
        adres = adres.reindex(columns=columnas_ordenadas, fill_value="")
        
        data.append(adres)
    return pd.concat(data, ignore_index=True)

def procesar_previsora(archivos, nit,selection_entidad, plan_entidad):
    data = []
    for archivo in archivos:
        df = pd.read_excel(archivo, header=8)
        df = df.drop(columns=['Unnamed: 7', 'Unnamed: 8', 'Unnamed: 9', 'Unnamed: 21'])
        df["N°. Doc. de cobro"] = df["N°. Doc. de cobro"].astype(str)
        df = df[["Fecha Solicitud de pago","N°. Doc. de cobro", " Valor Reclamado", "Valor pagado", "Valor Objetado", "I.V.A.", "Retención en la fuente", "I.C.A. - ImP. Ind y Ccio"]]
        df["SUMA RETENCIONES"] = df["Retención en la fuente"] + df["I.C.A. - ImP. Ind y Ccio"]
        df["VR. RECAUDADO"] = df["Valor pagado"] - df["Retención en la fuente"]
        df.dropna(inplace= True)
        
        df["NIT"] = nit
        df["PLAN"] = plan_entidad
        df["ASEGURADORA"] = selection_entidad
        df["CASO"] = ""
        df["Archivo"] = archivo.name
        
        df = df.rename(columns={
            "Fecha Solicitud de pago": "FECHA",
            "N°. Doc. de cobro":"APLICA A FV",
            "I.V.A": "IVA",
            "Retención en la fuente":"(-) RETEF",
            "I.C.A. - ImP. Ind y Ccio": "(-) ICA",
            " Valor Reclamado": "VR. FACTURA",
            "Valor pagado": "VR. BRUTO TOMADO POR ASEGURADORA"
        })
        
        columnas_ordenadas =["FECHA", "NIT", "PLAN", "ASEGURADORA", "CASO", "APLICA A FV",
                            "VR. FACTURA", "VR. BRUTO TOMADO POR ASEGURADORA", "(-) RETEF", 
                            "(-) ICA", "IVA", "SUMA RETENCIONES", "VR. RECAUDADO", "Archivo"]
        
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
        
        df = df.rename(columns={
            "FECHA PAGO": "FECHA",
            "FACTURA":"APLICA A FV",
            "VALOR RECLAMADO":"VR. FACTURA",
            "VALOR APROBADO":"VR. BRUTO TOMADO POR ASEGURADORA",
            "Rete-Fuente":"(-) RETEF",
            "ICA": "(-) ICA",
            })
        
        columnas_ordenadas=["FECHA", "NIT", "PLAN", "ASEGURADORA", "CASO", 
                            "APLICA A FV", "VR. FACTURA", "VR. BRUTO TOMADO POR ASEGURADORA",
                            "(-) RETEF", "(-) ICA", "IVA", "SUMA RETENCIONES", "VR. RECAUDADO", "Archivo"]
        
        df = df.reindex(columns=columnas_ordenadas, fill_value="")
        
        data.append(df)
        
    return pd.concat(data, ignore_index=True)

def procesar_sura(archivos, nit, selection_entidad, plan_entidad):
    data = []
    
    columns_requires= [
        "Factura", "Fecha Consignacion", "Vlr Factura", "Vlr Orden de Pago", 
        "RteFete", "RteICA", "RteIVA", "Vlr Consignado"
    ]
    
    column_name_mapping = {
            "Fecha Consignacion":"FECHA",
            "Factura":"APLICA A FV",
            "Vlr Factura":"VR. FACTURA",
            "Vlr Orden de Pago":"VR. BRUTO TOMADO POR ASEGURADORA",
            "RteFete": "(-) RETEF",
            "RteICA": "(-) ICA",
            "RteIVA":"IVA",
            "Vlr Consignado":"VR. RECAUDADO"
        }
    
    for archivo in archivos:
        
        archivo.seek(0)
        df = pd.read_excel(archivo, header=None)
        
        # Search 'Beneficiario' for any part of the sheet
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
        
        columnas_ordenadas = ["FECHA", "NIT", "PLAN", "ASEGURADORA", "CASO", "APLICA A FV",
                            "VR. FACTURA", "VR. BRUTO TOMADO POR ASEGURADORA", "(-) RETEF", 
                            "(-) ICA", "IVA", "SUMA RETENCIONES", "VR. RECAUDADO",  "ARCHIVOS"]
        
        data.append(df[columnas_ordenadas])
        
    return pd.concat(data, ignore_index=True) if data else pd.DataFrame()

def procesar_liberty(archivos, nit, selection_entidad, plan_entidad):
    data = []
    
    for archivo in archivos:
        df = pd.read_excel(archivo)
        df = df[["FECHA GIRO" ,"NRO FACTURA", "VALOR LIQUIDADO", "VALOR RETEFUENTE", "VALOR PAGADO"]]
        
        df["NIT"] = nit
        df["PLAN"] = plan_entidad
        df["ASEGURADORA"] = selection_entidad
        df["CASO"] = ""
        df["VR. BRUTO TOMADO POR ASEGURADORA"] = df["VALOR LIQUIDADO"]
        df["IVA"] = 0
        df["(-) ICA"] = 0
        df["SUMA RETENCIONES"] = df["VALOR RETEFUENTE"] + df["(-) ICA"]
        df["ARCHIVO"] = archivo.name
        
        df = df.rename(columns={
            "FECHA GIRO": "FECHA",
            "NRO FACTURA":"APLICA A FV",
            "VALOR LIQUIDADO":"VR. FACTURA",
            "VALOR RETEFUENTE":"(-) RETEF",
            "VALOR PAGADO":"VR. RECAUDADO"
        })
        
        columnas_ordenadas = ["FECHA", "NIT", "PLAN", "ASEGURADORA", "CASO",
                            "APLICA A FV", "VR. FACTURA", "VR. BRUTO TOMADO POR ASEGURADORA",
                            "(-) RETEF", "(-) ICA", "IVA", "SUMA RETENCIONES", "VR. RECAUDADO", "ARCHIVO"]
        
        df = df.reindex(columns=columnas_ordenadas, fill_value="")
        
        data.append(df)
    
    return pd.concat(data, ignore_index=True)

def procesar_bolivar(archivos, nit, selection_entidad, plan_entidad):
    data = []
    
    for archivo in archivos:
        df = pd.read_excel(archivo)
        df = df[["Fecha de Pago", "Detalle", "Rte. ICA", "Rte Fuente", "Valor pago"]]
        
        df["NIT"]=nit
        df["PLAN"]=plan_entidad
        df["ASEGURADORA"] =selection_entidad
        df["CASO"] = ""
        df["VR. FACTURA"] = 0
        df["IVA"] = 0
        df["ARCHIVO"] = archivo.name
        
        df["VR. BRUTO TOMADO POR ASEGURADORA"] = df["Valor pago"] / 0.98
        df["(-) RETEF"] = df["VR. BRUTO TOMADO POR ASEGURADORA"] * 0.02
        df["SUMA RETENCIONES"] = df["(-) RETEF"] + df["Rte. ICA"]
        
        df = df.rename(columns={
            "Fecha de Pago":"FECHA",
            "Detalle":"APLICA A FV",
            "Valor pago":"VR. RECAUDADO",
            "Rte. ICA":"(-) ICA",
        })
        
        columnas_ordenadas=["FECHA", "NIT", "ASEGURADORA", "CASO", "APLICA A FV", "VR. FACTURA",
                            "VR. BRUTO TOMADO POR ASEGURADORA", "(-) RETEF", "(-) ICA", "IVA",
                            "SUMA RETENCIONES", "VR. RECAUDADO"]
        
        df = df.reindex(columns=columnas_ordenadas, fill_value="")
        
        data.append(df)
    
    return pd.concat(data, ignore_index=True)
        

#PDF SECTION
def procesar_seg_estado(archivos, nit, selection_entidad, plan_entidad):
    data = []
    
    for pdf_file in archivos:
        try:
            with pdfplumber.open(pdf_file) as pdf:
                total_text = ""
                
                # Extract text in the first 2 pages
                for i, pagina in enumerate(pdf.pages[:2]):
                    text = pagina.extract_text() or ""
                    total_text += f"\n{text}"
                    
                    #Search SISCO once
                    if i == 0 and not re.search(r"www\.sis\.co[\.,]", text, re.IGNORECASE):
                        break
                
                facturas = []
                if re.search(r"www\.sis\.co[\.,]", total_text, re.IGNORECASE):
                    matches = re.findall(r"(\d{6,8})\s+\$\s*([\d.,]+)\s+\$\s*([\d.,]+)", total_text)
                    
                    for match in matches:
                        try:
                            valor_bruto = float(match[1].replace(".", "").replace(",", "."))
                            valor_neto = float(match[2].replace(".", "").replace(",", "."))
                            
                            facturas.append({
                                "NIT":nit,
                                "PLAN": plan_entidad,
                                "ASEGURADORA": selection_entidad,
                                "CASO": "",
                                "APLICA FV": match[0],
                                "VR. FACTURA":valor_neto,
                                "VR. BRUTO TOMADO POR ASEGURADORA":valor_bruto,
                                "(-) RETEF": valor_bruto * 0.02,
                                "(-) ICA":valor_bruto * 0.0066,
                                "IVA": 0,
                                "SUMA RETENCIONES":(valor_bruto *0.02) + (valor_bruto * 0.0066),
                                "VR. RECAUDADO": valor_neto,
                                "Archivo": pdf_file.name
                            })
                        except Exception as e:
                            print(f"Error en factura {match}: {str(e)}")
                data.extend(facturas)
        except Exception as e:
            print(f"Error procesando {pdf_file.name}: {str(e)}")
            continue
    return pd.DataFrame(data) if data else pd.DataFrame()


# Diccionario de funciones por entidad
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
    "EPS SURAMERICANA": procesar_sura,
    "EPS Y MEDICINA PREPAGADA SURAMETICANA S A":procesar_sura,
    "SEGUROS DE VIDA SURAMERICANA SA": procesar_sura,
    "LIBERTY SEGUROS SA": procesar_liberty,
    "LIBERTY SEGUROS DE VIDA SA": procesar_liberty,
    "SEGUROS COMERCIALES BOLIVAR": procesar_bolivar,
    "ARL SEGUROS BOLIVAR":procesar_bolivar,
    "SEGUROS DEL ESTADO SA":procesar_seg_estado
}

#Carga de archivos
file_upload = st.file_uploader("Sube el archivo de la entidad seleccionada (Excel o PDF)", type=["xlsx", "pdf"],
                            accept_multiple_files=True)

df_final = None

if st.button("Procesar Archivos") and file_upload and selection_entidad in funcion_procesamiento:
    st.write(f"Procesando archivos para {selection_entidad}...")
    
    df_final = funcion_procesamiento[selection_entidad](file_upload, nit, selection_entidad, plan_entidad)
    
    st.subheader("Vista previa de los datos procesados")
    st.dataframe(df_final)

if df_final is not None:
    output = BytesIO()
    with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
        df_final.to_excel(writer, index= False)
    output.seek(0)
    
    st.download_button("Descargar Archivo Procesado", output, file_name="archivo_procesado.xlsx", mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet")