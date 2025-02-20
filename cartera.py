import pdfplumber
import streamlit as st
import pandas as pd
import re
from io import BytesIO

def seg_estado(text):
    data = {"Facturas":[]}
    
    #Analyze Values
    reasearch = r"(\d+)\s+\$\s*([\d.,]+)\s+\$\s*([\d.,]+)"
    matches = re.findall(reasearch, text)
    
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
            "Archivo": pdf_file.name
        }
        for factura in data.get("Facturas",[])
    ]
    
    nuevos_resultados = []
    for resultado in resultados:
        valor_bruto = int(resultado["Valor Bruto"].replace(".", ""))
        valor_neto = int(resultado["Valor Neto"].replace(".", ""))
        retencion = valor_bruto - valor_neto
        resultado["Retención"] = retencion
        resultado_restructurado ={
            "Numero Factura": resultado["Numero Factura"],
            "Valor Bruto": resultado["Valor Bruto"],
            "Retención" : resultado["Retención"],
            "Valor Neto": resultado["Valor Neto"],
            "Archivo": resultado["Archivo"]
        }
        nuevos_resultados.append(resultado_restructurado)
    
    return nuevos_resultados

def main():
    st.title("Procesador de PDFs Seguros del Estado")
    st.write("Sube los archivos PDF para extraer la información")
    
    uploaded_files = st.file_uploader("Sube tus archivos PDF", type="pdf", accept_multiple_files=True)
    
    if uploaded_files:
        results = []
        errors = []
        
        #Progress Bar
        progress_bar = st.progress(0)
        status = st.empty()
        
        for i, uploaded_file in enumerate(uploaded_files):
            try:
                #Actualization progress
                progress = (i +1) / len(uploaded_files)
                progress_bar.progress(progress)
                status.text(f"Procesando archivo {i+1} de {len(uploaded_files)}...")
                
                #Text extraction
                result = []
                with pdfplumber.open(uploaded_file) as pdf:
                    
                    for page_num in [0,1]:
                        if len(pdf.pages) >page_num:
                            page = pdf.pages[page_num]
                            text = page.extract_text() or ""
                            current_result = extract(text, uploaded_file.name)
                            if current_result:
                                result.extend(current_result)
                                break
                    
                if result:
                    results.extend(result)
                else:
                    st.warning(f"No se encontraron datos en {uploaded_file.name}")
            except Exception as e:
                st.error(f"Error procesando el archivo {uploaded_file}: {str(e)}")
                errors.append(uploaded_file.name)
    
        # Show result
        if results:
            df = pd.DataFrame(results)
            
            #
            st.subheader("Vista previa de los datos")
            st.dataframe(df)
            
            #Generate excel file:
            output = BytesIO()
            with pd.ExcelWriter(output, engine="xlsxwriter") as writer:
                df.to_excel(writer, index = False, sheet_name="Datos Seguro Estado")
                writer.close()
            
            # Download Button
            st.download_button(
                label="Descargar Excel",
                data = output.getvalue(),
                file_name="resultados_cartera.xlsx",
                mime="application/vnd.openxmlformats-officedocument.spreadsheetml.sheet"
            )
            
            if errors:
                st.warning(f"Errores en los archivos: {', '.join(errors)}")
            
            #Restart Progress
            progress_bar.empty()
            status.text("Proceso completado exitosamente!")

if __name__ == "__main__":
    main()