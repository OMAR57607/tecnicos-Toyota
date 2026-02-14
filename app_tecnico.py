import streamlit as st
from supabase import create_client
import uuid
import os
import time
from datetime import datetime
from fpdf import FPDF
import concurrent.futures
import tempfile
import sentry_sdk

# ==========================================
# 1. CONFIGURACIÓN E INICIALIZACIÓN
# ==========================================

# A) Configuración de Sentry (Monitoreo de Errores)
# Busca la variable SENTRY_DSN en las variables de entorno de Railway
sentry_dsn = os.environ.get("SENTRY_DSN")
if sentry_dsn:
    sentry_sdk.init(
        dsn=sentry_dsn,
        traces_sample_rate=1.0,
        profiles_sample_rate=1.0,
    )

# B) Configuración de Página Streamlit
st.set_page_config(
    page_title="Taller Toyota", 
    page_icon="🔧", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

# C) Estilos CSS (Toyota Red & Mobile First)
TOYOTA_RED = "#EB0A1E"

st.markdown(f"""
    <style>
    /* Ocultar menú default */
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    
    /* Inputs táctiles grandes */
    .stTextInput input, .stSelectbox div, .stNumberInput input, .stTextArea textarea {{ 
        font-size: 16px !important; 
        min-height: 55px !important;
        border-radius: 8px !important;
    }}
    
    /* Botones principales */
    div.stButton > button {{
        height: 60px !important;
        font-size: 18px !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
        transition: all 0.3s ease;
    }}
    
    /* === TARJETA HISTORIAL DISEÑO NUEVO === */
    .report-card {{
        background-color: white;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        margin-bottom: 16px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        overflow: hidden;
    }}
    
    .card-header {{
        background-color: #f8f9fa;
        padding: 12px 15px;
        border-bottom: 1px solid #eee;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    
    .card-plate {{
        font-size: 1.3rem;
        font-weight: 800;
        color: #333;
    }}
    
    .card-model {{
        background-color: {TOYOTA_RED};
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.85rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}

    .card-body {{
        padding: 15px;
    }}
    
    .info-row {{
        display: flex;
        align-items: center;
        margin-bottom: 6px;
        color: #555;
    }}

    .card-footer {{
        padding: 10px 15px;
        border-top: 1px dashed #eee;
        background-color: #fff;
        display: flex;
        justify-content: flex-end;
    }}
    
    .pdf-link {{
        color: {TOYOTA_RED};
        font-weight: bold;
        text-decoration: none;
        display: flex;
        align-items: center;
        gap: 5px;
        border: 1px solid {TOYOTA_RED};
        padding: 5px 10px;
        border-radius: 6px;
    }}
    .pdf-link:hover {{
        background-color: {TOYOTA_RED};
        color: white;
    }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONEXIÓN SUPABASE (Railway Compatible)
# ==========================================
@st.cache_resource
def init_supabase():
    # Prioridad: Variables de entorno (Railway) -> Secrets (Local)
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    if not url or not key:
        try:
            url = st.secrets["SUPABASE_URL"]
            key = st.secrets["SUPABASE_KEY"]
        except:
            pass
            
    if not url or not key:
        st.error("❌ Error Crítico: Faltan credenciales de Supabase.")
        st.stop()
        
    return create_client(url, key)

supabase = init_supabase()

# ==========================================
# 3. CLASES Y FUNCIONES AUXILIARES
# ==========================================

class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.set_text_color(235, 10, 30) # Rojo Toyota
        self.cell(0, 10, 'REPORTE TÉCNICO DE SERVICIO', 0, 1, 'C')
        self.ln(5)

    def footer(self):
        self.set_y(-15)
        self.set_font('Arial', 'I', 8)
        self.set_text_color(128)
        self.cell(0, 10, f'Página {self.page_no()}', 0, 0, 'C')

def generar_pdf_avanzado(datos, imagenes_bytes):
    pdf = PDFReport()
    pdf.add_page()
    
    # --- DATOS GENERALES ---
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", 'B', 10)
    pdf.set_text_color(0)
    # Celda gris con info clave
    header_text = f" ORDEN: {datos['orden']}  |  FECHA: {datetime.now().strftime('%d/%m/%Y %H:%M')}"
    pdf.cell(0, 8, header_text, 1, 1, 'L', fill=True)
    
    pdf.ln(5)
    
    # Info en dos columnas simuladas
    pdf.set_font("Arial", '', 11)
    pdf.cell(95, 7, f"Técnico: {datos['tecnico']}", 0)
    pdf.cell(95, 7, f"Vehículo: {datos['modelo']} ({datos['anio']})", 0, 1)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    
    # --- FALLAS Y DIAGNÓSTICO ---
    pdf.ln(8)
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(235, 10, 30)
    pdf.cell(0, 8, "DIAGNÓSTICO Y REFACCIONES", 0, 1)
    pdf.set_text_color(0)
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 6, datos['fallas'])
    
    if datos['comentarios']:
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 11)
        pdf.cell(0, 8, "Observaciones Adicionales:", 0, 1)
        pdf.set_font("Arial", '', 10)
        pdf.multi_cell(0, 6, datos['comentarios'])

    # --- EVIDENCIA FOTOGRÁFICA ---
    if imagenes_bytes:
        pdf.add_page()
        pdf.set_font("Arial", 'B', 12)
        pdf.set_text_color(235, 10, 30)
        pdf.cell(0, 10, "EVIDENCIA FOTOGRÁFICA", 0, 1)
        
        x_start, y_start = 10, 30
        x, y = x_start, y_start
        
        for i, img_data in enumerate(imagenes_bytes):
            # Guardar temporalmente
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                tmp.write(img_data)
                tmp_path = tmp.name
            
            # Grid lógica: 2 fotos por fila
            if i > 0 and i % 2 == 0:
                y += 90 # Salto de fila
                x = x_start
                # Si bajamos mucho, nueva página
                if y > 220:
                    pdf.add_page()
                    y = 30
            
            try:
                # Insertar imagen (ajustar ancho a 90mm)
                pdf.image(tmp_path, x=x, y=y, w=90, h=60)
                # Marco alrededor de la foto
                pdf.rect(x, y, 90, 60)
                x += 95 # Mover a la derecha para la siguiente foto
            except Exception as e:
                print(f"Error imagen PDF: {e}")
            finally:
                os.unlink(tmp_path) # Limpieza obligatoria

    return pdf.output(dest='S').encode('latin-1')

def subir_imagen_worker(archivo, prefijo):
    """Sube una imagen a Supabase Storage y retorna la URL pública."""
    try:
        ext = archivo.name.split('.')[-1]
        filename = f"{prefijo}_{uuid.uuid4().hex[:6]}.{ext}"
        bucket = "evidencias-taller" # Asegúrate que este bucket exista y sea público en Supabase
        
        supabase.storage.from_(bucket).upload(filename, archivo.getvalue(), {"content-type": archivo.type})
        return supabase.storage.from_(bucket).get_public_url(filename)
    except Exception as e:
        print(f"Error subida: {e}")
        return None

# ==========================================
# 4. INTERFAZ DE USUARIO
# ==========================================

st.title("Sistema Taller")
st.caption("Gestión de Reportes y Evidencias")

tab_nuevo, tab_historial = st.tabs(["📝 NUEVA ORDEN", "📂 HISTORIAL"])

# --- PESTAÑA 1: NUEVO REPORTE ---
with tab_nuevo:
    # Token para reiniciar formulario sin recargar página completa
    if "form_id" not in st.session_state: st.session_state.form_id = str(uuid.uuid4())
    
    with st.container():
        c1, c2 = st.columns(2)
        tecnico = c1.text_input("Técnico", placeholder="Nombre", key=f"tec_{st.session_state.form_id}")
        orden = c2.text_input("Orden / Placas", placeholder="Ej: 123ABC", key=f"ord_{st.session_state.form_id}")
        
        c3, c4 = st.columns([2, 1])
        modelo = c3.selectbox("Modelo", ["Hilux", "Yaris", "Corolla", "RAV4", "Hiace", "Tacoma", "Camry", "Prius", "Avanza", "Raize", "Tundra", "Otro"], key=f"mod_{st.session_state.form_id}")
        anio = c4.number_input("Año", 1995, 2030, 2024, key=f"an_{st.session_state.form_id}")
        
        fallas = st.text_area("Fallas y Refacciones", height=100, key=f"fal_{st.session_state.form_id}")
        comentarios = st.text_area("Notas extra (Opcional)", height=60, key=f"com_{st.session_state.form_id}")
        
        fotos = st.file_uploader("Evidencia (Fotos)", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'], key=f"upl_{st.session_state.form_id}")
        
        st.markdown("---")
        
        ready = tecnico and orden and fallas
        
        if st.button("🚀 ENVIAR REPORTE", type="primary", use_container_width=True, disabled=not ready):
            status = st.status("⚙️ Procesando...", expanded=True)
            
            try:
                # 1. Subir fotos en paralelo (Multithreading)
                urls_fotos = []
                img_bytes = [f.getvalue() for f in fotos] if fotos else []
                
                if fotos:
                    status.write("📸 Subiendo imágenes a la nube...")
                    with concurrent.futures.ThreadPoolExecutor() as executor:
                        futures = [executor.submit(subir_imagen_worker, f, f"{orden}_{tecnico}") for f in fotos]
                        for future in concurrent.futures.as_completed(futures):
                            url = future.result()
                            if url: urls_fotos.append(url)
                
                # 2. Generar PDF
                status.write("📄 Creando documento PDF...")
                datos_pdf = {"orden": orden.upper(), "tecnico": tecnico.upper(), "modelo": modelo, "anio": anio, "fallas": fallas, "comentarios": comentarios}
                pdf_bytes = generar_pdf_avanzado(datos_pdf, img_bytes)
                
                # 3. Subir PDF
                pdf_name = f"Reporte_{orden}_{uuid.uuid4().hex[:4]}.pdf"
                supabase.storage.from_("reportes-pdf").upload(pdf_name, pdf_bytes, {"content-type": "application/pdf"})
                url_pdf = supabase.storage.from_("reportes-pdf").get_public_url(pdf_name)
                
                # 4. Insertar en DB
                status.write("💾 Guardando registro...")
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
                
                status.update(label="✅ ¡Enviado con éxito!", state="complete", expanded=False)
                st.balloons()
                
                # Botón de descarga inmediata
                st.download_button("📥 Descargar PDF Generado", pdf_bytes, file_name=pdf_name, mime="application/pdf", use_container_width=True)
                
                # Botón para limpiar
                if st.button("Nuevo Formulario"):
                    st.session_state.form_id = str(uuid.uuid4())
                    st.rerun()

            except Exception as e:
                status.update(label="❌ Error", state="error")
                st.error(f"Error: {e}")
                # Enviar error a Sentry manualmente si es crítico
                sentry_sdk.capture_exception(e)

# --- PESTAÑA 2: HISTORIAL Y BÚSQUEDA ---
with tab_historial:
    # Estado de paginación
    if "page" not in st.session_state: st.session_state.page = 0
    ITEMS_PER_PAGE = 5
    
    # Barra de búsqueda
    col_s, col_r = st.columns([4, 1])
    query_txt = col_s.text_input("Buscador", placeholder="Buscar por placa, modelo...", label_visibility="collapsed")
    
    if col_r.button("✖️"):
        st.session_state.page = 0
        st.rerun()

    # Construcción de Query
    start = st.session_state.page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE - 1
    
    query = supabase.table("evidencias_taller").select("*", count="exact").order("created_at", desc=True)
    
    if query_txt:
        # Búsqueda (ignora paginación estándar, trae Top 20)
        filtro = f"orden_placas.ilike.%{query_txt}%,tecnico.ilike.%{query_txt}%,auto_modelo.ilike.%{query_txt}%"
        res = query.or_(filtro).limit(20).execute()
        data = res.data
        total_rows = len(data)
        is_search = True
    else:
        # Paginación normal
        res = query.range(start, end).execute()
        data = res.data
        total_rows = res.count
        is_search = False

    # Renderizado
    if not data:
        st.info("No se encontraron registros.")
    else:
        if not is_search:
            st.caption(f"Mostrando {start + 1}-{min(end + 1, total_rows)} de {total_rows}")
            
        for item in data:
            # Formato fecha seguro
            try:
                dt = datetime.fromisoformat(item['created_at'])
                fecha_str = dt.strftime("%d %b - %H:%M")
            except: 
                fecha_str = "--/--"

            # TARJETA HTML OPTIMIZADA
            st.markdown(f"""
                <div class="report-card">
                    <div class="card-header">
                        <span class="card-plate">{item['orden_placas']}</span>
                        <span class="card-model">{item['auto_modelo']}</span>
                    </div>
                    <div class="card-body">
                        <div class="info-row">
                            👤 <b>Téc:</b>&nbsp;{item['tecnico']}
                        </div>
                        <div class="info-row">
                            📅 {fecha_str}
                        </div>
                    </div>
                    <div class="card-footer">
                        <a href="{item['url_pdf']}" target="_blank" class="pdf-link">
                           📄 Ver PDF
                        </a>
                    </div>
                </div>
            """, unsafe_allow_html=True)
            
        # Controles de Paginación
        if not is_search and total_rows > ITEMS_PER_PAGE:
            c_prev, c_info, c_next = st.columns([1, 2, 1])
            with c_prev:
                if st.button("⬅️", disabled=(st.session_state.page == 0), use_container_width=True):
                    st.session_state.page -= 1
                    st.rerun()
            with c_next:
                if st.button("➡️", disabled=(end >= total_rows), use_container_width=True):
                    st.session_state.page += 1
                    st.rerun()