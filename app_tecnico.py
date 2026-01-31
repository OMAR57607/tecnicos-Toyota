import streamlit as st
from supabase import create_client
import uuid
import time
import os
from datetime import datetime
from fpdf import FPDF

# ==========================================
# 1. CONFIGURACIÓN
# ==========================================
st.set_page_config(page_title="Taller Toyota", page_icon="🔧", layout="centered")

# CSS para móvil y tablas
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stTextInput input, .stSelectbox div, .stNumberInput input, .stTextArea textarea { 
        font-size: 18px !important; 
        min-height: 50px !important;
    }
    div.stButton > button {
        height: 65px !important;
        font-size: 20px !important;
        font-weight: 800 !important;
        border-radius: 10px !important;
    }
    /* Estilo para enlaces y alertas */
    .stAlert { padding: 10px !important; }
    a { text-decoration: none !important; }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONEXIÓN SUPABASE
# ==========================================
@st.cache_resource(ttl="2h")
def init_supabase_blindado():
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    if not url or not key:
        try:
            if "supabase" in st.secrets:
                url = st.secrets["supabase"]["url"]
                key = st.secrets["supabase"]["key"]
            else:
                url = st.secrets.get("SUPABASE_URL")
                key = st.secrets.get("SUPABASE_KEY")
        except: pass
    if not url or not key:
        st.error("❌ Error: Faltan credenciales de Supabase.")
        return None
    return create_client(url.replace("'", "").strip(), key.replace("'", "").strip())

supabase = init_supabase_blindado()
if not supabase: st.stop()

# ==========================================
# 3. FUNCIONES (PDF y ESTADO)
# ==========================================
def generar_pdf(datos):
    pdf = FPDF()
    pdf.add_page()
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "REPORTE TÉCNICO DE TALLER", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 10, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='R')
    pdf.ln(10)
    
    # Datos
    pdf.set_fill_color(235, 10, 30) 
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, " DATOS DEL VEHÍCULO", ln=True, fill=True)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 11)
    pdf.ln(2)
    pdf.cell(0, 7, f"Tecnico: {datos['tecnico']}", ln=True)
    pdf.cell(0, 7, f"Orden/Placas: {datos['orden_placas']}", ln=True)
    pdf.cell(0, 7, f"Modelo: {datos['auto_modelo']} - Anio: {datos['anio']}", ln=True)
    
    # Fallas
    pdf.ln(5)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, " REFACCIONES Y FALLAS", ln=True, fill=True)
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 11)
    pdf.ln(2)
    pdf.multi_cell(0, 7, datos['fallas_refacciones'])
    
    if datos['comentarios']:
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, " COMENTARIOS ADICIONALES", ln=True)
        pdf.set_font("Arial", '', 11)
        pdf.multi_cell(0, 7, datos['comentarios'])

    return pdf.output(dest='S').encode('latin-1')

if "form_key" not in st.session_state:
    st.session_state["form_key"] = str(uuid.uuid4())
if "pdf_data" not in st.session_state:
    st.session_state["pdf_data"] = None
if "ultima_orden" not in st.session_state:
    st.session_state["ultima_orden"] = ""

def reiniciar_formulario():
    st.session_state["form_key"] = str(uuid.uuid4())
    st.session_state["pdf_data"] = None

# ==========================================
# 4. INTERFAZ PRINCIPAL (TABS)
# ==========================================
c1, c2 = st.columns([1, 4])
with c1:
    if os.path.exists("logo.png"): st.image("logo.png")
with c2:
    st.markdown("### 🔧 Sistema de Taller")

# --- PESTAÑAS ---
tab1, tab2 = st.tabs(["📝 NUEVO REPORTE", "📂 HISTORIAL Y BÚSQUEDA"])

