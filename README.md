# 🎵 Venom — Agente Entrevistador de Músicos

Agente IA que entrevista músicos sobre su experiencia con DAWs (Digital Audio Workstations) para recopilar datos de producto.

## Stack

- **Frontend**: Streamlit (Python)
- **LLM**: Llama 3.3 70B via Groq API (OpenAI-compatible)
- **Almacenamiento**: JSON local + export CSV

## Requisitos previos

1. **Python 3.10+** instalado
2. **API Key de Groq** (ver instrucciones abajo)

## Cómo obtener tu API Key de Groq

1. Ve a [console.groq.com](https://console.groq.com/)
2. Inicia sesión o crea una cuenta
3. En el menú lateral, ve a **API Keys**
4. Click en **Create API Key**
5. Ponle un nombre (ej: "venom") y copia la key generada (empieza con `gsk_...`)
6. Guárdala en un lugar seguro

## Instalación local

```bash
# 1. Clonar o navegar al directorio
cd agente-entrevistador

# 2. Crear entorno virtual (recomendado)
python -m venv venv
venv\Scripts\activate        # Windows
# source venv/bin/activate   # macOS/Linux

# 3. Instalar dependencias
pip install -r requirements.txt

# 4. Configurar API Key (elige UNA opción):

# Opción A: Archivo .env (recomendado para desarrollo)
copy .env.example .env
# Edita .env y reemplaza "tu_api_key_aqui" con tu key real

# Opción B: Variable de entorno
set GROQ_API_KEY=tu_api_key_aqui        # Windows CMD
# export GROQ_API_KEY=tu_api_key_aqui   # macOS/Linux

# Opción C: Ingresarla directamente en la interfaz (sidebar)

# 5. Correr la app
streamlit run app.py
```

Se abrirá en tu navegador en `http://localhost:8501`

## Deploy en Streamlit Cloud (para compartir el link)

1. Sube este directorio a un **repositorio de GitHub**
2. Ve a [share.streamlit.io](https://share.streamlit.io/)
3. Conecta tu cuenta de GitHub
4. Selecciona el repo → archivo `app.py`
5. En **Advanced settings** → **Secrets**, agrega:
   ```toml
   GROQ_API_KEY = "gsk_tu_key_aqui"
   ```
6. Click **Deploy**
7. Comparte el link con los músicos

> ⚠️ **Nota**: En Streamlit Cloud (plan gratis), los archivos JSON se pierden si la app se reinicia. Para entrevistas reales, descarga el CSV regularmente.

## Uso

### Para el músico (usuario)
1. Abre el link
2. Conversa con Venom sobre su experiencia con DAWs
3. Dura 5-10 minutos
4. Al final, Venom genera un perfil automáticamente

### Para Ricardo/Nicolás (admins)
- **Modo Demo**: Toggle en la sidebar para ver info técnica y el perfil JSON
- **Revelar proyecto**: Toggle para cambiar entre modo stealth (investigación) y modo reveal (mencionar el DAW)
- **Exportar CSV**: Botón en la sidebar para descargar todas las entrevistas
- **Nueva entrevista**: Botón para resetear y empezar otra

## Estructura

```
agente-entrevistador/
├── app.py              # App principal (todo en un archivo)
├── requirements.txt    # Dependencias Python
├── .env.example        # Template para API key
├── .env                # Tu API key real (NO subir a GitHub)
├── .gitignore          # Ignora .env y data/
├── .streamlit/
│   └── config.toml     # Tema visual (púrpura oscuro)
├── data/
│   └── entrevistas/    # JSONs de entrevistas (se crea automático)
└── README.md           # Este archivo
```

## Configuración avanzada

En `app.py` puedes cambiar:

```python
AGENT_NAME = "Venom"                       # Nombre del agente
MODEL = "llama-3.3-70b-versatile"          # Groq: llama-3.3-70b-versatile, llama-3.1-8b-instant, mixtral-8x7b-32768
```

## Resolución de problemas

| Problema | Solución |
|----------|----------|
| "No se encontró API key" | Verifica que la key esté en .env, secrets, o el sidebar |
| "Error conectando con API" | Verifica que la key sea válida en console.groq.com |
| La app no abre | ¿Instalaste las dependencias? `pip install -r requirements.txt` |
| El agente no genera perfil | Puede pasar si la conversación fue muy corta. Intenta responder más |

---

*Proyecto DAW Inteligente — Ricardo & Nicolás — 2026*
