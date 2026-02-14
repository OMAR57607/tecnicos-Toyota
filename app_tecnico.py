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
# 0. MANEJO DE ERRORES (SENTRY)
# ==========================================
sentry_sdk = None
try:
    import sentry_sdk
    if os.environ.get("SENTRY_DSN"):
        sentry_sdk.init(dsn=os.environ.get("SENTRY_DSN"), traces_sample_rate=1.0)
except ImportError:
    pass

# ==========================================
# 1. CONFIGURACIÓN Y ESTILOS
# ==========================================
st.set_page_config(page_title="Taller Toyota", page_icon="🔧", layout="centered")

TOYOTA_RED = "#EB0A1E"

st.markdown(f"""
    <style>
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    
    /* Inputs y Botones grandes para Móvil */
    .stTextInput input, .stSelectbox div, .stNumberInput input, .stTextArea textarea {{ 
        font-size: 16px !important; 
        min-height: 55px !important;
        border-radius: 8px !important;
    }}
    div.stButton > button {{
        height: 60px !important;
        font-size: 18px !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
    }}
    
    /* TARJETA MEJORADA */
    .report-card {{
        background-color: white;
        border: 1px solid #ddd;
        border-left: 6px solid {TOYOTA_RED};
        border-radius: 8px;
        margin-bottom: 15px;
        box-shadow: 0 3px 6px rgba(0,0,0,0.08);
        padding: 0;
        overflow: hidden;
    }}
    .card-header {{
        background-color: #f9f9f9;
        padding: 12px 15px;
        border-bottom: 1px solid #eee;
        display: flex;
        justify-content: space-between;
        align-items: center;
    }}
    .plate {{ font-size: 1.3rem; font-weight: 800; color: #222; letter-spacing: 0.5px; }}
    .model-tag {{
        background-color: {TOYOTA_RED};
        color: white;
        padding: 5px 12px;
        border-radius: 15px;
        font-weight: bold;
        font-size: 0.8rem;
        text-transform: uppercase;
    }}
    .card-body {{ padding: 15px; color: #555; font-size: 0.95rem; }}
    .card-footer {{
        padding: 10px 15px;
        background-color: #fff;
        border-top: 1px dashed #eee;
        text-align: right;
    }}
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONEXIÓN SUPABASE
# ==========================================
@st.cache_resource
def init_supabase():
    try:
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
    except:
        url = os.environ.get("SUPABASE_URL")
        key = os.environ.get("SUPABASE_KEY")
    
    if not url or not key: return None
    return create_client(url, key)

supabase = init_supabase()
if not supabase: st.stop()

# ==========================================
# 3. FUNCIONES (PDF & FOTOS)
# ==========================================
class PDFReport(FPDF):
    def header(self):
        # SIN LOGO EN PDF
        self.set_font('Arial', 'B', 15)
        self.set_text_color(235, 10, 30)
        self.cell(0, 10, 'REPORTE TÉCNICO TOYOTA', 0, 1, 'C')
        self.ln(5)

def generar_pdf_avanzado(datos, imagenes_bytes):
    pdf = PDFReport()
    pdf.add_page()
    
    # DATOS
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", 'B', 10)
    pdf.set_text_color(0)
    header_info = f" FOLIO: {datos['orden']}  |  FECHA: {datetime.now().strftime('%d/%m/%Y')}"
    pdf.cell(0, 8, header_info, 1, 1, 'L', fill=True)
    pdf.ln(4)
    
    pdf.set_font("Arial", '', 10)
    pdf.cell(95, 8, f"Técnico: {datos['tecnico']}", 0)
    pdf.cell(95, 8, f"Asesor: {datos['asesor']}", 0, 1) 
    
    pdf.cell(0, 8, f"Vehículo: {datos['modelo']} ({datos['anio']})", 0, 1)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    
    # SECCIONES
    pdf.ln(6)
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(235, 10, 30)
    pdf.cell(0, 8, "REFACCIONES A COTIZAR / FALLAS", 0, 1)
    pdf.set_text_color(0)
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 6, datos['fallas'])
    
    if datos['comentarios']:
        pdf.ln(6)
        pdf.set_font("Arial", 'B', 12)
        pdf.set_text_color(235, 10, 30)
        pdf.cell(0, 8, "RECOMENDACIONES TÉCNICAS", 0, 1)
        pdf.set_text_color(0)
        pdf.set_font("Arial", '', 11)
        pdf.multi_cell(0, 6, datos['comentarios'])

    # FOTOS
    if imagenes_bytes:
        pdf.add_page()
        pdf.set_font("Arial", 'B', 12)
        pdf.set_text_color(235, 10, 30)
        pdf.cell(0, 10, "EVIDENCIA FOTOGRÁFICA", 0, 1)
        
        x, y = 10, 30
        for i, img in enumerate(imagenes_bytes):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                tmp.write(img)
                name = tmp.name
            
            if y > 240: 
                pdf.add_page()
                y = 30
            
            try: pdf.image(name, x=x, y=y, w=80, h=60)
            except: pass
            
            os.unlink(name)
            
            if i % 2 == 0: x += 90
            else: x = 10; y += 70
            
    return pdf.output(dest='S').encode('latin-1')

def subir_foto_worker(file, path):
    try:
        # Renombrar archivo para evitar conflictos
        ext = file.name.split('.')[-1]
        name = f"{path}_{uuid.uuid4().hex[:8]}.{ext}"
        bucket = "evidencias-taller"
        
        # Subir
        supabase.storage.from_(bucket).upload(name, file.getvalue(), {"content-type": file.type})
        
        # Retornar URL
        return supabase.storage.from_(bucket).get_public_url(name)
    except Exception as e:
        print(f"Error subiendo {file.name}: {e}")
        return None

# ==========================================
# 4. INTERFAZ PRINCIPAL
# ==========================================
c_logo, c_title = st.columns([1, 4]) 
with c_logo:
    if os.path.exists("logo.png"):
        st.image("logo.png", width=100)
    else:
        st.markdown("<h1>🔴</h1>", unsafe_allow_html=True)
with c_title:
    st.title("Sistema Taller")
    st.caption("Recepción y Diagnóstico")

tab_nuevo, tab_historial = st.tabs(["📝 NUEVA ORDEN", "📂 HISTORIAL"])

# --- TAB 1: FORMULARIO ---
with tab_nuevo:
    if "tecnico_actual" not in st.session_state: st.session_state.tecnico_actual = ""
    if "form_token" not in st.session_state: st.session_state.form_token = str(uuid.uuid4())

    with st.container():
        tecnico = st.text_input("👤 Tu Nombre", value=st.session_state.tecnico_actual, placeholder="Ej: Juan Pérez")
        st.session_state.tecnico_actual = tecnico 

        if not tecnico:
            st.info("👋 ¡Hola! Por favor escribe tu nombre para comenzar.")
            st.stop()
        
        st.divider()

        c_orden, c_asesor = st.columns(2)
        orden = c_orden.text_input("📋 Orden / Placas", key=f"ord_{st.session_state.form_token}", placeholder="Ej: 12345 o Placas")
        asesor = c_asesor.text_input("👨‍💼 Asesor", key=f"ase_{st.session_state.form_token}", placeholder="Ej: Laura García")
        
        c_m, c_a = st.columns([2,1])
        modelo = c_m.selectbox("Modelo", ["Hilux", "Yaris", "Corolla", "RAV4", "Hiace", "Tacoma", "Camry", "Prius", "Avanza", "Tundra", "Otro"], key=f"mod_{st.session_state.form_token}")
        anio = c_a.number_input("Año", 1990, 2026, 2024, key=f"yr_{st.session_state.form_token}")
        
        st.markdown("##### 🛠️ Refacciones y Diagnóstico")
        fallas = st.text_area("Detalla las refacciones a cotizar", height=100, key=f"fail_{st.session_state.form_token}", placeholder="Ej: Amortiguadores delanteros, Balatas traseras...")

        st.markdown("##### 📸 Evidencia (Fotos)")
        fotos = st.file_uploader("Sube tus fotos aquí", accept_multiple_files=True, type=['png','jpg','jpeg'], key=f"pix_{st.session_state.form_token}")

        st.markdown("##### ⚠️ Recomendaciones Técnicas")
        recomendaciones = st.text_area("Observaciones para el cliente", height=80, key=f"rec_{st.session_state.form_token}", placeholder="Ej: Se recomienda cambio de llantas en el próximo servicio...")

        # VALIDACIÓN OBLIGATORIA
        campos_llenos = (
            orden and 
            len(orden) > 2 and 
            asesor and 
            fallas and 
            fotos and 
            recomendaciones
        )
        
        if not campos_llenos:
            st.warning("📝 Faltan detalles por llenar. Revisa que tengas fotos y recomendaciones.")

        if st.button("🚀 ENVIAR A COTIZACIÓN", type="primary", use_container_width=True, disabled=not campos_llenos):
            status = st.status("⚙️ Procesando la orden...", expanded=True)
            
            try:
                # 1. SUBIDA SECUENCIAL DE FOTOS
                urls_fotos = []
                img_bytes = [f.getvalue() for f in fotos]
                
                if fotos:
                    status.write("📸 Subiendo evidencia (una por una)...")
                    for i, file in enumerate(fotos):
                        url = subir_foto_worker(file, f"{orden}_{tecnico}")
                        if url:
                            urls_fotos.append(url)
                        else:
                            st.error(f"No se pudo subir la foto {i+1}")
                
                # 2. GENERAR PDF
                status.write("📄 Generando reporte PDF...")
                datos_pdf = {
                    "orden": orden.upper(), "tecnico": tecnico.upper(), "asesor": asesor.upper(), 
                    "modelo": modelo, "anio": anio, "fallas": fallas, "comentarios": recomendaciones
                }
                pdf_bytes = generar_pdf_avanzado(datos_pdf, img_bytes)
                
                # 3. SUBIR PDF
                pdf_name = f"Reporte_{orden}_{uuid.uuid4().hex[:4]}.pdf"
                supabase.storage.from_("reportes-pdf").upload(pdf_name, pdf_bytes, {"content-type": "application/pdf"})
                url_pdf = supabase.storage.from_("reportes-pdf").get_public_url(pdf_name)

                # 4. GUARDAR EN DB
                status.write("💾 Guardando en el sistema...")
                payload = {
                    "orden_placas": orden.upper(),
                    "tecnico": tecnico.upper(),
                    "asesor": asesor.upper(),
                    "auto_modelo": modelo,
                    "anio": anio,
                    "fallas_refacciones": fallas,
                    "comentarios": recomendaciones,
                    "evidencia_fotos": urls_fotos,
                    "url_pdf": url_pdf,
                    "created_at": datetime.now().isoformat(),
                    "estado": "Pendiente"
                }
                supabase.table("evidencias_taller").insert(payload).execute()
                
                status.update(label="✅ ¡Listo! La orden fue enviada correctamente.", state="complete", expanded=False)
                # SIN GLOBOS (BALLOONS REMOVED)
                
                st.session_state.form_token = str(uuid.uuid4())
                time.sleep(1.5)
                st.rerun()
                
            except Exception as e:
                status.update(label="❌ Ocurrió un inconveniente", state="error")
                st.error(f"Detalles del error: {e}")

# --- TAB 2: HISTORIAL ---
with tab_historial:
    if "page" not in st.session_state: st.session_state.page = 0
    if "busqueda" not in st.session_state: st.session_state.busqueda = ""
    
    ITEMS = 5

    def limpiar_busqueda():
        st.session_state.busqueda = ""
        st.session_state.page = 0

    c_s, c_x = st.columns([5, 1])
    txt = c_s.text_input("🔍 Buscar:", key="busqueda", placeholder="Placa, modelo o técnico...", label_visibility="collapsed")
    c_x.button("✖️", on_click=limpiar_busqueda, use_container_width=True)

    q = supabase.table("evidencias_taller").select("*", count="exact").order("created_at", desc=True)
    
    start = st.session_state.page * ITEMS
    end = start + ITEMS - 1

    if txt:
        f = f"orden_placas.ilike.%{txt}%,tecnico.ilike.%{txt}%,auto_modelo.ilike.%{txt}%"
        res = q.or_(f).limit(20).execute()
        data = res.data
        total = len(data)
        is_search = True
    else:
        res = q.range(start, end).execute()
        data = res.data
        total = res.count or 0
        is_search = False

    st.caption(f"Total de registros: {total}")

    if not data:
        st.info("No hay órdenes pendientes por ahora.")
    else:
        for item in data:
            try: d = datetime.fromisoformat(item['created_at']).strftime("%d %b %H:%M")
            except: d = "--"
            
            asesor_info = item.get('asesor', '') 
            asesor_str = f"| 👨‍💼 {asesor_info}" if asesor_info else ""

            st.markdown(f"""
            <div class="report-card">
                <div class="card-header">
                    <span class="plate">{item['orden_placas']}</span>
                    <span class="model-tag">{item['auto_modelo']}</span>
                </div>
                <div class="card-body">
                    👤 {item['tecnico']} {asesor_str}<br>
                    📅 {d} <br>
                    <span style="color:#EB0A1E; font-size:0.8em;">• Estatus: {item.get('estado', 'Pendiente')}</span>
                </div>
                <div class="card-footer">
                    <a href="{item['url_pdf']}" target="_blank" style="color:#EB0A1E; font-weight:bold;">
                        📄 VER PDF
                    </a>
                </div>
            </div>
            """, unsafe_allow_html=True)

    if not is_search:
        st.markdown("---")
        col_p, col_lbl, col_n = st.columns([1, 2, 1])
        with col_p:
            if st.button("⬅️", disabled=(st.session_state.page == 0), use_container_width=True):
                st.session_state.page -= 1
                st.rerun()
        with col_lbl:
            st.markdown(f"<div style='text-align:center; margin-top:15px;'>Página <b>{st.session_state.page + 1}</b></div>", unsafe_allow_html=True)
        with col_n:
            if st.button("➡️", disabled=(end >= total), use_container_width=True):
                st.session_state.page += 1
                st.rerun()
