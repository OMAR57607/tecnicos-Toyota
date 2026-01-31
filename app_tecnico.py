import streamlit as st
from supabase import create_client
import uuid
import time
import os
from datetime import datetime
from fpdf import FPDF  # <--- NUEVA LIBRERÍA (pip install fpdf2)

# ==========================================
# 1. CONFIGURACIÓN Y PDF LOGIC
# ==========================================
st.set_page_config(page_title="Taller Toyota", page_icon="🔧", layout="centered")

def generar_pdf(datos):
    pdf = FPDF()
    pdf.add_page()
    
    # Encabezado
    pdf.set_font("Arial", 'B', 16)
    pdf.cell(0, 10, "REPORTE TÉCNICO DE TALLER", ln=True, align='C')
    pdf.set_font("Arial", '', 10)
    pdf.cell(0, 10, f"Fecha: {datetime.now().strftime('%d/%m/%Y %H:%M')}", ln=True, align='R')
    pdf.ln(10)
    
    # Datos del Vehículo
    pdf.set_fill_color(235, 10, 30) # Rojo Toyota
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, " DATOS DEL VEHÍCULO", ln=True, fill=True)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 11)
    pdf.ln(2)
    pdf.cell(0, 7, f"Técnico: {datos['tecnico']}", ln=True)
    pdf.cell(0, 7, f"Orden/Placas: {datos['orden_placas']}", ln=True)
    pdf.cell(0, 7, f"Modelo: {datos['auto_modelo']} - Año: {datos['anio']}", ln=True)
    
    # Refacciones
    pdf.ln(5)
    pdf.set_text_color(255, 255, 255)
    pdf.set_font("Arial", 'B', 12)
    pdf.cell(0, 8, " REFACCIONES Y FALLAS", ln=True, fill=True)
    
    pdf.set_text_color(0, 0, 0)
    pdf.set_font("Arial", '', 11)
    pdf.ln(2)
    pdf.multi_cell(0, 7, datos['fallas_refacciones'])
    
    # Comentarios
    if datos['comentarios']:
        pdf.ln(5)
        pdf.set_font("Arial", 'B', 12)
        pdf.cell(0, 8, " COMENTARIOS ADICIONALES", ln=True)
        pdf.set_font("Arial", '', 11)
        pdf.multi_cell(0, 7, datos['comentarios'])

    return pdf.output(dest='S').encode('latin-1')

# CSS (Mismo que tenías)
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stTextInput input, .stSelectbox div, .stNumberInput input, .stTextArea textarea { font-size: 18px !important; min-height: 50px !important;}
    [data-testid="stFileUploader"] { padding: 15px; border: 2px dashed #EB0A1E; border-radius: 12px; text-align: center;}
    div.stButton > button { height: 65px !important; font-size: 20px !important; font-weight: 800 !important; border-radius: 10px !important;}
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
            url = st.secrets["supabase"]["url"]
            key = st.secrets["supabase"]["key"]
        except: pass
    if not url or not key:
        st.error("❌ Error: Faltan credenciales de Supabase.")
        return None
    return create_client(url.strip(), key.strip())

supabase = init_supabase_blindado()
if not supabase: st.stop()

# ==========================================
# 3. GESTIÓN DE ESTADO
# ==========================================
if "form_key" not in st.session_state:
    st.session_state["form_key"] = str(uuid.uuid4())
if "pdf_data" not in st.session_state:
    st.session_state["pdf_data"] = None

def reiniciar_formulario():
    st.session_state["form_key"] = str(uuid.uuid4())
    st.session_state["pdf_data"] = None

# ==========================================
# 4. INTERFAZ
# ==========================================
c1, c2 = st.columns([1, 4])
with c1:
    if os.path.exists("logo.png"): st.image("logo.png")
with c2:
    st.markdown("### 🔧 Reporte Técnico")

tecnico = st.text_input("👷 NOMBRE DEL TÉCNICO", placeholder="Tu nombre aquí...", key="tecnico_persistente")
if not tecnico:
    st.warning("👆 Escribe tu nombre para empezar.")
    st.stop() 

st.divider()
key_act = st.session_state["form_key"]

st.markdown("##### 🚗 Datos del Vehículo")
col_a, col_b, col_c = st.columns([1.5, 1.5, 1])
with col_a:
    orden = st.text_input("📋 ORDEN / PLACAS", placeholder="Obligatorio", key=f"ord_{key_act}")
with col_b:
    modelos_toyota = ["Hilux", "Yaris", "Corolla", "RAV4", "Hiace", "Tacoma", "Camry", "Prius", "Avanza", "Raize", "Tundra", "Sequoia", "Otro"]
    auto = st.selectbox("MODELO", modelos_toyota, key=f"mod_{key_act}")
with col_c:
    anio = st.number_input("AÑO", min_value=1990, max_value=2030, value=2024, step=1, key=f"yr_{key_act}")

st.markdown("---")
st.markdown("##### 🛠️ Listado de Refacciones / Fallas")
fallas = st.text_area("Refacciones", height=150, key=f"fail_{key_act}", label_visibility="collapsed")

st.markdown("##### 📝 Comentarios Adicionales")
comentarios = st.text_area("Observaciones", height=80, key=f"com_{key_act}", label_visibility="collapsed")

st.markdown("##### 📸 Fotos Evidencia")
img_files = st.file_uploader("Fotos", accept_multiple_files=True, type=['png', 'jpg', 'jpeg'], key=f"upl_{key_act}", label_visibility="collapsed")

st.markdown("---")

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
                barra = st.progress(0, text="Subiendo...")
                
                for i, img in enumerate(img_files):
                    ext = img.name.split('.')[-1]
                    filename = f"{orden}_{uuid.uuid4().hex[:4]}.{ext}"
                    supabase.storage.from_("evidencias-taller").upload(filename, img.getvalue())
                    res = supabase.storage.from_("evidencias-taller").get_public_url(filename)
                    uploaded_urls.append(res if isinstance(res, str) else res.public_url)
                    barra.progress(int(((i + 1) / len(img_files)) * 100))

                datos = {
                    "orden_placas": orden.upper().strip(),
                    "tecnico": tecnico.upper().strip(), 
                    "auto_modelo": auto.upper(),
                    "anio": int(anio),
                    "fallas_refacciones": fallas.upper(), 
                    "comentarios": comentarios.upper(),
                    "evidencia_fotos": uploaded_urls,
                    "estado": "Pendiente",
                    "created_at": datetime.utcnow().isoformat()
                }
                
                supabase.table("evidencias_taller").insert(datos).execute()
                
                # Generar PDF para el estado de sesión
                st.session_state["pdf_data"] = generar_pdf(datos)
                st.success("✅ Reporte guardado.")
                
            except Exception as e:
                st.error(f"Error: {e}")
    else:
        st.button("🛑 FALTA INFORMACIÓN", disabled=True, use_container_width=True)

# MOSTRAR BOTÓN DE DESCARGA SI EL PDF YA SE GENERÓ
if st.session_state["pdf_data"]:
    st.markdown("---")
    st.download_button(
        label="📥 DESCARGAR PDF PARA IMPRIMIR",
        data=st.session_state["pdf_data"],
        file_name=f"Reporte_{orden}.pdf",
        mime="application/pdf",
        use_container_width=True
    )
    if st.button("🔄 HACER NUEVO REPORTE"):
        reiniciar_formulario()
        st.rerun()
