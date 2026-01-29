import streamlit as st
from supabase import create_client
import uuid
import time
import os

# ==========================================
# 1. CONFIGURACIÓN (Debe ir primero)
# ==========================================
st.set_page_config(page_title="Recepción Toyota", page_icon="🚗", layout="centered")

# CSS Ajustado (Original conservado)
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    .stTextInput input, .stTextArea textarea { font-size: 16px !important; }
    [data-testid="stFileUploader"] {
        padding: 10px; border: 2px dashed #EB0A1E; border-radius: 10px;
        background-color: #f9f9f9; text-align: center;
    }
    @media (prefers-color-scheme: dark) {
        [data-testid="stFileUploader"] { background-color: #262730; }
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONEXIÓN SUPABASE (Corregido)
# ==========================================
@st.cache_resource
def init_supabase():
    try:
        # CORRECCIÓN AQUÍ: Se agregaron las etiquetas url y key
        url = st.secrets["supabase"]["url"]
        key = st.secrets["supabase"]["key"]
        return create_client(url, key)
    except: 
        return None

supabase = init_supabase()

# ==========================================
# 3. LÓGICA DE ESTADO (Anti-Desconexión)
# ==========================================

# Iniciamos una "versión" del formulario para poder limpiarlo sin errores
if "form_iter" not in st.session_state:
    st.session_state["form_iter"] = 0

def limpiar_formulario():
    # En lugar de borrar uno por uno (que da error), cambiamos la versión
    # Esto limpia TODO (incluyendo fotos) al instante
    st.session_state["form_iter"] += 1

# Atajo para la versión actual
v = st.session_state["form_iter"]

# ==========================================
# 4. INTERFAZ
# ==========================================

col_logo, col_titulo = st.columns([1, 3])
with col_logo:
    if os.path.exists("logo.png"): 
        st.image("logo.png", use_container_width=True)
with col_titulo:
    st.markdown("## 🛠️ Reporte Técnico")

if not supabase:
    st.error("⚠️ Error de conexión: Configurar secrets.toml")
    st.stop()

st.markdown("---")

# --- SECCIÓN 1: DATOS (Keys dinámicas con _{v} para limpieza segura) ---
st.subheader("📋 Datos del Vehículo")

orden = st.text_input("ORDEN / PLACAS", placeholder="Obligatorio", key=f"orden_input_{v}")

col1, col2, col3 = st.columns([2, 1.5, 1])
with col1:
    vin = st.text_input("VIN (17 Dígitos)", max_chars=17, key=f"vin_input_{v}")
with col2:
    auto = st.text_input("AUTO", placeholder="Ej. Hilux", key=f"auto_input_{v}")
with col3:
    anio = st.text_input("AÑO", placeholder="2024", key=f"anio_input_{v}")

# --- SECCIÓN 2: DIAGNÓSTICO ---
col_fallas, col_comentarios = st.columns(2)
with col_fallas:
    fallas = st.text_area("FALLAS / REFACCIONES", height=120, key=f"fallas_input_{v}")
with col_comentarios:
    comentarios = st.text_area("COMENTARIOS", height=120, key=f"comentarios_input_{v}")

# --- SECCIÓN 3: FOTOS ---
img_files = st.file_uploader(
    "ADJUNTAR FOTOS", 
    accept_multiple_files=True, 
    type=['png', 'jpg', 'jpeg', 'webp'],
    label_visibility="collapsed",
    key=f"uploader_{v}" # El uploader ahora se limpia correctamente
)

# --- BOTÓN DE ENVÍO ---
if img_files:
    st.write(" ")
    if st.button(f"📤 ENVIAR REPORTE ({len(img_files)})", type="primary", use_container_width=True):
        
        # Validaciones
        errores = []
        if not orden: errores.append("Falta Orden")
        if not vin: errores.append("Falta VIN")
        if not auto: errores.append("Falta Auto")
        if not anio: errores.append("Falta Año")
        
        if errores:
            for err in errores: st.error(f"⚠️ {err}")
        else:
            try:
                uploaded_urls = []
                my_bar = st.progress(0, text="Subiendo...")

                # 1. Subir Fotos
                for i, img in enumerate(img_files):
                    file_bytes = img.getvalue()
                    ext = img.name.split('.')[-1]
                    clean_orden = orden.strip().replace(" ", "_")
                    filename = f"{clean_orden}_{vin[-4:]}_{uuid.uuid4().hex[:6]}.{ext}"
                    
                    supabase.storage.from_("evidencias-taller").upload(
                        filename, file_bytes, {"content-type": img.type}
                    )
                    
                    res = supabase.storage.from_("evidencias-taller").get_public_url(filename)
                    # Ajuste para obtener URL según versión de librería
                    final_url = res.public_url if hasattr(res, 'public_url') else res
                    uploaded_urls.append(final_url)
                    my_bar.progress(int(((i + 1) / len(img_files)) * 100))

                # 2. Insertar Datos
                datos = {
                    "orden_placas": orden.upper().strip(),
                    "vin": vin.upper().strip(),
                    "auto_modelo": auto.upper().strip(),
                    "anio": int(anio) if anio.isdigit() else 0,
                    "fallas_refacciones": fallas.upper(),
                    "comentarios": comentarios.upper(),
                    "evidencia_fotos": uploaded_urls
                }
                
                supabase.table("evidencias_taller").insert(datos).execute()

                my_bar.progress(100, text="✅ Enviado correctamente")
                time.sleep(1)
                
                # 3. LIMPIEZA SEGURA
                limpiar_formulario() 
                st.rerun() 

            except Exception as e:
                st.error(f"Error: {str(e)}")
