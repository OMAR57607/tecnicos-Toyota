import streamlit as st
from supabase import create_client
import uuid
import time
import os
from datetime import datetime

# ==========================================
# 1. CONFIGURACIÓN (MODO TOUCH / MÓVIL)
# ==========================================
st.set_page_config(page_title="Taller Toyota", page_icon="🔧", layout="centered")

# CSS: Botones gigantes y textos grandes para leer bajo el sol o con prisas
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Textos generales más grandes */
    .stTextInput input, .stSelectbox div, .stNumberInput input { 
        font-size: 18px !important; 
        min-height: 50px !important; 
    }
    
    /* ÁREA DE DICTADO (IMPORTANTE PARA VOZ) */
    .stTextArea textarea {
        font-size: 20px !important; /* Letra grande para ver lo que se dicta */
        line-height: 1.5 !important;
        background-color: #ffffeba3; /* Color sutil para destacar donde escribir/hablar */
    }
    
    /* Área de carga de fotos */
    [data-testid="stFileUploader"] {
        padding: 15px; 
        border: 2px dashed #EB0A1E; 
        border-radius: 12px;
        background-color: #fff0f0; 
        text-align: center;
    }
    
    /* Botón de envío */
    div.stButton > button {
        height: 65px !important;
        font-size: 22px !important;
        font-weight: 900 !important;
        border-radius: 10px !important;
        text-transform: uppercase;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
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
        st.error("❌ Error de Conexión: Faltan credenciales.")
        return None

    return create_client(url.replace("'", "").strip(), key.replace("'", "").strip())

supabase = init_supabase_blindado()
if not supabase: st.stop()

# ==========================================
# 3. GESTIÓN DE ESTADO (PERSISTENCIA)
# ==========================================
if "form_key" not in st.session_state:
    st.session_state["form_key"] = str(uuid.uuid4())

def reiniciar_formulario():
    # Cambiamos la key para limpiar los inputs del auto, pero NO el nombre del técnico
    st.session_state["form_key"] = str(uuid.uuid4())

# ==========================================
# 4. INTERFAZ DE BAHÍA
# ==========================================

# Encabezado
c1, c2 = st.columns([1, 4])
with c1:
    if os.path.exists("logo.png"): st.image("logo.png")
with c2:
    st.markdown("### 🔧 Reporte Técnico")

# --- ZONA 1: TÉCNICO (PERSISTENTE) ---
# Este campo NO cambia al reiniciar el formulario. El técnico lo pone una vez en la mañana.
tecnico = st.text_input("👷 NOMBRE DEL TÉCNICO", placeholder="Tu nombre aquí...", key="tecnico_persistente")

if not tecnico:
    st.warning("👆 Para empezar, escribe tu nombre arriba.")
    st.stop() 

st.divider()

# Key dinámica para resetear tras envío
key_act = st.session_state["form_key"]

# --- ZONA 2: IDENTIFICACIÓN DEL AUTO (OBLIGATORIO) ---
st.markdown("##### 🚗 Identificación del Vehículo")
col_a, col_b, col_c = st.columns([1.5, 1.5, 1])

with col_a:
    orden = st.text_input("📋 ORDEN / PLACAS", placeholder="Obligatorio", key=f"ord_{key_act}")

with col_b:
    modelos_toyota = ["Hilux", "Yaris", "Corolla", "RAV4", "Hiace", "Tacoma", "Camry", "Prius", "Avanza", "Raize", "Tundra", "Sequoia", "Otro"]
    auto = st.selectbox("MODELO", modelos_toyota, key=f"mod_{key_act}")

with col_c:
    anio = st.number_input("AÑO", min_value=1990, max_value=2030, value=2024, step=1, key=f"yr_{key_act}")

# --- ZONA 3: DICTADO DE FALLAS (OBLIGATORIO Y GRANDE) ---
st.markdown("---")
st.markdown("##### 🎤 ¿Qué necesita el auto? (Dictar o Escribir)")
st.caption("Menciona fallas y refacciones requeridas.")

# Text Area grande para facilitar el uso del micrófono del teclado
fallas = st.text_area(
    "Descripción", 
    height=150, 
    placeholder="Presiona el micrófono en tu teclado y dicta: \n'Servicio de 20 mil kilometros, balatas delanteras y plumillas...'", 
    key=f"fail_{key_act}",
    label_visibility="collapsed"
)

# --- ZONA 4: EVIDENCIA (OBLIGATORIO) ---
st.markdown("##### 📸 Evidencia Fotográfica")
img_files = st.file_uploader(
    "Toca para tomar fotos o subir", 
    accept_multiple_files=True, 
    type=['png', 'jpg', 'jpeg'],
    label_visibility="collapsed",
    key=f"upl_{key_act}"
)

st.write(" ") # Espacio

# --- ZONA 5: BOTÓN DE ACCIÓN CON VALIDACIÓN ---
# Validamos que TODO esté lleno antes de mostrar el botón habilitado visualmente
datos_completos = orden and auto and anio and fallas and img_files and tecnico

if datos_completos:
    if st.button(f"🚀 ENVIAR REPORTE ({len(img_files)} FOTOS)", type="primary", use_container_width=True):
        try:
            uploaded_urls = []
            barra = st.progress(0, text="Subiendo fotos...")
            
            # 1. Subir imágenes a Storage
            for i, img in enumerate(img_files):
                ext = img.name.split('.')[-1]
                # Nombre único: ORDEN_TECNICO_ID.jpg
                filename = f"{orden}_{tecnico.split()[0]}_{uuid.uuid4().hex[:4]}.{ext}"
                bucket = "evidencias-taller"
                
                supabase.storage.from_(bucket).upload(filename, img.getvalue(), {"content-type": img.type})
                
                # Obtener URL
                res = supabase.storage.from_(bucket).get_public_url(filename)
                final_url = res if isinstance(res, str) else res.public_url
                uploaded_urls.append(final_url)
                
                barra.progress(int(((i + 1) / len(img_files)) * 100))

            # 2. Insertar Datos en Tabla (Usando columna 'tecnico')
            datos = {
                "orden_placas": orden.upper().strip(),
                "tecnico": tecnico.upper().strip(), 
                "auto_modelo": auto.upper(),
                "anio": int(anio),
                "fallas_refacciones": fallas.upper(), # Guardamos en mayúsculas
                "evidencia_fotos": uploaded_urls,
                "estado": "Pendiente",
                "created_at": datetime.utcnow().isoformat()
            }
            
            supabase.table("evidencias_taller").insert(datos).execute()
            
            barra.empty()
            st.balloons() # Feedback visual gratificante
            st.success(f"✅ Reporte de {auto} enviado correctamente.")
            time.sleep(2)
            
            reiniciar_formulario() # Limpia todo menos el técnico
            st.rerun()
            
        except Exception as e:
            st.error(f"Ocurrió un error al subir: {e}")

else:
    # Botón deshabilitado o mensaje de advertencia visual
    st.warning("⚠️ Para enviar, completa: Orden, Fotos y Descripción de Fallas.")
    st.button("🛑 FALTAN DATOS OBLIGATORIOS", disabled=True, use_container_width=True)
