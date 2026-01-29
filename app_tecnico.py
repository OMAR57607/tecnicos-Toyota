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
    layout="centered", # 'centered' se ve mejor en celulares
    initial_sidebar_state="collapsed"
)

# CSS PROFESIONAL
st.markdown("""
    <style>
    /* Ocultar elementos innecesarios de Streamlit */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    header {visibility: hidden;}
    
    /* 1. Ajuste de la "Cintilla" Superior */
    .block-container {
        padding-top: 1rem !important; /* Subir todo el contenido */
        padding-bottom: 2rem !important;
    }

    /* 2. Estilo de Inputs (Más grandes y legibles) */
    .stTextInput input, .stTextArea textarea { 
        font-size: 16px !important; 
        border-radius: 8px !important;
    }
    
    /* 3. Estilo del Uploader (Zona de carga) */
    [data-testid="stFileUploader"] {
        padding: 15px; 
        border: 2px dashed #EB0A1E; 
        border-radius: 12px;
        background-color: #f8f9fa; 
        text-align: center;
    }
    
    /* Modo Oscuro compatible */
    @media (prefers-color-scheme: dark) {
        [data-testid="stFileUploader"] { background-color: #262730; }
    }
    </style>
""", unsafe_allow_html=True)

# ==========================================
# 2. CONEXIÓN SUPABASE BLINDADA
# ==========================================
@st.cache_resource
def init_supabase():
    # Intenta leer de st.secrets (Local) o Variables de Entorno (Railway)
    url = os.environ.get("SUPABASE_URL")
    key = os.environ.get("SUPABASE_KEY")
    
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
# 3. GESTIÓN DE ESTADO (FORMULARIO ESTABLE)
# ==========================================

# Inicializar key del uploader si no existe (Truco para limpiar archivos)
if "uploader_key" not in st.session_state:
    st.session_state["uploader_key"] = str(uuid.uuid4())

def limpiar_formulario():
    """Limpia los campos visualmente sin perder la conexión."""
    campos = ["orden", "vin", "auto", "anio", "fallas", "comentarios"]
    for campo in campos:
        if f"{campo}_input" in st.session_state:
            st.session_state[f"{campo}_input"] = ""
    
    # Cambiamos la key del uploader para forzar su reinicio
    st.session_state["uploader_key"] = str(uuid.uuid4())

# ==========================================
# 4. INTERFAZ DE USUARIO (CINTILLA)
# ==========================================

# --- ENCABEZADO CENTRADO ---
# Usamos columnas [1,2,1] para que el logo quede perfectamente al centro
c_izq, c_cen, c_der = st.columns([1, 2, 1])

with c_cen:
    if os.path.exists("logo.png"): 
        st.image("logo.png", use_container_width=True)
    else:
        st.markdown("<h1 style='text-align: center; color: #EB0A1E;'>TOYOTA</h1>", unsafe_allow_html=True)

st.markdown("<h3 style='text-align: center; margin-top: -15px; color: #555;'>🛠️ Reporte Técnico</h3>", unsafe_allow_html=True)
st.markdown("---")

# Verificación de conexión
if not supabase:
    st.error("❌ Error Crítico: No se detectaron credenciales de Supabase en Railway.")
    st.stop()

# --- FORMULARIO ---
# Usamos `key` fija para mantener los datos si el usuario recarga accidentalmente, 
# pero los borramos programáticamente al enviar.

st.caption("📋 **DATOS DE IDENTIFICACIÓN**")
orden = st.text_input("ORDEN / PLACAS", placeholder="Requerido", key="orden_input")

c1, c2, c3 = st.columns([2, 1.5, 1])
with c1:
    vin = st.text_input("VIN (Últimos 8 o completo)", key="vin_input")
with c2:
    auto = st.text_input("MODELO", placeholder="Ej. Tacoma", key="auto_input")
with c3:
    anio = st.text_input("AÑO", placeholder="2024", key="anio_input")

st.write("") # Espacio
st.caption("🔧 **DIAGNÓSTICO**")
fallas = st.text_area("FALLAS / REFACCIONES", height=100, placeholder="Describe las fallas o piezas...", key="fallas_input")
comentarios = st.text_area("OBSERVACIONES ADICIONALES", height=80, placeholder="Golpes, detalles, etc.", key="comentarios_input")

st.write("") # Espacio
st.caption("📸 **EVIDENCIA FOTOGRÁFICA**")
img_files = st.file_uploader(
    "Subir Fotos", 
    accept_multiple_files=True, 
    type=['png', 'jpg', 'jpeg', 'webp'],
    label_visibility="collapsed",
    key=st.session_state["uploader_key"] # Key dinámica para poder limpiar
)

# --- LÓGICA DE ENVÍO ---
st.write("---")

# El botón se activa solo si hay datos mínimos o fotos
btn_disabled = False 
if st.button("📤 ENVIAR REPORTE A NUBE", type="primary", use_container_width=True, disabled=btn_disabled):
    
    # 1. Validaciones
    errores = []
    if not orden: errores.append("El campo 'Orden / Placas' es obligatorio.")
    if not auto: errores.append("El campo 'Modelo' es obligatorio.")
    
    if errores:
        for e in errores: st.error(f"⚠️ {e}")
    else:
        try:
            with st.status("🚀 Procesando reporte...", expanded=True) as status:
                uploaded_urls = []
                
                # A) Subida de Imágenes
                if img_files:
                    st.write(f"Subiendo {len(img_files)} imágenes...")
                    progress_bar = st.progress(0)
                    
                    for i, img in enumerate(img_files):
                        file_bytes = img.getvalue()
                        ext = img.name.split('.')[-1]
                        # Limpieza de nombre archivo
                        clean_orden = "".join(e for e in orden if e.isalnum())
                        filename = f"{clean_orden}_{uuid.uuid4().hex[:6]}.{ext}"
                        
                        # Subir a Storage
                        supabase.storage.from_("evidencias-taller").upload(
                            filename, file_bytes, {"content-type": img.type}
                        )
                        
                        # Obtener URL Pública
                        res_url = supabase.storage.from_("evidencias-taller").get_public_url(filename)
                        # Manejo seguro de la respuesta de URL
                        final_url = res_url if isinstance(res_url, str) else (res_url.get('publicUrl') or res_url.public_url)
                        uploaded_urls.append(final_url)
                        
                        # Actualizar barra
                        progress_bar.progress(int(((i + 1) / len(img_files)) * 100))
                
                # B) Preparar Datos
                st.write("Guardando en base de datos...")
                
                datos_db = {
                    "orden_placas": orden.upper().strip(),
                    "vin": vin.upper().strip(),
                    "auto_modelo": auto.upper().strip(),
                    "anio": int(anio) if (anio and anio.isdigit()) else 0,
                    "fallas_refacciones": fallas.upper(),
                    "comentarios": comentarios.upper(),
                    "evidencia_fotos": uploaded_urls, # Array de URLs
                    "estado": "Pendiente" # Para que aparezca en el Dashboard principal
                }
                
                # C) Insertar
                supabase.table("evidencias_taller").insert(datos_db).execute()
                
                status.update(label="✅ ¡Reporte Enviado con Éxito!", state="complete", expanded=False)
            
            # Feedback final y Limpieza
            st.success(f"Orden {orden} registrada correctamente.")
            time.sleep(1.5)
            limpiar_formulario()
            st.rerun()

        except Exception as e:
            st.error(f"❌ Ocurrió un error al enviar: {str(e)}")
