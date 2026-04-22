"""
🎵 Venom — Agente Entrevistador de Músicos
Proyecto DAW Inteligente | Ricardo & Nicolás
Stack: Streamlit + Groq API (Llama 3.3 70B)

Para correr localmente:
    streamlit run app.py
"""

import streamlit as st
import json
import os
import csv
import re
import io
import uuid
from datetime import datetime
from pathlib import Path

try:
    import gspread
    from google.oauth2.service_account import Credentials
    GSPREAD_AVAILABLE = True
except ImportError:
    GSPREAD_AVAILABLE = False

# Cargar .env si existe (para desarrollo local)
try:
    from dotenv import load_dotenv
    load_dotenv()
except ImportError:
    pass  # No pasa nada si no está instalado


# ═════════════════════════════════════════════
# CONFIGURACIÓN
# ═════════════════════════════════════════════
AGENT_NAME = "Venom"
MODEL = "meta-llama/llama-3.3-70b-instruct"  # OpenRouter: Llama 3.3 70B ($0.10/M in, $0.32/M out)
MAX_CONTEXT_MESSAGES = 12  # Máximo de mensajes (sin system) a enviar a la API
DATA_DIR = Path("data/entrevistas")
SHEET_ID = "1pkEpG_Mz5EZa_qiDz8ZqF8rLXbd4ersE8uqSOiDzmzc"

# Columnas del Google Sheet (mismo orden que los headers)
SHEET_COLUMNS = [
    "timestamp", "nombre", "daw_principal", "experiencia_años", "nicho",
    "herramientas_adicionales", "dolor_principal", "dolores_secundarios",
    "funciones_amadas", "funciones_odiadas", "momento_creatividad_cortada",
    "cosas_fuera_del_daw", "flujo_trabajo_resumen", "suenos_daw_ideal",
    "opinion_ia", "beta_tester", "insights_clave", "nivel_tecnico"
]


