import streamlit as st
from supabase import create_client
import uuid
import time
import os
from datetime import datetime
from fpdf import FPDF
import concurrent.futures
import tempfile

# ==========================================
# 1. CONFIGURACIÓN Y ESTILOS
# ==========================================
st.set_page_config(page_title="Taller Toyota", page_icon="🔧", layout="centered")

TOYOTA_RED = "#EB0A1E"
TOYOTA_BLACK = "#000000"

st.markdown(f"""
    <style>
    /* Ocultar elementos default */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    
    /* Inputs más grandes para dedos de mecánicos */
    .stTextInput input, .stSelectbox div, .stNumberInput input, .stTextArea textarea {{ 
        font-size: 16px !important; 
        min-height: 55px !important;
        border-radius: 8px !important;
    }}
    
    /* Botones primarios estilo Toyota */
    div.stButton > button {{
        height: 60px !important;
        font-size: 18px !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        transition: all 0.3s ease;
    }}
    
    /* Tarjetas del historial */
    .report-card {{
        background-color: #f8f9fa;
        border-left: 5px solid {TOYOTA_RED};
        padding: 15px;
        margin-bottom: 15px;
        border-radius: 5px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.1);
    }}
    
    /* Enlaces */
    a {{ text-decoration: none !important; }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. GESTIÓN DE SUPABASE
# ==========================================
@st.cache_resource
def init_supabase():
    # Intenta obtener secretos de st.secrets primero (producción), luego env vars (local)
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
    except:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
        
    if not url or not key:
        st.error("❌ Error Crítico: No se detectaron las credenciales de Supabase.")
        st.stop()
    return create_client(url, key)

supabase = init_supabase()

# ==========================================
# 3. LÓGICA DE NEGOCIO (PDF & UPLOAD)
# ==========================================

class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.set_text_color(235, 10, 30) # Toyota Red
        self.cell(0, 10, 'REPORTE TÉCNICO TOYOTA', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Pagina {self.page_no()}', 0, 0, 'C')

def generar_pdf_avanzado(datos, imagenes_bytes):
    pdf = PDFReport()
    pdf.add_page()
    
    # --- SECCIÓN 1: DATOS ---
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 8, f" FOLIO: {datos['orden']}  |  FECHA: {datetime.now().strftime('%d/%m/%Y')}", 1, 1, 'L', fill=True)
    
    pdf.ln(4)
    pdf.set_font("Arial", '', 10)
    pdf.set_text_color(0)
    
    # Tabla simple de datos
    pdf.cell(95, 8, f"Técnico: {datos['tecnico']}", 0)
    pdf.cell(95, 8, f"Vehículo: {datos['modelo']} ({datos['anio']})", 0, 1)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    
    # --- SECCIÓN 2: FALLAS ---
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(235, 10, 30)
    pdf.cell(0, 10, "DIAGNÓSTICO Y REFACCIONES", 0, 1)
    pdf.set_text_color(0)
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 6, datos['fallas'])
    
    if datos['comentarios']:
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, "Observaciones Adicionales:", 0, 1)
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 6, datos['comentarios'])

    # --- SECCIÓN 3: EVIDENCIA FOTOGRÁFICA ---
    if imagenes_bytes:
        pdf.add_page()
        pdf.set_font("Arial", 'B', 12)
        pdf.set_text_color(235, 10, 30)
        pdf.cell(0, 10, "EVIDENCIA FOTOGRÁFICA", 0, 1)
        
        # Guardar imágenes temporalmente para insertarlas en el PDF
        x, y = 10, 30
        for i, img_data in enumerate(imagenes_bytes):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                tmp.write(img_data)
                tmp_path = tmp.name
            
            # Lógica simple de grid (2 imágenes por fila)
            if i > 0 and i % 2 == 0:
                y += 110 # Salto de fila
                x = 10
                if y > 250: # Nueva página si se acaba el espacio
                    pdf.add_page()
                    y = 30
            
            try:
                # Ajustar tamaño manteniendo proporción (aprox)
                pdf.image(tmp_path, x=x, y=y, w=90, h=60)
                x += 100
            except:
                pass
            os.unlink(tmp_path) # Limpiar temp

    return pdf.output(dest='S').encode('latin-1')

def subir_imagen_worker(archivo, ruta_base):
    """ Función auxiliar para subir imágenes en paralelo """
    try:
        ext = archivo.name.split('.')[-1]
        filename = f"{ruta_base}_{uuid.uuid4().hex[:6]}.{ext}"
        bucket = "evidencias-taller"
        
        # Subir
        supabase.storage.from_(bucket).upload(filename, archivo.getvalue(), {"content-type": archivo.type})
        
        # Obtener URL Pública
        public_url = supabase.storage.from_(bucket).get_public_url(filename)
        return public_url
    except Exception as e:
        print(f"Error subiendo {archivo.name}: {e}")
        return None

# ==========================================
# 4. INTERFAZ GRÁFICA
# ==========================================

# Cabecera
c1, c2 = st.columns([1, 5])
with c1:
    # Placeholder si no hay logo
    st.markdown("🔴", unsafe_allow_html=True) 
with c2:
    st.title("Sistema Taller")
    st.caption("Reportes técnicos y evidencia digital")

tab_nuevo, tab_historial = st.tabs(["📝 NUEVA ORDEN", "📂 HISTORIAL"])

# --- TAB 1: FORMULARIO ---
with tab_nuevo:
    # Gestión de estado del formulario
    if "form_reset_token" not in st.session_state: st.session_state.form_reset_token = str(uuid.uuid4())
    
    with st.container():
        st.info("💡 Llena los campos obligatorios para habilitar el envío.")
        
        col_t1, col_t2 = st.columns(2)
        tecnico = col_t1.text_input("Técnico Responsable", key="tech_name")
        orden = col_t2.text_input("No. Orden / Placa", key=f"ord_{st.session_state.form_reset_token}")
        
        c_mod, c_anio = st.columns([2, 1])
        modelo = c_mod.selectbox("Modelo", ["Hilux", "Yaris", "Corolla", "RAV4", "Hiace", "Tacoma", "Camry", "Prius", "Avanza", "Raize", "Tundra", "Otro"], key=f"mod_{st.session_state.form_reset_token}")
        anio = c_anio.number_input("Año", 1995, 2026, 2024, key=f"an_{st.session_state.form_reset_token}")
        
        fallas = st.text_area("Descripción de Fallas y Refacciones", height=120, key=f"fai_{st.session_state.form_reset_token}")
        comentarios = st.text_area("Observaciones (Opcional)", height=80, key=f"com_{st.session_state.form_reset_token}")
        
        fotos = st.file_uploader("Evidencia (Máx 6 fotos)", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'], key=f"upl_{st.session_state.form_reset_token}")

        st.markdown("---")
        
        # Validación
        es_valido = tecnico and orden and fallas and len(orden) > 2

        if st.button("🚀 PROCESAR ORDEN", type="primary", use_container_width=True, disabled=not es_valido):
            
            status_container = st.status("⚙️ Iniciando proceso...", expanded=True)
            
            try:
                # 1. Subida paralela de imágenes
                urls_fotos = []
                imagenes_bytes = [f.getvalue() for f in fotos] # Guardar bytes para el PDF
                
                if fotos:
                    status_container.write("📸 Subiendo imágenes a la nube...")
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        # Preparamos los argumentos para cada hilo
                        futures = [executor.submit(subir_imagen_worker, f, f"{orden}_{tecnico}") for f in fotos]
                        for future in concurrent.futures.as_completed(futures):
                            url = future.result()
                            if url: urls_fotos.append(url)
                
                # 2. Generación de PDF
                status_container.write("📄 Generando reporte PDF...")
                datos_pdf = {
                    "orden": orden.upper(), "tecnico": tecnico.upper(),
                    "modelo": modelo, "anio": anio, "fallas": fallas, "comentarios": comentarios
                }
                pdf_bytes = generar_pdf_avanzado(datos_pdf, imagenes_bytes)
                
                # 3. Subir PDF
                pdf_name = f"Reporte_{orden}_{uuid.uuid4().hex[:4]}.pdf"
                supabase.storage.from_("reportes-pdf").upload(pdf_name, pdf_bytes, {"content-type": "application/pdf"})
                url_pdf = supabase.storage.from_("reportes-pdf").get_public_url(pdf_name)
                
                # 4. Guardar en Base de Datos
                status_container.write("💾 Registrando en base de datos...")
                payload = {
                    "orden_placas": orden.upper(),
                    "tecnico": tecnico.upper(),
                    "auto_modelo": modelo,
                    "anio": anio,
                    "fallas_refacciones": fallas,
                    "comentarios": comentarios,
                    "evidencia_fotos": urls_fotos,
                    "url_pdf": url_pdf,
                    "created_at": datetime.now().isoformat(),
                    "estado": "Finalizado"
                }
                supabase.table("evidencias_taller").insert(payload).execute()
                
                status_container.update(label="✅ ¡Proceso Exitoso!", state="complete", expanded=False)
                
                # Botón de descarga directa
                st.download_button("📥 DESCARGAR REPORTE", pdf_bytes, file_name=pdf_name, mime="application/pdf", use_container_width=True)
                
                # Resetear form (opcional, o dejar para que el usuario limpie)
                if st.button("Nuevo Reporte"):
                    st.session_state.form_reset_token = str(uuid.uuid4())
                    st.rerun()

            except Exception as e:
                status_container.update(label="❌ Error", state="error")
                st.error(f"Ocurrió un error: {str(e)}")

# --- TAB 2: HISTORIAL ---
with tab_historial:
    c_search, c_btn = st.columns([4, 1])
    query_txt = c_search.text_input("Buscar reporte", placeholder="Placa, modelo o técnico", label_visibility="collapsed")
    
    if c_btn.button("🔄"):
        st.rerun()

    # Query optimizada
    base_query = supabase.table("evidencias_taller").select("*").order("created_at", desc=True).limit(15)
    
    if query_txt:
        # Filtro OR
        filtro = f"orden_placas.ilike.%{query_txt}%,tecnico.ilike.%{query_txt}%,auto_modelo.ilike.%{query_txt}%"
        base_query = base_query.or_(filtro)
    
    data = base_query.execute().data
    
    if not data:
        st.info("No hay registros recientes.")
    
    for item in data:
        # Parseo seguro de fecha
        try:
            dt = datetime.fromisoformat(item['created_at'])
            fecha_fmt = dt.strftime("%d %b %Y - %H:%M")
        except:
            fecha_fmt = "Fecha desconocida"
            
        st.markdown(f"""
            <div class="report-card">
                <div style="display:flex; justify-content:space-between; align-items:center;">
                    <h3 style="margin:0; color:#333;">{item['orden_placas']}</h3>
                    <span style="background:#eee; padding:2px 8px; border-radius:4px; font-size:0.8em;">{item['auto_modelo']}</span>
                </div>
                <div style="color:#666; font-size:0.9em; margin-top:5px;">
                    👤 <b>{item['tecnico']}</b> &nbsp;|&nbsp; 📅 {fecha_fmt}
                </div>
                <div style="margin-top:10px;">
                    <a href="{item['url_pdf']}" target="_blank" style="color:{TOYOTA_RED}; font-weight:bold;">
                       📄 Ver PDF
                    </a>
                </div>
            </div>
        """, unsafe_allow_html=True)
