import streamlit as st
from supabase import create_client
import uuid
import time
import os
from datetime import datetime

# ==========================================
# 1. CONFIGURACIÓN E INICIALIZACIÓN
# ==========================================
st.set_page_config(page_title="Taller Toyota", page_icon="🔧", layout="centered")

# CSS para Móviles (Botones grandes y inputs legibles)
st.markdown("""
    <style>
    /* Ocultar elementos innecesarios */
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Inputs más grandes para dedos en tablets */
    .stTextInput input, .stSelectbox div, .stNumberInput input { 
        font-size: 18px !important; 
        min-height: 50px !important; 
    }
    
    /* Área de carga de archivos destacada */
    [data-testid="stFileUploader"] {
        padding: 20px; 
        border: 2px dashed #EB0A1E; 
        border-radius: 12px;
        background-color: #fff0f0; 
        text-align: center;
    }
    
    /* Botón de envío gigante */
    div.stButton > button {
        height: 60px !important;
        font-size: 20px !important;
        font-weight: bold !important;
        border-radius: 8px !important;
    }
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
        st.error("❌ Falta configuración de Supabase.")
        return None

    return create_client(url.replace("'", "").strip(), key.replace("'", "").strip())

supabase = init_supabase_blindado()
if not supabase: st.stop()

# ==========================================
# 3. GESTIÓN DE ESTADO (PERSISTENCIA)
# ==========================================
# Usamos esto para limpiar el formulario PERO mantener al técnico
if "form_key" not in st.session_state:
    st.session_state["form_key"] = str(uuid.uuid4())

def reiniciar_formulario():
    # Generamos nueva key para limpiar inputs, EXCEPTO el técnico que va aparte
    st.session_state["form_key"] = str(uuid.uuid4())

# ==========================================
# 4. INTERFAZ TÉCNICO (SIMPLIFICADA)
# ==========================================

# Encabezado compacto
c1, c2 = st.columns([1, 4])
with c1:
    if os.path.exists("logo.png"): st.image("logo.png")
with c2:
    st.markdown("### 🔧 Reporte de Bahía")

# --- ZONA 1: ¿QUIÉN ERES? (PERSISTENTE) ---
# Este campo NO usa la key dinámica, por eso no se borra al enviar
tecnico = st.text_input("👷 NOMBRE DEL TÉCNICO", placeholder="Ej. Juan Pérez", key="tecnico_persistente")

if not tecnico:
    st.info("👆 Ingresa tu nombre para comenzar.")
    st.stop() # Detiene la app hasta que pongan nombre

st.divider()

# --- ZONA 2: EL VEHÍCULO (SE LIMPIA CADA VEZ) ---
key_act = st.session_state["form_key"]

col_a, col_b = st.columns([1.5, 1])
with col_a:
    orden = st.text_input("📋 ORDEN / PLACAS", placeholder="Núm. Orden", key=f"ord_{key_act}")

with col_b:
    # Lista rápida para no escribir
    modelos_toyota = ["Hilux", "Yaris", "Corolla", "RAV4", "Hiace", "Tacoma", "Camry", "Prius", "Avanza", "Raize", "Otro"]
    auto = st.selectbox("🚗 MODELO", modelos_toyota, key=f"mod_{key_act}")

# --- ZONA 3: EVIDENCIA ---
st.markdown("##### 📸 Evidencia (Fallas y Piezas)")
img_files = st.file_uploader(
    "Subir Fotos", 
    accept_multiple_files=True, 
    type=['png', 'jpg', 'jpeg'],
    label_visibility="collapsed",
    key=f"upl_{key_act}"
)

# --- ZONA 4: DETALLES (PLEGABLE PARA NO ESTORBAR) ---
with st.expander("📝 Agregar detalles o comentarios (Opcional)"):
    fallas = st.text_area("Descripción de Fallas / Piezas", height=100, placeholder="¿Qué piezas necesitamos?", key=f"fail_{key_act}")
    anio = st.number_input("Año del Auto", min_value=1990, max_value=2030, value=2024, step=1, key=f"yr_{key_act}")

# --- BOTÓN DE ACCIÓN ---
if img_files and orden:
    if st.button(f"🚀 ENVIAR REPORTE ({len(img_files)} FOTOS)", type="primary", use_container_width=True):
        
        try:
            uploaded_urls = []
            barra = st.progress(0, text="Subiendo evidencia...")
            
            # 1. Subir imágenes
            for i, img in enumerate(img_files):
                ext = img.name.split('.')[-1]
                # Nombre de archivo: ORDEN_TECNICO_RANDOM.jpg
                filename = f"{orden}_{tecnico.split()[0]}_{uuid.uuid4().hex[:4]}.{ext}"
                
                bucket = "evidencias-taller"
                supabase.storage.from_(bucket).upload(filename, img.getvalue(), {"content-type": img.type})
                
                # Obtener URL pública
                res = supabase.storage.from_(bucket).get_public_url(filename)
                # Compatibilidad versiones supabase
                final_url = res if isinstance(res, str) else res.public_url
                uploaded_urls.append(final_url)
                
                barra.progress(int(((i + 1) / len(img_files)) * 100))

            # 2. Guardar en Base de Datos (Sin VIN, Con Técnico)
            datos = {
                "orden_placas": orden.upper().strip(),
                "tecnico": tecnico.upper().strip(),  # <--- CAMBIO AQUÍ
                "auto_modelo": auto.upper(),
                "anio": int(anio),
                "fallas_refacciones": fallas.upper() if fallas else "REVISIÓN GENERAL",
                "evidencia_fotos": uploaded_urls,
                "estado": "Pendiente",
                "created_at": datetime.utcnow().isoformat()
            }
            
            # NOTA: Asegúrate de que la tabla 'evidencias_taller' tenga la columna 'tecnico'
            # y que la columna 'vin' no sea obligatoria (o elimínala de la BD).
            supabase.table("evidencias_taller").insert(datos).execute()
            
            barra.empty()
            st.success("✅ ¡Enviado! Listo para el siguiente auto.")
            time.sleep(1.5)
            
            reiniciar_formulario()
            st.rerun()
            
        except Exception as e:
            st.error(f"Error al subir: {e}")

elif img_files and not orden:
    st.warning("⚠️ Falta el número de Orden o Placas.")
