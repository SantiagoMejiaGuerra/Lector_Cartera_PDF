# Procesador de Documentos PDF - Área de Cartera 🏦

**SEGUROS DEL ESTADO**
*Sistema de Extracción Automatizado de Datos de Facturas en PDF*

[![Streamlit](https://img.shields.io/badge/Deploy%20with-Streamlit-FF4B4B?logo=streamlit)](https://streamlit.io)
[![Python](https://img.shields.io/badge/Python-3.8%2B-blue?logo=python)](https://www.python.org)

## 📌 Description

Specialised tool for automated processing of PDF documents from the State Insurance portfolio area. Extracts critical information from invoices including:
- Invoice numbers
- Gross values
- Net values
- Document authenticity validation

Developed with **Python** technology and integrated into a modern web interface using **Streamlit**.

## 👨‍🏫 Key Features

- **Batch Processing:** Loads multiple PDFs simultaneously
- **Intelligent Detection:** Automatically searches the first 2 pages of each document
- **SISCO Validation:** Filters documents through authenticity verification
- **Export to Excel:** Generates consolidated reports in XLSX format
- **Alert System:** Notifies of errors and unrecognised documents
- **Progress Bar:** Viewing of processing status

## 🛠️ Installation

1. **Requirements:** Python 3.8+.
   - Python 3.8+
   - Pip package manager

2. **Clone repository:**
   ````bash
   git clone https://github.com/tu-usuario/procesador-pdf-cartera.git
   cd processor-pdf-wallet

3. **Install dependencies**.
   ````bash
   pip install -r requirements.txt

4. **Run application**
   ````bash
   streamlit run portfolio.py