# ═════════════════════════════════════════════
# SYSTEM PROMPT
# ═════════════════════════════════════════════
def get_system_prompt(reveal_project=False):
    """Genera el system prompt del agente.
    
    Args:
        reveal_project: Si True, menciona el proyecto DAW.
                        Si False, modo stealth (investigación genérica).
    """
    if reveal_project:
        contexto = (
            "Estás recopilando opiniones para un proyecto de vanguardia: "
            "crear un DAW innovador que busca ser intuitivo, amigable, dinámico "
            "y adaptable a las necesidades de cada músico, con ayuda de la IA."
        )
    else:
        contexto = (
            "Estás recopilando opiniones de músicos para un proyecto de "
            "investigación sobre la experiencia de usuario en herramientas "
            "de producción musical."
        )
    
    return f"""Eres {AGENT_NAME}, un agente de investigación musical. Tu misión es entrevistar músicos sobre su experiencia con DAWs (Digital Audio Workstations).

## PERSONALIDAD
- Casual, cercano, como un colega músico que entiende el mundo del audio
- Adaptas tu lenguaje al del usuario: si habla técnico, respondes técnico. Si habla coloquial, respondes coloquial
- Nunca condescendiente. Nunca suenas como vendedor.
- Conciso pero cálido

## CONTEXTO
{contexto}

## CONOCIMIENTO
- Conoces todos los DAWs principales: Ableton Live, FL Studio, Logic Pro, Reaper, Pro Tools, Cubase, Bitwig Studio, Ardour, Studio One
- Entiendes middleware de game audio: Wwise, FMOD
- Sabes de plugins VST/AU/CLAP, síntesis, mezcla, mastering, sound design
- Si el usuario trabaja en game audio, sabes que probablemente también usa middleware aparte del DAW
- Entiendes las diferencias entre producción, mezcla, mastering, sound design, composición, beat-making
- Conoces conceptos como: piano roll, mixer, timeline, session view, routing, buses, sends, sidechain, automation, freeze/render

## FLUJO DE LA ENTREVISTA
Guía la conversación naturalmente a través de estas fases. NO las anuncies como "fase 1, fase 2". Transiciona de forma conversacional y natural.

**INICIO** (tu primer mensaje):
- Preséntate como {AGENT_NAME}
- Da contexto breve sobre la investigación
- Pregunta: ¿Qué DAW usas principalmente? ¿Hace cuánto? ¿Para qué tipo de música o trabajo?
- Sé conciso: máximo 4-5 líneas

**LO BUENO** (1-2 intercambios):
- ¿Hay alguna función o parte de la interfaz que ames o sientas que está muy bien diseñada? ¿Por qué te gusta tanto?
- Escucha activamente y profundiza brevemente si es interesante

**LO MALO** (2-3 intercambios — SECCIÓN MÁS IMPORTANTE):
- ¿Cuál es la tarea técnica o rutinaria que más detestas o que más tiempo te roba al trabajar?
- ¿Alguna función que uses constantemente pero te resulte incómoda, confusa o frustrante? ¿Por qué?
- ¿Recuerdas algún momento donde el DAW cortó tu creatividad o inspiración? ¿Qué pasó?
- ¿Hay algo que hagas FUERA del DAW que desearías poder hacer dentro?
(No preguntes TODAS — adapta según lo que ya respondió)

**FLUJO DE TRABAJO** (1-2 intercambios):
- Pide que describa su flujo de trabajo típico de forma conversacional
- Busca entender: herramientas adicionales que usa, cómo organiza samples/presets/proyectos, si colabora con otros

**DAW SOÑADO** (1-2 intercambios):
- Si pudieras diseñar tu DAW ideal desde cero, ¿qué tendría?
- ¿Cómo imaginas que la inteligencia artificial podría ayudarte? ¿Hay algo que la IA NO debería hacer?

**CIERRE** (1 mensaje):
- Agradece genuinamente su tiempo y respuestas
- Pregunta si le gustaría ser de los primeros en probar herramientas nuevas cuando estén disponibles
- Despídete de forma cálida

## REGLAS ESTRICTAS
- Máximo 2 preguntas por mensaje
- Si el usuario da respuestas cortas → profundiza: "¿podrías darme un ejemplo concreto?" o "¿qué pasa exactamente cuando eso ocurre?"
- Si el usuario se extiende → escucha y haz follow-up inteligente basado en lo que dijo
- NO es un formulario. Es una CONVERSACIÓN natural entre colegas.
- NO repitas preguntas que el usuario ya respondió implícitamente
- Adapta preguntas al nicho (game audio → middleware y audio interactivo, beats → samples y loops, podcast → edición de voz)
- La entrevista completa: 6-10 mensajes tuyos, duración 5-10 minutos
- Si detectas que el usuario quiere terminar antes, respeta su tiempo y cierra amablemente

## GENERACIÓN DE PERFIL
Después de tu mensaje de cierre/despedida, genera INMEDIATAMENTE un bloque JSON con el perfil del músico.
El JSON va envuelto en ```json ```. Usa EXACTAMENTE este formato:

```json
{{
  "nombre": "nombre si lo mencionó, sino Anónimo",
  "daw_principal": "nombre del DAW",
  "experiencia_años": "estimación numérica o rango",
  "nicho": "game_audio | produccion_musical | beats_lofi | podcast | sound_design | electronica | grabacion_bandas | composicion | dj | otro",
  "herramientas_adicionales": ["lista de herramientas/plugins/middleware mencionados"],
  "dolor_principal": "resumen en 1-2 oraciones del mayor dolor",
  "dolores_secundarios": ["lista de otros dolores mencionados"],
  "funciones_amadas": ["funciones o interfaces que le gustan y por qué"],
  "funciones_odiadas": ["funciones o interfaces que le frustran y por qué"],
  "momento_creatividad_cortada": "descripción del momento si lo mencionó, o null",
  "cosas_fuera_del_daw": "qué hace fuera del DAW que querría dentro, o null",
  "flujo_trabajo_resumen": "resumen breve de su workflow",
  "suenos_daw_ideal": ["lista de features deseadas para un DAW ideal"],
  "opinion_ia": "resumen de su postura sobre IA en DAWs",
  "beta_tester": true,
  "insights_clave": "1-2 oraciones con lo más valioso para diseño de producto",
  "nivel_tecnico": "principiante | intermedio | avanzado | profesional"
}}
```"""