# ==========================================
# PESTAÑA 1: FORMULARIO TÉCNICO
# ==========================================
with tab1:
    tecnico = st.text_input("👷 NOMBRE DEL TÉCNICO", placeholder="Tu nombre aquí...", key="tecnico_persistente")
    if not tecnico:
        st.warning("👆 Escribe tu nombre para empezar.")
        st.stop() 

    st.divider()
    key_act = st.session_state["form_key"]

    col_a, col_b, col_c = st.columns([1.5, 1.5, 1])
    with col_a:
        orden = st.text_input("📋 ORDEN", placeholder="Obligatorio", key=f"ord_{key_act}")
    with col_b:
        modelos = ["Hilux", "Yaris", "Corolla", "RAV4", "Hiace", "Tacoma", "Camry", "Prius", "Avanza", "Raize", "Tundra", "Otro"]
        auto = st.selectbox("MODELO", modelos, key=f"mod_{key_act}")
    with col_c:
        anio = st.number_input("AÑO", 1990, 2030, 2024, key=f"yr_{key_act}")

    fallas = st.text_area("Listado de Fallas", height=150, placeholder="Describe las fallas...", key=f"fail_{key_act}")
    comentarios = st.text_area("Observaciones", height=80, key=f"com_{key_act}")
    img_files = st.file_uploader("Fotos Evidencia", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'], key=f"upl_{key_act}")

    st.markdown("---")
    
    # Botones
    datos_completos = orden and auto and anio and fallas and img_files and tecnico
    c_reset, c_send = st.columns([1, 2], gap="small")

    with c_reset:
        if st.button("🗑️ LIMPIAR", type="secondary", use_container_width=True):
            reiniciar_formulario()
            st.rerun()

    with c_send:
        if datos_completos:
            if st.button(f"🚀 ENVIAR ({len(img_files)})", type="primary", use_container_width=True):
                try:
                    uploaded_urls = []
                    barra = st.progress(0, text="Procesando...")
                    
                    # 1. Fotos
                    for i, img in enumerate(img_files):
                        ext = img.name.split('.')[-1]
                        filename = f"{orden}_{tecnico.split()[0]}_{uuid.uuid4().hex[:4]}.{ext}"
                        supabase.storage.from_("evidencias-taller").upload(filename, img.getvalue(), {"content-type": img.type})
                        res = supabase.storage.from_("evidencias-taller").get_public_url(filename)
                        final_url = res if isinstance(res, str) else res.public_url
                        uploaded_urls.append(final_url)
                        barra.progress(int(((i + 1) / (len(img_files) + 1)) * 100))

                    # 2. PDF (Construcción robusta)
                    datos_temp = {
                        "tecnico": tecnico.upper(), "orden_placas": orden.upper(),
                        "auto_modelo": auto.upper(), "anio": int(anio),
                        "fallas_refacciones": fallas.upper(), "comentarios": comentarios.upper()
                    }
                    pdf_bytes = generar_pdf(datos_temp)
                    
                    pdf_name = f"PDF_{orden}_{uuid.uuid4().hex[:4]}.pdf"
                    
                    # Subir al bucket público
                    supabase.storage.from_("reportes-pdf").upload(pdf_name, pdf_bytes, {"content-type": "application/pdf"})
                    
                    # Construir URL manualmente para evitar fallos
                    project_url = os.environ.get("SUPABASE_URL") or st.secrets.get("SUPABASE_URL") or st.secrets["supabase"]["url"]
                    project_url = project_url.replace("'", "").strip().rstrip("/")
                    url_pdf_final = f"{project_url}/storage/v1/object/public/reportes-pdf/{pdf_name}"
                    
                    barra.progress(100)

                    # 3. Base de Datos
                    datos = {
                        "orden_placas": orden.upper(), "tecnico": tecnico.upper(), 
                        "auto_modelo": auto.upper(), "anio": int(anio),
                        "fallas_refacciones": fallas.upper(), "comentarios": comentarios.upper(),
                        "evidencia_fotos": uploaded_urls,
                        "url_pdf": url_pdf_final,
                        "estado": "Pendiente",
                        "created_at": datetime.utcnow().isoformat()
                    }
                    supabase.table("evidencias_taller").insert(datos).execute()
                    
                    st.session_state["pdf_data"] = pdf_bytes
                    st.session_state["ultima_orden"] = orden.upper()
                    
                    barra.empty()
                    st.success("✅ ¡Enviado exitosamente!")
                    time.sleep(1)
                    st.rerun()
                    
                except Exception as e:
                    st.error(f"Error: {e}")
        else:
            st.button("🛑 FALTA INFO", disabled=True, use_container_width=True)

    # Descarga local inmediata
    if st.session_state["pdf_data"]:
        st.success("Reporte generado.")
        st.download_button(
            label="📥 DESCARGAR PDF",
            data=st.session_state["pdf_data"],
            file_name=f"Reporte_{st.session_state['ultima_orden']}.pdf",
            mime="application/pdf",
            use_container_width=True
        )
        if st.button("🔄 Nuevo Reporte"):
            reiniciar_formulario()
            st.rerun()

# ==========================================
# PESTAÑA 2: HISTORIAL Y BÚSQUEDA
# ==========================================
with tab2:
    # Encabezado con Botón de Recarga
    c_head, c_ref = st.columns([3, 1])
    with c_head:
        st.subheader("🔍 Historial y Búsqueda")
    with c_ref:
        if st.button("🔄 RECARGAR DATOS", use_container_width=True):
            st.rerun()
    
    # --- ZONA DE BÚSQUEDA ---
    col_search, col_btn = st.columns([3, 1])
    with col_search:
        # Input de búsqueda
        busqueda = st.text_input("Buscar por Placa, Técnico o Modelo", placeholder="Ej: Juan, Yaris, 882...", label_visibility="collapsed")
    with col_btn:
        if st.button("🔎", use_container_width=True):
            st.rerun()

    # --- LÓGICA DE FILTRADO ---
    try:
        query = supabase.table("evidencias_taller").select("orden_placas, tecnico, auto_modelo, created_at, url_pdf").order("created_at", desc=True)
        
        if busqueda:
            st.caption(f"Mostrando resultados para: '{busqueda}'")
            filtro_or = f"orden_placas.ilike.%{busqueda}%,tecnico.ilike.%{busqueda}%,auto_modelo.ilike.%{busqueda}%"
            query = query.or_(filtro_or)
        else:
            st.caption("Mostrando los últimos 10 reportes recientes.")
            query = query.limit(10)

        response = query.execute()
        data = response.data
        
        # --- VISUALIZACIÓN ---
        if data:
            for item in data:
                with st.container():
                    # Formato de fecha
                    fecha_obj = datetime.fromisoformat(item['created_at'])
                    fecha_str = fecha_obj.strftime('%d/%m/%Y')
                    hora_str = fecha_obj.strftime('%H:%M')
                    
                    # Layout de la tarjeta
                    c1, c2, c3 = st.columns([3, 2, 1.5])
                    
                    with c1:
                        st.markdown(f"**🚗 {item['orden_placas']}**")
                        st.caption(f"Modelo: {item['auto_modelo']}")
                    
                    with c2:
                        st.write(f"👷 {item['tecnico']}")
                        st.caption(f"{fecha_str} - {hora_str}")
                        
                    with c3:
                        if item.get('url_pdf'):
                            # Botón tipo enlace HTML puro para evitar problemas de Streamlit
                            st.markdown(f"""
                                <a href="{item['url_pdf']}" target="_blank" style="
                                    text-decoration: none;
                                    background-color: #d1e7dd;
                                    color: #0f5132;
                                    padding: 8px 12px;
                                    border-radius: 8px;
                                    font-weight: bold;
                                    display: block;
                                    text-align: center;
                                    border: 1px solid #0f5132;
                                ">📄 Ver PDF</a>
                            """, unsafe_allow_html=True)
                        else:
                            st.warning("Sin PDF")
                    
                    st.divider()
        else:
            st.info("🔍 No se encontraron reportes con esos datos.")
            
    except Exception as e:
        st.error(f"Error cargando historial: {e}")
