import streamlit as st
from supabase import create_client
import uuid
import time
import os
from datetime import datetime

# ==========================================
# 1. CONFIGURACIÓN (MODO TALLER)
# ==========================================
st.set_page_config(page_title="Taller Toyota", page_icon="🔧", layout="centered")

# CSS: Letras grandes para facilitar lectura, pero SIN colores forzados
st.markdown("""
    <style>
    #MainMenu {visibility: hidden;}
    footer {visibility: hidden;}
    
    /* Aumentar tamaño de letra en inputs para dedos grandes/tablets */
    .stTextInput input, .stSelectbox div, .stNumberInput input, .stTextArea textarea { 
        font-size: 18px !important; 
        min-height: 50px !important;
    }
    
    /* Área de carga de fotos más visible */
    [data-testid="stFileUploader"] {
        padding: 15px; 
        border: 2px dashed #EB0A1E; 
        border-radius: 12px;
        text-align: center;
        background-color: transparent; /* Respetar tema del usuario */
    }
    
    /* Botón de envío gigante */
    div.stButton > button {
        height: 65px !important;
        font-size: 22px !important;
        font-weight: 900 !important;
        border-radius: 10px !important;
        text-transform: uppercase;
        box-shadow: 0 4px 6px rgba(0,0,0,0.2);
    }
    
    /* Espaciado para que no se vea amontonado */
    .block-container { padding-top: 2rem; }
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
# 3. GESTIÓN DE ESTADO (PERSISTENCIA)
# ==========================================
if "form_key" not in st.session_state:
    st.session_state["form_key"] = str(uuid.uuid4())

def reiniciar_formulario():
    # Cambiamos la key para limpiar los inputs del auto
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
tecnico = st.text_input("👷 NOMBRE DEL TÉCNICO", placeholder="Tu nombre aquí...", key="tecnico_persistente")

if not tecnico:
    st.warning("👆 Escribe tu nombre para empezar.")
    st.stop() 

st.divider()

# Key dinámica para resetear tras envío
key_act = st.session_state["form_key"]

# --- ZONA 2: IDENTIFICACIÓN DEL AUTO (OBLIGATORIO) ---
st.markdown("##### 🚗 Datos del Vehículo")
col_a, col_b, col_c = st.columns([1.5, 1.5, 1])

with col_a:
    orden = st.text_input("📋 ORDEN / PLACAS", placeholder="Obligatorio", key=f"ord_{key_act}")

with col_b:
    modelos_toyota = ["Hilux", "Yaris", "Corolla", "RAV4", "Hiace", "Tacoma", "Camry", "Prius", "Avanza", "Raize", "Tundra", "Sequoia", "Otro"]
    auto = st.selectbox("MODELO", modelos_toyota, key=f"mod_{key_act}")

with col_c:
    anio = st.number_input("AÑO", min_value=1990, max_value=2030, value=2024, step=1, key=f"yr_{key_act}")

# --- ZONA 3: LISTADO DE REFACCIONES (OBLIGATORIO) ---
st.markdown("---")
st.markdown("##### 🛠️ Listado de Refacciones / Fallas")
st.caption("Usa el micrófono del teclado para dictar el listado.")

fallas = st.text_area(
    "Listado de Refacciones", 
    height=150, 
    placeholder="Ej: \n- Balatas delanteras\n- Amortiguador derecho\n- Servicio 20k", 
    key=f"fail_{key_act}",
    label_visibility="collapsed"
)

# --- ZONA 4: COMENTARIOS ADICIONALES (OPCIONAL/EXTRA) ---
# Aquí va el campo que faltaba en tu tabla
st.markdown("##### 📝 Comentarios Adicionales (Opcional)")
comentarios = st.text_area(
    "Observaciones extra", 
    height=80, 
    placeholder="Ej: Cliente espera en sala, urge cotización...", 
    key=f"com_{key_act}",
    label_visibility="collapsed"
)

# --- ZONA 5: EVIDENCIA (OBLIGATORIO) ---
st.markdown("##### 📸 Fotos Evidencia")
img_files = st.file_uploader(
    "Toca aquí para tomar fotos", 
    accept_multiple_files=True, 
    type=['png', 'jpg', 'jpeg'],
    label_visibility="collapsed",
    key=f"upl_{key_act}"
)

st.write(" ") 

# --- ZONA 6: BOTÓN DE ACCIÓN ---
# Validación: Orden, Auto, Año, Fallas y Fotos son OBLIGATORIOS. Comentarios es opcional.
datos_completos = orden and auto and anio and fallas and img_files and tecnico

if datos_completos:
    if st.button(f"🚀 ENVIAR REPORTE ({len(img_files)} FOTOS)", type="primary", use_container_width=True):
        try:
            uploaded_urls = []
            barra = st.progress(0, text="Subiendo evidencia...")
            
            # 1. Subir imágenes
            for i, img in enumerate(img_files):
                ext = img.name.split('.')[-1]
                filename = f"{orden}_{tecnico.split()[0]}_{uuid.uuid4().hex[:4]}.{ext}"
                bucket = "evidencias-taller"
                
                supabase.storage.from_(bucket).upload(filename, img.getvalue(), {"content-type": img.type})
                res = supabase.storage.from_(bucket).get_public_url(filename)
                final_url = res if isinstance(res, str) else res.public_url
                uploaded_urls.append(final_url)
                
                barra.progress(int(((i + 1) / len(img_files)) * 100))

            # 2. Insertar Datos en Tabla (Mapeo exacto a tu imagen)
            datos = {
                "orden_placas": orden.upper().strip(),
                "tecnico": tecnico.upper().strip(), 
                "auto_modelo": auto.upper(),
                "anio": int(anio),
                "fallas_refacciones": fallas.upper(), 
                "comentarios": comentarios.upper() if comentarios else "", # Nuevo campo
                "evidencia_fotos": uploaded_urls,
                "estado": "Pendiente",
                "created_at": datetime.utcnow().isoformat()
            }
            
            supabase.table("evidencias_taller").insert(datos).execute()
            
            barra.empty()
            st.success(f"✅ Reporte enviado correctamente.")
            time.sleep(1.5)
            
            reiniciar_formulario() 
            st.rerun()
            
        except Exception as e:
            st.error(f"Error al enviar: {e}")

else:
    st.warning("⚠️ Completa: Orden, Fallas y Fotos para enviar.")
    st.button("🛑 DATOS INCOMPLETOS", disabled=True, use_container_width=True)