# ═════════════════════════════════════════════
# ALMACENAMIENTO
# ═════════════════════════════════════════════
def get_sheets_client():
    """Crea cliente gspread usando credenciales de Streamlit Secrets o archivo local."""
    if not GSPREAD_AVAILABLE:
        return None
    
    scopes = [
        "https://www.googleapis.com/auth/spreadsheets",
        "https://www.googleapis.com/auth/drive"
    ]
    
    try:
        # Primero intenta Streamlit Secrets (para Streamlit Cloud)
        creds_dict = dict(st.secrets["gcp_service_account"])
        creds = Credentials.from_service_account_info(creds_dict, scopes=scopes)
        return gspread.authorize(creds)
    except (KeyError, FileNotFoundError):
        pass
    
    # Fallback: archivo local service_account.json
    sa_path = Path("service_account.json")
    if sa_path.exists():
        creds = Credentials.from_service_account_file(str(sa_path), scopes=scopes)
        return gspread.authorize(creds)
    
    return None


def save_to_sheets(profile_data):
    """Guarda el perfil del músico como nueva fila en Google Sheets."""
    gc = get_sheets_client()
    if not gc:
        return False
    
    try:
        sheet = gc.open_by_key(SHEET_ID).sheet1
        
        # Construir fila en el orden correcto de columnas
        row = []
        for col in SHEET_COLUMNS:
            if col == "timestamp":
                row.append(datetime.now().strftime("%Y-%m-%d %H:%M:%S"))
            else:
                value = profile_data.get(col, "")
                # Listas y dicts se convierten a string legible
                if isinstance(value, (list, dict)):
                    row.append(json.dumps(value, ensure_ascii=False))
                elif isinstance(value, bool):
                    row.append("Sí" if value else "No")
                else:
                    row.append(str(value) if value is not None else "")
        
        sheet.append_row(row, value_input_option="USER_ENTERED")
        return True
    except Exception as e:
        st.warning(f"⚠️ No se pudo guardar en Google Sheets: {e}")
        return False


def save_message_to_sheets(session_id, role, content):
    """Guarda un mensaje individual en la hoja 'conversaciones' de Google Sheets.
    Esto permite recuperar entrevistas aunque el músico cierre el navegador."""
    gc = get_sheets_client()
    if not gc:
        return False
    
    try:
        spreadsheet = gc.open_by_key(SHEET_ID)
        
        # Obtener o crear la hoja 'conversaciones'
        try:
            conv_sheet = spreadsheet.worksheet("conversaciones")
        except gspread.exceptions.WorksheetNotFound:
            conv_sheet = spreadsheet.add_worksheet(
                title="conversaciones", rows=1000, cols=4
            )
            conv_sheet.append_row(
                ["session_id", "timestamp", "role", "content"],
                value_input_option="USER_ENTERED"
            )
        
        # Truncar contenido para no exceder límites de celdas (50k chars)
        content_clean = clean_display_text(content)
        if len(content_clean) > 10000:
            content_clean = content_clean[:10000] + "... [truncado]"
        
        conv_sheet.append_row(
            [
                session_id,
                datetime.now().strftime("%Y-%m-%d %H:%M:%S"),
                role,
                content_clean
            ],
            value_input_option="USER_ENTERED"
        )
        return True
    except Exception:
        return False


