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

st.markdown(f"""
    <style>
    #MainMenu {{visibility: hidden;}}
    footer {{visibility: hidden;}}
    
    /* Estilos Generales */
    .stTextInput input, .stSelectbox div, .stNumberInput input, .stTextArea textarea {{ 
        font-size: 16px !important; 
        min-height: 55px !important;
        border-radius: 8px !important;
    }}
    div.stButton > button {{
        height: 55px !important;
        font-size: 18px !important;
        font-weight: 700 !important;
        border-radius: 8px !important;
    }}
    
    /* TARJETA MEJORADA */
    .report-card {{
        background-color: white;
        border: 1px solid #ddd;
        border-left: 5px solid {TOYOTA_RED};
        border-radius: 8px;
        margin-bottom: 12px;
        box-shadow: 0 2px 4px rgba(0,0,0,0.05);
        padding: 15px;
    }}
    .card-header {{
        display: flex;
        justify-content: space-between;
        align-items: center;
        margin-bottom: 10px;
        border-bottom: 1px solid #eee;
        padding-bottom: 5px;
    }}
    .plate {{ font-size: 1.4rem; font-weight: 800; color: #333; }}
    .model-tag {{
        background-color: {TOYOTA_RED};
        color: white;
        padding: 4px 12px;
        border-radius: 20px;
        font-weight: bold;
        font-size: 0.85rem;
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
    return create_client(url, key) if url and key else None

supabase = init_supabase()
if not supabase: st.stop()

# ==========================================
# 3. FUNCIONES AUXILIARES
# ==========================================
class PDFReport(FPDF):
    def header(self):
        self.set_font('Arial', 'B', 15)
        self.set_text_color(235, 10, 30)
        self.cell(0, 10, 'REPORTE TÉCNICO TOYOTA', 0, 1, 'C')
        self.ln(5)

def generar_pdf_avanzado(datos, imagenes_bytes):
    pdf = PDFReport()
    pdf.add_page()
    pdf.set_fill_color(240, 240, 240)
    pdf.set_font("Arial", 'B', 10)
    pdf.cell(0, 8, f" FOLIO: {datos['orden']}  |  FECHA: {datetime.now().strftime('%d/%m/%Y')}", 1, 1, 'L', fill=True)
    pdf.ln(5)
    pdf.set_font("Arial", '', 10)
    pdf.cell(95, 8, f"Técnico: {datos['tecnico']}", 0)
    pdf.cell(95, 8, f"Vehículo: {datos['modelo']} ({datos['anio']})", 0, 1)
    pdf.line(10, pdf.get_y(), 200, pdf.get_y())
    pdf.ln(5)
    pdf.set_font("Arial", 'B', 12)
    pdf.set_text_color(235, 10, 30)
    pdf.cell(0, 10, "DIAGNÓSTICO", 0, 1)
    pdf.set_text_color(0)
    pdf.set_font("Arial", '', 11)
    pdf.multi_cell(0, 6, datos['fallas'])
    
    if imagenes_bytes:
        pdf.add_page()
        pdf.cell(0, 10, "EVIDENCIA", 0, 1)
        x, y = 10, 30
        for i, img in enumerate(imagenes_bytes):
            with tempfile.NamedTemporaryFile(delete=False, suffix=".jpg") as tmp:
                tmp.write(img)
                name = tmp.name
            if y > 240: pdf.add_page(); y=30
            try: pdf.image(name, x=x, y=y, w=80, h=60)
            except: pass
            os.unlink(name)
            if i%2==0: x+=90
            else: x=10; y+=70
            
    return pdf.output(dest='S').encode('latin-1')

def subir_foto(file, path):
    try:
        ext = file.name.split('.')[-1]
        name = f"{path}_{uuid.uuid4().hex[:6]}.{ext}"
        bucket = "evidencias-taller"
        supabase.storage.from_(bucket).upload(name, file.getvalue(), {"content-type": file.type})
        return supabase.storage.from_(bucket).get_public_url(name)
    except: return None

# ==========================================
# 4. INTERFAZ PRINCIPAL
# ==========================================
c1, c2 = st.columns([1, 5])
with c1: st.markdown("🔴", unsafe_allow_html=True) 
with c2: st.title("Sistema Taller")

tab_nuevo, tab_historial = st.tabs(["📝 NUEVA ORDEN", "📂 HISTORIAL"])

# --- TAB 1: FORMULARIO ---
with tab_nuevo:
    # ### ARREGLO 1: Persistencia del Técnico
    if "tecnico_actual" not in st.session_state: st.session_state.tecnico_actual = ""
    # ### ARREGLO 2: Token único para evitar duplicados
    if "form_token" not in st.session_state: st.session_state.form_token = str(uuid.uuid4())

    with st.container():
        # Input del técnico siempre visible
        tecnico = st.text_input("👤 Nombre del Técnico", value=st.session_state.tecnico_actual, placeholder="Ingresa tu nombre para desbloquear")
        st.session_state.tecnico_actual = tecnico # Guardar en tiempo real

        if not tecnico:
            st.warning("🔒 Escribe tu nombre para comenzar.")
            st.stop()
        
        st.divider()

        # Usamos form_token en los keys para limpiar los campos al cambiar el token
        col_ord, _ = st.columns([2,1])
        orden = col_ord.text_input("📋 Orden / Placas", key=f"ord_{st.session_state.form_token}")
        
        c_m, c_a = st.columns([2,1])
        modelo = c_m.selectbox("Modelo", ["Hilux", "Yaris", "Corolla", "RAV4", "Hiace", "Tacoma", "Camry", "Prius", "Avanza", "Tundra", "Otro"], key=f"mod_{st.session_state.form_token}")
        anio = c_a.number_input("Año", 1990, 2026, 2024, key=f"yr_{st.session_state.form_token}")
        
        fallas = st.text_area("Fallas", height=100, key=f"fail_{st.session_state.form_token}")
        fotos = st.file_uploader("Fotos", accept_multiple_files=True, type=['png','jpg'], key=f"pix_{st.session_state.form_token}")
        notas = st.text_area("Notas extra", height=60, key=f"note_{st.session_state.form_token}")

        if st.button("🚀 ENVIAR REPORTE", type="primary", use_container_width=True, disabled=not(orden and fallas)):
            status = st.status("⚙️ Procesando...", expanded=True)
            try:
                # 1. Fotos
                urls = []
                bytes_img = [f.getvalue() for f in fotos]
                if fotos:
                    status.write("Subiendo fotos...")
                    with concurrent.futures.ThreadPoolExecutor() as exc:
                        futures = [exc.submit(subir_foto, f, f"{orden}_{tecnico}") for f in fotos]
                        for f in concurrent.futures.as_completed(futures):
                            if u:=f.result(): urls.append(u)
                
                # 2. PDF
                status.write("Generando PDF...")
                pdf_data = generar_pdf_avanzado(
                    {"orden":orden, "tecnico":tecnico, "modelo":modelo, "anio":anio, "fallas":fallas, "comentarios":notas}, 
                    bytes_img
                )
                pdf_name = f"Reporte_{orden}_{uuid.uuid4().hex[:4]}.pdf"
                supabase.storage.from_("reportes-pdf").upload(pdf_name, pdf_data, {"content-type": "application/pdf"})
                url_pdf = supabase.storage.from_("reportes-pdf").get_public_url(pdf_name)

                # 3. DB
                status.write("Guardando...")
                supabase.table("evidencias_taller").insert({
                    "orden_placas": orden.upper(), "tecnico": tecnico.upper(), "auto_modelo": modelo,
                    "anio": anio, "fallas_refacciones": fallas, "comentarios": notas,
                    "evidencia_fotos": urls, "url_pdf": url_pdf,
                    "created_at": datetime.now().isoformat()
                }).execute()
                
                status.update(label="✅ ¡Listo!", state="complete", expanded=False)
                
                # ### ARREGLO: Resetear Token para limpiar campos y EVITAR DUPLICADOS
                st.session_state.form_token = str(uuid.uuid4()) 
                time.sleep(1)
                st.rerun()
                
            except Exception as e:
                st.error(f"Error: {e}")

# --- TAB 2: HISTORIAL (ARREGLADO VISUALMENTE) ---
with tab_historial:
    if "page" not in st.session_state: st.session_state.page = 0
    if "busqueda" not in st.session_state: st.session_state.busqueda = ""
    
    ITEMS = 5

    # ### ARREGLO 3: Callback para limpiar Búsqueda REALMENTE
    def limpiar():
        st.session_state.busqueda = ""
        st.session_state.page = 0

    c_search, c_x = st.columns([5, 1])
    # Vinculamos el text_input directamente al session_state
    txt = c_search.text_input("🔍 Buscar:", key="busqueda", placeholder="Placa, modelo...", label_visibility="collapsed")
    
    # Botón con callback 'on_click'
    c_x.button("✖️", on_click=limpiar, use_container_width=True)

    # Lógica
    start = st.session_state.page * ITEMS
    end = start + ITEMS - 1
    
    q = supabase.table("evidencias_taller").select("*", count="exact").order("created_at", desc=True)
    
    if txt:
        f = f"orden_placas.ilike.%{txt}%,tecnico.ilike.%{txt}%,auto_modelo.ilike.%{txt}%"
        res = q.or_(f).limit(20).execute()
        data = res.data
        total = len(data)
        searching = True
    else:
        res = q.range(start, end).execute()
        data = res.data
        total = res.count or 0
        searching = False

    # Renderizado
    st.caption(f"Registros encontrados: {total}")

    if not data:
        st.info("No hay datos.")
    else:
        for item in data:
            try: d = datetime.fromisoformat(item['created_at']).strftime("%d %b %H:%M")
            except: d = "--"
            
            st.markdown(f"""
            <div class="report-card">
                <div class="card-header">
                    <span class="plate">{item['orden_placas']}</span>
                    <span class="model-tag">{item['auto_modelo']}</span>
                </div>
                <div style="color:#555; margin-bottom:10px;">
                    👤 {item['tecnico']} &nbsp;|&nbsp; 📅 {d}
                </div>
                <div style="text-align:right;">
                    <a href="{item['url_pdf']}" target="_blank" style="color:{TOYOTA_RED}; font-weight:bold; border:1px solid {TOYOTA_RED}; padding:5px 10px; border-radius:5px;">
                        📄 VER PDF
                    </a>
                </div>
            </div>
            """, unsafe_allow_html=True)

    # ### ARREGLO 4: Paginación SIEMPRE VISIBLE (Incluso si solo hay 1 página)
    # Lo sacamos de condicionales complejos para que se vea la estructura
    if not searching:
        st.markdown("---")
        col_p, col_lbl, col_n = st.columns([1, 2, 1])
        
        with col_p:
            if st.button("⬅️", disabled=(st.session_state.page == 0), use_container_width=True):
                st.session_state.page -= 1
                st.rerun()
        
        with col_lbl:
            st.markdown(f"<div style='text-align:center; margin-top:15px;'>Página <b>{st.session_state.page + 1}</b></div>", unsafe_allow_html=True)
            
        with col_n:
            # Deshabilitar si hemos llegado al final
            if st.button("➡️", disabled=(end >= total), use_container_width=True):
                st.session_state.page += 1
                st.rerun()
