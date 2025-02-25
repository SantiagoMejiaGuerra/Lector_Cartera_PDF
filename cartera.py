import pdfplumber
import streamlit as st
import pandas as pd
import re
from streamlit.components.v1 import components
from io import BytesIO

def seg_estado(text):
    data = {"Facturas":[]}
    
    #Analyze Values
    reasearch = r"^(\d{6,})\s+\$\s*([\d.,]+)\s+\$\s*([\d.,]+)"
    matches = re.findall(reasearch, text, re.MULTILINE)
    
    for match in matches:
        number = match[0]
        value1 = match[1].replace(",", ".")
        value2 = match[2].replace(",", ".")
        data["Facturas"].append((number, value1, value2))
    return data
    

def extract(text, pdf_file):
    if not re.search(r"www\.sis\.co[\.,]", text, re.IGNORECASE):
        
        return []
    
    data = seg_estado(text)
    
    resultados = [
        {
            "Numero Factura": factura[0],
            "Valor Bruto": factura[1],
            "Valor Neto": factura[2],
            "Archivo": pdf_file
        }
        for factura in data.get("Facturas",[])
    ]
    
    nuevos_resultados = []
    for resultado in resultados:
        valor_bruto = int(resultado["Valor Bruto"].replace(".", ""))
        valor_neto = int(resultado["Valor Neto"].replace(".", ""))
        retencion = valor_bruto - valor_neto
        servicios = valor_bruto * 0.02
        ica = valor_bruto * 0.0066
        resultado["Servicios (2%)"] = servicios
        resultado["ICA (6.6%)"] = ica
        resultado["Retención"] = retencion
        resultado_restructurado ={
            "Numero Factura": resultado["Numero Factura"],
            "Valor Bruto": resultado["Valor Bruto"],
            "Retención" : resultado["Retención"],
            "Servicios (2%)" : resultado["Servicios (2%)"],
            "ICA (6.6%)": resultado["ICA (6.6%)"],
            "Valor Neto": resultado["Valor Neto"],
            "Archivo": resultado["Archivo"]
        }
        nuevos_resultados.append(resultado_restructurado)
    
    return nuevos_resultados

def previsora_excel(excel_file):
    df = pd.read_excel(excel_file, header=8)
    df = df.drop(columns=[col for col in df.columns if "Unnamed" in col], errors='ignore')
    # df["N°. Doc. de cobro"] = df["N°. Doc. de cobro"].astype()
    df = df[["Fecha Solicitud de pago","N°. Doc. de cobro", " Valor Reclamado", "Valor pagado", "Valor Objetado", "I.V.A.", "Retención en la fuente", "I.C.A. - ImP. Ind y Ccio"]]
    df.dropna(inplace= True)
    df["Archivo"] = excel_file.name
    return df

def main():

    st.image("LOGO_RED_SLOGM-02.png", width=300, use_container_width=True)
    
    st.title("Procesador de Facturas y Excel")
    
    # Process section PDF
    st.header("Procesar Facturas PDF")
    uploaded_pdfs = st.file_uploader("Sube tus archivos PDF", 
                                    type="pdf", 
                                    accept_multiple_files=True,
                                    key="pdf_uploader")
    
    if st.button("Procesar PDFs"):
        if uploaded_pdfs:
            all_results = []
            for pdf_file in uploaded_pdfs:
                try:
                    with pdfplumber.open(pdf_file) as pdf:
                        current_results = []
                        # Procesar primera página
                        if len(pdf.pages) >= 1:
                            primera_pagina = pdf.pages[0]
                            texto = primera_pagina.extract_text() or ""
                            resultado = extract(texto, pdf_file.name)
                            if resultado:
                                current_results.extend(resultado)
                        # Procesar segunda página si existe
                        if len(pdf.pages) >= 2:
                            segunda_pagina = pdf.pages[1]
                            texto = segunda_pagina.extract_text() or ""
                            resultado = extract(texto, pdf_file.name)
                            if resultado:
                                current_results.extend(resultado)
                        if current_results:
                            all_results.extend(current_results)
                except Exception as e:
                    st.error(f"Error procesando {pdf_file.name}: {str(e)}")
            
            if all_results:
                df_pdfs = pd.DataFrame(all_results)
                st.success("¡Procesamiento de PDFs completado!")
                st.dataframe(df_pdfs)
                
                # Crear Excel descargable
                output = BytesIO()
                with pd.ExcelWriter(output, engine='xlsxwriter') as writer:
                    df_pdfs.to_excel(writer, index=False)
                st.download_button(
                    label="Descargar resultados PDFs",
                    data=output.getvalue(),
                    file_name="resultados_facturas.xlsx",
                    mime="application/vnd.ms-excel"
                )
            else:
                st.warning("No se encontraron resultados en los PDFs")
        else:
            st.warning("Por favor sube al menos un archivo PDF")
    
    # Sección para procesar Excel
    st.header("Procesar Excel Previsora")
    uploaded_excel = st.file_uploader("Sube tu archivo Excel", 
                                    type=["xlsx", "xls"],
                                    accept_multiple_files=True,
                                    key="excel_uploader")
    
    if st.button("Procesar Excel"):
        if uploaded_excel:
            try:
                dfs = []
                
                for excel_file in uploaded_excel:
                    df = previsora_excel(excel_file)
                    dfs.append(df)
                
                df_excel = pd.concat(dfs, ignore_index=True)
                
                st.success("¡Procesamiento de Excel completado!")
                st.dataframe(df_excel)
                
                #Creacion de excel
                output = BytesIO()
                with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                    df_excel.to_excel(writer, index=False)
                st.download_button(
                    label="Descargar Excel Procesando",
                    data = output.getvalue(),
                    file_name="excel_procesado.xlsx",
                    mime="application/vnd.ms-excel"
                )
            except Exception as e:
                st.error(f"Error procesando Excel: {str(e)}")
        else:
            st.warning("Por favor sube un archivo Excel")

if __name__ == "__main__":
    main()