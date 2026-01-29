# Usamos una versión ligera de Python
FROM python:3.9-slim

# Evita archivos caché y logs innecesarios
ENV PYTHONDONTWRITEBYTECODE=1
ENV PYTHONUNBUFFERED=1

# Directorio de trabajo
WORKDIR /app

# Instalar dependencias del sistema
RUN apt-get update && apt-get install -y \
    build-essential \
    curl \
    git \
    && rm -rf /var/lib/apt/lists/*

# Copiamos requirements primero para aprovechar la caché
COPY requirements.txt .
RUN pip install --no-cache-dir -r requirements.txt

# --- INICIO DEL HACK (MODIFICADO PARA logo.png) ---
# 1. Copiamos TU logo.png a la carpeta interna de Streamlit
#    Lo renombramos a 'boot_logo.png' en el destino para que sea fácil de referenciar
COPY logo.png /usr/local/lib/python3.9/site-packages/streamlit/static/boot_logo.png

# 2. Modificamos el HTML interno de Streamlit para:
#    a) Ocultar la animación original (el cochecito/círculos)
#    b) Poner tu logo como fondo centrado
RUN sed -i 's|</head>|<style>#stAppLoading { background-image: url("boot_logo.png"); background-repeat: no-repeat; background-position: center; background-size: 150px; } #stAppLoading > svg { display: none; }</style></head>|' /usr/local/lib/python3.9/site-packages/streamlit/static/index.html
# --- FIN DEL HACK ---

# Copiamos el resto de tus archivos (app.py, etc.)
COPY . .

# Comando de arranque (Asegúrate de que tu archivo principal se llame automatizacion.py)
CMD sh -c "streamlit run automatizacion.py --server.port=$PORT --server.address=0.0.0.0"