def save_interview(profile_data, messages):
    """Guarda la entrevista completa (perfil + conversación) en un archivo JSON."""
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    
    timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
    nombre = profile_data.get("nombre", "anonimo")
    nombre_clean = re.sub(r'[^\w]', '_', nombre.lower())[:20]
    filename = f"{timestamp}_{nombre_clean}.json"
    
    data = {
        "perfil": profile_data,
        "conversacion": [
            {"rol": m["role"], "contenido": m["content"]}
            for m in messages if m["role"] != "system"
        ],
        "metadata": {
            "fecha": datetime.now().isoformat(),
            "agente": AGENT_NAME,
            "modelo": MODEL,
            "total_mensajes_usuario": len([m for m in messages if m["role"] == "user"])
        }
    }
    
    filepath = DATA_DIR / filename
    with open(filepath, "w", encoding="utf-8") as f:
        json.dump(data, f, ensure_ascii=False, indent=2)
    
    return filepath


def extract_profile_json(text):
    """Extrae el perfil JSON del mensaje del agente (busca bloque ```json```)."""
    match = re.search(r'```json\s*(\{.*?\})\s*```', text, re.DOTALL)
    if match:
        try:
            return json.loads(match.group(1))
        except json.JSONDecodeError:
            pass
    return None


def clean_display_text(text):
    """Remueve bloques JSON del texto visible al usuario."""
    cleaned = re.sub(r'```json\s*\{.*?\}\s*```', '', text, flags=re.DOTALL)
    return cleaned.strip()


def get_all_profiles():
    """Lee todos los perfiles de entrevistas guardadas."""
    profiles = []
    if DATA_DIR.exists():
        for f in sorted(DATA_DIR.glob("*.json")):
            try:
                with open(f, "r", encoding="utf-8") as file:
                    data = json.load(file)
                    if "perfil" in data:
                        profiles.append(data["perfil"])
            except (json.JSONDecodeError, KeyError):
                continue
    return profiles


def profiles_to_csv():
    """Convierte todos los perfiles a formato CSV (string)."""
    profiles = get_all_profiles()
    if not profiles:
        return None
    
    # Recopilar todas las keys manteniendo orden
    all_keys = []
    for p in profiles:
        for k in p.keys():
            if k not in all_keys:
                all_keys.append(k)
    
    output = io.StringIO()
    writer = csv.DictWriter(output, fieldnames=all_keys)
    writer.writeheader()
    
    for p in profiles:
        row = {}
        for k in all_keys:
            v = p.get(k, "")
            # Listas y dicts se convierten a string JSON para CSV
            row[k] = json.dumps(v, ensure_ascii=False) if isinstance(v, (list, dict, bool)) else str(v)
        writer.writerow(row)
    
    return output.getvalue()


# ═════════════════════════════════════════════
# CLIENTE API
# ═════════════════════════════════════════════
def get_client():
    """Crea el cliente OpenAI apuntando a OpenRouter (producción) o Groq (local fallback).
    Busca la API key en este orden: OpenRouter secrets/env → Groq secrets/env → sidebar input.
    """
    from openai import OpenAI
    
    # 1. OpenRouter (producción)
    api_key = None
    try:
        api_key = st.secrets.get("OPENROUTER_API_KEY")
    except (KeyError, FileNotFoundError):
        pass
    if not api_key:
        api_key = os.getenv("OPENROUTER_API_KEY", "")
    if api_key:
        return OpenAI(api_key=api_key, base_url="https://openrouter.ai/api/v1")
    
    # 2. Groq (fallback local)
    api_key = st.session_state.get("api_key_input", "")
    if not api_key:
        try:
            api_key = st.secrets["GROQ_API_KEY"]
        except (KeyError, FileNotFoundError):
            pass
    if not api_key:
        api_key = os.getenv("GROQ_API_KEY", "")
    if api_key:
        return OpenAI(api_key=api_key, base_url="https://api.groq.com/openai/v1")
    
    return None


