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
    /* ... (mantén tus estilos de inputs y botones anteriores) ... */
    
    /* NUEVA TARJETA MEJORADA */
    .report-card {{
        background-color: white;
        border: 1px solid #e0e0e0;
        border-radius: 12px;
        padding: 0; /* Quitamos padding del contenedor principal para manejarlo dentro */
        margin-bottom: 16px;
        box-shadow: 0 4px 6px rgba(0,0,0,0.05);
        overflow: hidden; /* Para que el borde rojo no se salga */
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
        font-size: 1.2rem;
        font-weight: 800;
        color: #333;
    }}
    
    .card-model {{
        background-color: {TOYOTA_RED}; /* Fondo ROJO */
        color: white; /* Texto BLANCO */
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.9rem;
        text-transform: uppercase;
        letter-spacing: 0.5px;
    }}

    .card-body {{
        padding: 15px;
    }}

    .card-footer {{
        padding: 10px 15px;
        border-top: 1px dashed #eee;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
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
    # --- GESTIÓN DE ESTADO DE PAGINACIÓN ---
    if "page" not in st.session_state: st.session_state.page = 0
    ITEMS_PER_PAGE = 5  # Muestra 5 tarjetas por página para que sea ligero en móvil

    # --- BARRA DE BÚSQUEDA ---
    c_search, c_reset = st.columns([4, 1])
    query_txt = c_search.text_input("🔍 Buscar:", placeholder="Placa, modelo...", label_visibility="collapsed")
    if c_reset.button("✖️", help="Limpiar búsqueda"):
        st.session_state.page = 0 # Resetear página al limpiar
        query_txt = "" # (Nota: esto requiere rerun para limpiar visualmente el input, o usar session state en el input)
        st.rerun()

    # --- CONSULTA A SUPABASE CON PAGINACIÓN ---
    # Calculamos el rango (ej. Pagina 0: 0 a 9, Pagina 1: 10 a 19)
    start = st.session_state.page * ITEMS_PER_PAGE
    end = start + ITEMS_PER_PAGE - 1

    query = supabase.table("evidencias_taller").select("*", count="exact").order("created_at", desc=True)

    # Si hay búsqueda, NO usamos paginación estándar (o reiniciamos a pag 0)
    if query_txt:
        filtro = f"orden_placas.ilike.%{query_txt}%,tecnico.ilike.%{query_txt}%,auto_modelo.ilike.%{query_txt}%"
        query = query.or_(filtro)
        # Nota: Al buscar, traemos los primeros 20 resultados coincidentes
        data_response = query.limit(20).execute()
        total_rows = len(data_response.data)
        is_search = True
    else:
        # Si NO hay búsqueda, aplicamos rango de paginación
        data_response = query.range(start, end).execute()
        total_rows = data_response.count # Supabase nos dice cuántos hay en total
        is_search = False

    data = data_response.data

    # --- VISUALIZACIÓN DE TARJETAS ---
    if not data:
        st.info("📭 No se encontraron registros.")
    else:
        if not is_search:
            st.caption(f"Mostrando {start + 1} - {min(end + 1, total_rows)} de {total_rows} órdenes")

        for item in data:
            # Parseo de fecha
            try:
                dt = datetime.fromisoformat(item['created_at'])
                fecha_fmt = dt.strftime("%d %b %H:%M") # Ej: 13 Feb 14:30
            except: fecha_fmt = "--/--"

            # Renderizado HTML con el NUEVO DISEÑO
            st.markdown(f"""
                <div class="report-card">
                    <div class="card-header">
                        <span class="card-plate">{item['orden_placas']}</span>
                        <span class="card-model">{item['auto_modelo']}</span>
                    </div>
                    <div class="card-body">
                        <div style="color:#555; margin-bottom:5px;">
                            👷‍♂️ <b>Técnico:</b> {item['tecnico']}
                        </div>
                        <div style="color:#777; font-size:0.9em;">
                            📅 {fecha_fmt}
                        </div>
                    </div>
                    <div class="card-footer">
                        <a href="{item['url_pdf']}" target="_blank" style="color:#EB0A1E; font-weight:bold; display:flex; align-items:center gap:5px;">
                           📄 Ver Reporte PDF
                        </a>
                    </div>
                </div>
            """, unsafe_allow_html=True)

    # --- BOTONES DE PAGINACIÓN (SOLO SI NO ESTAMOS BUSCANDO) ---
    if not is_search and total_rows > ITEMS_PER_PAGE:
        c_prev, c_page, c_next = st.columns([1, 2, 1])
        
        with c_prev:
            if st.button("⬅️ Anterior", disabled=(st.session_state.page == 0), use_container_width=True):
                st.session_state.page -= 1
                st.rerun()
        
        with c_page:
            st.markdown(f"<p style='text-align:center; padding-top:10px;'>Página {st.session_state.page + 1}</p>", unsafe_allow_html=True)
            
        with c_next:
            # Deshabilitar si ya no hay más registros
            if st.button("Siguiente ➡️", disabled=(end >= total_rows), use_container_width=True):
                st.session_state.page += 1
                st.rerun()
