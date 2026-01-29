import streamlit as st
from supabase import create_client
import uuid
import time
import os

# ==========================================
# 1. CONFIGURACIÓN DE PÁGINA Y ESTILOS
# ==========================================
st.set_page_config(
    page_title="Recepción Toyota", 
    page_icon="🚗", 
    layout="centered",
    initial_sidebar_state="collapsed"
)

st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    .block-container {
        padding-top: 1rem !important;
        padding-bottom: 2rem !important;
    }

    .stTextInput input, .stTextArea textarea { 
        font-size: 16px !important; 
        border-radius: 8px !important;
    }
    
    [data-testid="stFileUploader"] {
        padding: 15px; 
        border: 2px dashed #EB0A1E; 
        border-radius: 12px;
        background-color: #f8f9fa; 
        text-align: center;
    }
    
    @media (prefers-color-scheme: dark) {
        [data-testid="stFileUploader"] { background-color: #262730; }
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONEXIÓN SUPABASE
# ==========================================
@st.cache_resource
def init_supabase():
    # Prioridad 1: Variables de Entorno (Railway)
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
    # Prioridad 2: Secrets (Local)
    if not url or not key:
        try:
            url = st.secrets["SUPABASE_URL"]
            key = st.secrets["SUPABASE_KEY"]
        except: pass
        
    if not url or not key:
        return None

    return create_client(url, key)

supabase = init_supabase()

# ==========================================
# 3. GESTIÓN DE ESTADO
# ==========================================
if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = str(uuid.uuid4())

def limpiar_formulario():
    campos = ["orden", "vin", "auto", "anio", "fallas", "comentarios"]
    for campo in campos:
        if f"{campo}_input" in st.session_state:
            st.session_state[f"{campo}_input"] = ""
    st.session_state["uploader_key"] = str(uuid.uuid4())

# ==========================================
# 4. INTERFAZ DE USUARIO
# ==========================================
c_izq, c_cen, c_der = st.columns([1, 2, 1])
with c_cen:
    if os.path.exists("logo.png"): 
        st.image("logo.png", use_container_width=True)
    else:
        st.markdown("<h1 style='text-align: center; color: #EB0A1E;'>TOYOTA</h1>", unsafe_allow_html=True)

st.markdown("<h3 style='text-align: center; margin-top: -15px; color: #555;'>🛠️ Reporte Técnico</h3>", unsafe_allow_html=True)
st.markdown("---")

if not supabase:
    st.error("❌ Error: No se detectaron credenciales de Supabase.")
    st.stop()

# --- FORMULARIO ---
st.caption("📋 **DATOS DE IDENTIFICACIÓN**")
orden = st.text_input("ORDEN / PLACAS", placeholder="Requerido", key="orden_input")

c1, c2, c3 = st.columns([2, 1.5, 1])
with c1:
    vin = st.text_input("VIN (Últimos 8 o completo)", key="vin_input")
with c2:
    auto = st.text_input("MODELO", placeholder="Ej. Tacoma", key="auto_input")
with c3:
    anio = st.text_input("AÑO", placeholder="2024", key="anio_input")

st.write("") 
st.caption("🔧 **DIAGNÓSTICO**")
fallas = st.text_area("FALLAS / REFACCIONES", height=100, placeholder="Describe las fallas...", key="fallas_input")
comentarios = st.text_area("OBSERVACIONES ADICIONALES", height=80, key="comentarios_input")

st.write("") 
st.caption("📸 **EVIDENCIA FOTOGRÁFICA**")
img_files = st.file_uploader(
    "Subir Fotos", 
    accept_multiple_files=True, 
    type=['png', 'jpg', 'jpeg', 'webp'],
    label_visibility="collapsed",
    key=st.session_state["uploader_key"]
)

st.write("---")

if st.button("📤 ENVIAR REPORTE A NUBE", type="primary", use_container_width=True):
    errores = []
    if not orden: errores.append("El campo 'Orden / Placas' es obligatorio.")
    if not auto: errores.append("El campo 'Modelo' es obligatorio.")
    
    if errores:
        for e in errores: st.error(f"⚠️ {e}")
    else:
        try:
            with st.status("🚀 Procesando reporte...", expanded=True) as status:
                uploaded_urls = []
                
                if img_files:
                    st.write(f"Subiendo {len(img_files)} imágenes...")
                    progress_bar = st.progress(0)
                    
                    for i, img in enumerate(img_files):
                        file_bytes = img.getvalue()
                        ext = img.name.split('.')[-1]
                        clean_orden = "".join(e for e in orden if e.isalnum())
                        filename = f"{clean_orden}_{uuid.uuid4().hex[:6]}.{ext}"
                        
                        supabase.storage.from_("evidencias-taller").upload(
                            filename, file_bytes, {"content-type": img.type}
                        )
                        
                        res_url = supabase.storage.from_("evidencias-taller").get_public_url(filename)
                        # Compatibilidad con diferentes versiones de la librería
                        final_url = res_url if isinstance(res_url, str) else (getattr(res_url, 'public_url', None) or res_url.get('publicUrl'))
                        uploaded_urls.append(final_url)
                        progress_bar.progress(int(((i + 1) / len(img_files)) * 100))
                
                datos_db = {
                    "orden_placas": orden.upper().strip(),
                    "vin": vin.upper().strip(),
                    "auto_modelo": auto.upper().strip(),
                    "anio": int(anio) if (anio and anio.isdigit()) else 0,
                    "fallas_refacciones": fallas.upper(),
                    "comentarios": comentarios.upper(),
                    "evidencia_fotos": uploaded_urls,
                    "estado": "Pendiente"
                }
                
                supabase.table("evidencias_taller").insert(datos_db).execute()
                status.update(label="✅ ¡Reporte Enviado con Éxito!", state="complete", expanded=False)
            
            st.success(f"Orden {orden} registrada correctamente.")
            time.sleep(1.5)
            limpiar_formulario()
            st.rerun()

        except Exception as e:
            st.error(f"❌ Error al enviar: {str(e)}")