# ═════════════════════════════════════════════
# APP PRINCIPAL
# ═════════════════════════════════════════════
def main():
    # ── Configuración de página ──
    st.set_page_config(
        page_title=f"🎵 {AGENT_NAME} — Entrevista Musical",
        page_icon="🎵",
        layout="centered"
    )
    
    # ── Inicializar estado ──
    if "messages" not in st.session_state:
        st.session_state.messages = []
    if "interview_complete" not in st.session_state:
        st.session_state.interview_complete = False
    if "profile_data" not in st.session_state:
        st.session_state.profile_data = None
    if "session_id" not in st.session_state:
        st.session_state.session_id = str(uuid.uuid4())[:8]
    
    # ── Detectar si hay key preconfigurada (producción) ──
    has_preconfigured_key = False
    try:
        if st.secrets.get("OPENROUTER_API_KEY") or st.secrets.get("GROQ_API_KEY"):
            has_preconfigured_key = True
    except (KeyError, FileNotFoundError):
        pass
    if not has_preconfigured_key and (os.getenv("OPENROUTER_API_KEY") or os.getenv("GROQ_API_KEY")):
        has_preconfigured_key = True
    
    # ── Sidebar ──
    demo_mode = False
    reveal_project = False
    
    with st.sidebar:
        st.title(f"🎵 {AGENT_NAME}")
        st.caption("Entrevistador de Músicos")
        
        if not has_preconfigured_key:
            # Solo mostrar controles de dev cuando NO hay key preconfigurada
            st.divider()
            
            api_key = st.text_input(
                "🔑 API Key (Groq)",
                type="password",
                value="",
                help="Tu API key de console.groq.com"
            )
            if api_key:
                st.session_state.api_key_input = api_key
            
            st.divider()
            
            demo_mode = st.toggle("🔧 Modo Demo", value=False)
            
            if demo_mode:
                reveal_project = st.toggle(
                    "📢 Revelar proyecto DAW",
                    value=False,
                    help="ON = menciona que están creando un DAW. OFF = investigación genérica."
                )
            
            st.divider()
            
            n_profiles = len(get_all_profiles())
            st.metric("📊 Entrevistas guardadas", n_profiles)
            
            csv_data = profiles_to_csv()
            if csv_data:
                st.download_button(
                    "📥 Exportar CSV",
                    csv_data,
                    file_name=f"entrevistas_{datetime.now().strftime('%Y%m%d')}.csv",
                    mime="text/csv",
                    use_container_width=True
                )
        
        st.divider()
        
        # Botón nueva entrevista (siempre visible)
        if st.button("🔄 Nueva entrevista", use_container_width=True):
            st.session_state.messages = []
            st.session_state.interview_complete = False
            st.session_state.profile_data = None
            st.session_state.session_id = str(uuid.uuid4())[:8]
            st.rerun()
    
    # ── Verificar API Key ──
    client = get_client()
    if not client:
        st.title(f"🎵 {AGENT_NAME}")
        st.warning("👈 Ingresa tu API key de Groq en la barra lateral para comenzar.")
        st.info(
            "**¿Cómo obtener tu API key?**\n\n"
            "1. Ve a [console.groq.com](https://console.groq.com/)\n"
            "2. Inicia sesión con tu cuenta\n"
            "3. Ve a **API Keys** en el menú lateral\n"
            "4. Click en **Create API Key**\n"
            "5. Copia la key y pégala en la barra lateral"
        )
        return
    
    # ── Título principal ──
    st.title(f"🎵 {AGENT_NAME}")
    st.caption("Cuéntanos tu experiencia con DAWs")
    
    # ── Generar mensaje de bienvenida (primera vez) ──
    if not st.session_state.messages:
        system_prompt = get_system_prompt(reveal_project=reveal_project)
        st.session_state.messages = [
            {"role": "system", "content": system_prompt}
        ]
        
        with st.spinner("🎵 Iniciando entrevista..."):
            try:
                response = client.chat.completions.create(
                    model=MODEL,
                    messages=st.session_state.messages + [
                        {"role": "user", "content": "[SISTEMA: El músico acaba de conectarse. Genera tu bienvenida.]"}
                    ],
                    temperature=0.7,
                    max_tokens=300
                )
                intro = response.choices[0].message.content
                st.session_state.messages.append(
                    {"role": "assistant", "content": intro}
                )
                save_message_to_sheets(
                    st.session_state.session_id, "assistant", intro
                )
            except Exception as e:
                st.error(f"Error conectando con la API: {e}")
                st.session_state.messages = []
                return
        
        st.rerun()
    
    # ── Mostrar historial de mensajes ──
    for msg in st.session_state.messages:
        if msg["role"] == "system":
            continue
        
        avatar = "🎵" if msg["role"] == "assistant" else "🎤"
        with st.chat_message(msg["role"], avatar=avatar):
            display = clean_display_text(msg["content"])
            if display:
                st.markdown(display)
    
    # ── Entrevista completada ──
    if st.session_state.interview_complete:
        st.success("✅ ¡Entrevista completada y guardada! Gracias por participar.")
        
        if st.session_state.profile_data and demo_mode:
            with st.expander("📊 Perfil generado", expanded=True):
                st.json(st.session_state.profile_data)
        return
    
    # ── Chat input del usuario ──
    if prompt := st.chat_input("Escribe tu respuesta..."):
        # Agregar mensaje del usuario y guardar en Sheets
        st.session_state.messages.append({"role": "user", "content": prompt})
        save_message_to_sheets(st.session_state.session_id, "user", prompt)
        
        with st.chat_message("user", avatar="🎤"):
            st.markdown(prompt)
        
        # Obtener respuesta del agente
        with st.chat_message("assistant", avatar="🎵"):
            with st.spinner(""):
                try:
                    # Ventana deslizante: system + últimos N mensajes
                    msgs = st.session_state.messages
                    system_msgs = [m for m in msgs if m["role"] == "system"]
                    non_system = [m for m in msgs if m["role"] != "system"]
                    context = system_msgs + non_system[-MAX_CONTEXT_MESSAGES:]
                    
                    response = client.chat.completions.create(
                        model=MODEL,
                        messages=context,
                        temperature=0.7,
                        max_tokens=800
                    )
                    reply = response.choices[0].message.content
                except Exception as e:
                    st.error(f"Error: {e}")
                    return
            
            # Mostrar texto (sin el JSON interno)
            display = clean_display_text(reply)
            if display:
                st.markdown(display)
            
            # Detectar si la entrevista terminó (perfil JSON generado)
            profile = extract_profile_json(reply)
        
        # Guardar mensaje y persistir en Sheets
        st.session_state.messages.append({"role": "assistant", "content": reply})
        save_message_to_sheets(st.session_state.session_id, "assistant", reply)
        
        # Si se detectó perfil → guardar entrevista
        if profile:
            save_interview(profile, st.session_state.messages)
            sheets_ok = save_to_sheets(profile)
            st.session_state.interview_complete = True
            st.session_state.profile_data = profile
            if sheets_ok:
                st.toast("💾 Entrevista guardada en Google Sheets", icon="✅")
            else:
                st.toast("💾 Entrevista guardada localmente", icon="✅")
            st.rerun()
    
    # ── Debug info (solo en modo demo) ──
    if demo_mode:
        st.divider()
        with st.expander("🔧 System Prompt"):
            st.code(get_system_prompt(reveal_project), language="text")
        with st.expander("🔧 Mensajes en memoria"):
            st.write(f"Total: {len(st.session_state.messages)} mensajes")
            for i, m in enumerate(st.session_state.messages):
                if m["role"] != "system":
                    st.text(f"[{i}] {m['role']}: {m['content'][:100]}...")


if __name__ == "__main__":
    main()
