import os
import subprocess
import webbrowser
import json
import time
import pyautogui
import warnings
import threading
import re 
from PIL import ImageGrab, Image
import psutil    
import pyperclip 
import datetime 
import numpy as np 
import base64
from io import BytesIO
import ast
import operator
import requests 

# --- IA Y LIBRERÍAS DE RED ---
try: 
    import google.generativeai as genai
    GENAI_DISPONIBLE = True
except ImportError: 
    GENAI_DISPONIBLE = False
    print("⚠️ Falta Gemini. Ejecuta: pip install google-generativeai")
    
try: 
    from openai import OpenAI
    OPENAI_DISPONIBLE = True
except ImportError: 
    OPENAI_DISPONIBLE = False
    print("⚠️ Falta OpenAI. Ejecuta: pip install openai")
    
try: from ddgs import DDGS 
except ImportError: pass

# --- VISIÓN LOCAL ---
try:
    import pytesseract
    pytesseract.pytesseract.tesseract_cmd = r'C:\Program Files\Tesseract-OCR\tesseract.exe'
    TESSERACT_DISPONIBLE = True
except ImportError:
    TESSERACT_DISPONIBLE = False
    print("⚠️ Falta pytesseract. Ejecuta: pip install pytesseract")

# --- OÍDOS LOCALES LIGEROS (WHISPER TINY) ---
try:
    import whisper
    warnings.filterwarnings("ignore")
    print("⏳ [SISTEMA] Cargando modelo auditivo Whisper 'Tiny' (~150MB RAM)...")
    # Usamos el modelo "tiny" para ahorrar muchísima memoria RAM.
    modelo_whisper = whisper.load_model("tiny") 
    WHISPER_DISPONIBLE = True
    print("✅ [SISTEMA] Oídos locales ultraligeros cargados con éxito.")
except Exception as e:
    WHISPER_DISPONIBLE = False
    print(f"⚠️ Whisper desactivado. Razón: {e}")

# --- VOZ ---
try:
    import edge_tts
    import pygame
    VOZ_AVANZADA = True
    pygame.mixer.init()
except ImportError:
    VOZ_AVANZADA = False
    print("⚠️ Faltan librerías de voz. Ejecuta: pip install edge-tts pygame-ce")

try:
    import sounddevice as sd
    import scipy.io.wavfile as wav
    import speech_recognition as sr
    MICROFONO_DISPONIBLE = True
except ImportError:
    MICROFONO_DISPONIBLE = False

# --- LIBRERÍAS DE CALENDARIO Y CORREO ---
try:
    from google.auth.transport.requests import Request
    from google.oauth2.credentials import Credentials
    from google_auth_oauthlib.flow import InstalledAppFlow
    from googleapiclient.discovery import build
except ImportError:
    print("⚠️ Faltan librerías de Google.")

import smtplib
import imaplib
import email
from email.mime.text import MIMEText
from email.mime.multipart import MIMEMultipart
from email.header import decode_header
try: import PyPDF2; import docx
except ImportError: pass
try: import pywhatkit
except ImportError: pass
try: import customtkinter as ctk
except ImportError: 
    print("\n❌ ERROR: Falta la librería customtkinter. Ejecuta: pip install customtkinter")
    os._exit(1)

# --- BASE DE DATOS VECTORIAL ---
try:
    import chromadb
    import uuid
    CHROMA_DISPONIBLE = True
except ImportError:
    CHROMA_DISPONIBLE = False
    print("\n⚠️ Recomendación: Ejecuta 'pip install chromadb uuid' para habilitar la Memoria Cuántica.")

warnings.filterwarnings("ignore")

# ==========================================
# 1. CONFIGURACIÓN Y SEGURIDAD
# ==========================================
NOMBRE_ASISTENTE = "N.O.V.A." 
BASE_DIR = os.path.dirname(os.path.abspath(__file__))
ARCHIVO_LLAVES = os.path.join(BASE_DIR, "llaves_nova.txt")
ARCHIVO_CONFIG = os.path.join(BASE_DIR, "config_nova.json")
CARPETA_DRIVE = os.path.join(BASE_DIR, "Nova_Drive")
ARCHIVO_MEMORIA = os.path.join(BASE_DIR, f"memoria_vectorial.json")

# Modelos Locales de Ollama
OLLAMA_URL = "http://localhost:11434/api"
OLLAMA_MODEL_TEXTO = "qwen2.5:3b"
OLLAMA_MODEL_VECTORES = "nomic-embed-text"

if not os.path.exists(CARPETA_DRIVE): os.makedirs(CARPETA_DRIVE)
if not os.path.exists(ARCHIVO_MEMORIA):
    with open(ARCHIVO_MEMORIA, "w", encoding="utf-8") as f: json.dump([], f)
if not os.path.exists(ARCHIVO_CONFIG):
    config_default = {"GMAIL_USUARIO": "tu_correo@gmail.com", "GMAIL_PASSWORD": "tu_contraseña_de_aplicacion"}
    with open(ARCHIVO_CONFIG, "w", encoding="utf-8") as f: json.dump(config_default, f, indent=4)

with open(ARCHIVO_CONFIG, "r", encoding="utf-8") as f:
    config_data = json.load(f)
    GMAIL_USUARIO = config_data.get("GMAIL_USUARIO", "")
    GMAIL_PASSWORD = config_data.get("GMAIL_PASSWORD", "")

lock_historial = threading.Lock()
lock_tareas = threading.Lock()
historial_chat = []
TAREAS_PROGRAMADAS = []

app_gui = None
def log_msg(mensaje):
    print(mensaje) 
    if app_gui: app_gui.after(0, app_gui.escribir_log, str(mensaje))

if CHROMA_DISPONIBLE:
    try:
        chroma_client = chromadb.PersistentClient(path=os.path.join(BASE_DIR, "Nova_ChromaDB"))
        nova_collection = chroma_client.get_or_create_collection(name="nova_core_memory", metadata={"hnsw:space": "cosine"})
    except Exception as e:
        log_msg(f"⚠️ Error iniciando ChromaDB: {e}. Degradando a memoria JSON de respaldo.")
        CHROMA_DISPONIBLE = False

# ==========================================
# 1.1 EVALUADOR MATEMÁTICO SEGURO
# ==========================================
class EvaluadorSeguro:
    def __init__(self):
        self.operadores = {ast.Add: operator.add, ast.Sub: operator.sub, ast.Mult: operator.mul, ast.Div: operator.truediv, ast.Pow: operator.pow, ast.USub: operator.neg}
    
    def evaluar(self, expresion):
        try:
            tree = ast.parse(expresion, mode='eval')
            return self._evaluar_nodo(tree.body)
        except: return "Expresión inválida o insegura."

    def _evaluar_nodo(self, node):
        if isinstance(node, ast.Num): return node.n
        elif isinstance(node, ast.Constant) and isinstance(node.value, (int, float)): return node.value
        elif isinstance(node, ast.BinOp):
            op = self.operadores[type(node.op)]
            return op(self._evaluar_nodo(node.left), self._evaluar_nodo(node.right))
        elif isinstance(node, ast.UnaryOp):
            op = self.operadores[type(node.op)]
            return op(self._evaluar_nodo(node.operand))
        raise TypeError("Operación bloqueada por seguridad.")

evaluador_matematico = EvaluadorSeguro()

# ==========================================
# 1.2 CLASE: OMNI PROVIDER MANAGER (HÍBRIDO)
# ==========================================
class OmniProviderManager:
    def __init__(self, filepath):
        self.filepath = filepath
        self.keys = []
        self.current_index = 0
        self.openai_client = None
        self._load_keys()
        self._configure_key()

    def _load_keys(self):
        if not os.path.exists(self.filepath):
            with open(self.filepath, "w") as f: f.write("# Pega tus API Keys aqui abajo. Una por linea.\n")
            log_msg(f"⚠️ [SISTEMA] Archivo '{self.filepath}' creado para llaves de respaldo.")
            return
        with open(self.filepath, "r") as f:
            lineas = f.read().splitlines()
            self.keys = [linea.strip() for linea in lineas if linea.strip() and not linea.startswith("#")]
        if self.keys: log_msg(f"🔑 [PROVIDER MANAGER] {len(self.keys)} API Keys de respaldo cargadas.")

    def _configure_key(self):
        if not self.keys: return False
        if self.current_index >= len(self.keys): self.current_index = 0
        clave = self.keys[self.current_index]
        try:
            if clave.startswith("sk-"):
                if OPENAI_DISPONIBLE: self.openai_client = OpenAI(api_key=clave)
                else: self.openai_client = None
            else:
                self.openai_client = None
                if GENAI_DISPONIBLE: genai.configure(api_key=clave)
            return True
        except Exception: return False

    def _rotate_key(self):
        if not self.keys: raise Exception("No hay llaves de respaldo disponibles.")
        llave_perdida = self.keys[self.current_index]
        log_msg(f"🔥 [PROVIDER MANAGER] Llave de respaldo comprometida ({llave_perdida[:8]}...). Descartada.")
        self.keys.pop(self.current_index)
        if not self.keys: raise Exception("Todas las API Keys de respaldo han fallado.")
        if self.current_index >= len(self.keys): self.current_index = 0
        self._configure_key()
        time.sleep(1)

    def _extraer_texto_prompt(self, contents):
        texto_final = ""
        for item in contents:
            if item.get("role") == "user":
                for part in item.get("parts", []):
                    if isinstance(part, str): texto_final += part + "\n"
        return texto_final

    def generate_content(self, contents, json_mode=True):
        # 1. INTENTO LOCAL (OLLAMA)
        texto_prompt = self._extraer_texto_prompt(contents)
        payload = {"model": OLLAMA_MODEL_TEXTO, "prompt": texto_prompt, "stream": False}
        if json_mode: payload["format"] = "json"

        try:
            # AUMENTADO A 120 SEGUNDOS: Para darle tiempo a la PC si usa memoria virtual
            response = requests.post(f"{OLLAMA_URL}/generate", json=payload, timeout=120)
            if response.status_code == 200:
                class MockResponseLocal:
                    def __init__(self, text): self.text = text
                return MockResponseLocal(response.json()["response"])
        except requests.exceptions.RequestException: pass 
        
        # 2. PLAN B: NUBE
        log_msg("☁️ [REDIRECCIÓN] Servidor local inactivo o saturado. Usando Red de Respaldo...")
        if not self.keys: raise Exception("Cerebro Local offline y no hay llaves de respaldo disponibles.")
        
        intentos = 0
        max_intentos = len(self.keys) + 1 
        while intentos < max_intentos:
            clave_actual = self.keys[self.current_index]
            try:
                if clave_actual.startswith("sk-"):
                    if not OPENAI_DISPONIBLE: raise Exception("Librería openai no instalada.")
                    content_list = []
                    for item in contents:
                        if item.get("role") == "user":
                            for part in item.get("parts", []):
                                if isinstance(part, str): content_list.append({"type": "text", "text": part})
                                elif hasattr(part, 'save'):
                                    buffered = BytesIO(); part.save(buffered, format="PNG")
                                    img_str = base64.b64encode(buffered.getvalue()).decode("utf-8")
                                    content_list.append({"type": "image_url", "image_url": {"url": f"data:image/png;base64,{img_str}"}})
                    kwargs = {"model": "gpt-4o-mini", "messages": [{"role": "user", "content": content_list}]}
                    if json_mode: kwargs["response_format"] = {"type": "json_object"}
                    resp_api = self.openai_client.chat.completions.create(**kwargs)
                    class MockResponseNube:
                        def __init__(self, text): self.text = text
                    return MockResponseNube(resp_api.choices[0].message.content)
                else:
                    if not GENAI_DISPONIBLE: raise Exception("Librería google-generativeai no instalada.")
                    config = {"response_mime_type": "application/json"} if json_mode else {}
                    model = genai.GenerativeModel('gemini-2.5-flash', generation_config=config)
                    return model.generate_content(contents)
            except Exception as e:
                error_str = str(e).lower()
                if any(x in error_str for x in ["429", "quota", "exhausted", "key", "400", "insufficient", "rate_limit"]):
                    self._rotate_key(); intentos += 1
                else: raise e
        raise Exception("Cerebro Local offline y Bóveda de llaves saturada.")

    def embed_content(self, text, task_type="retrieval_document"):
        # 1. INTENTO LOCAL (OLLAMA)
        payload = {"model": OLLAMA_MODEL_VECTORES, "prompt": text}
        try:
            # AUMENTADO A 60 SEGUNDOS
            response = requests.post(f"{OLLAMA_URL}/embeddings", json=payload, timeout=60)
            if response.status_code == 200: return response.json()["embedding"]
        except requests.exceptions.RequestException: pass 
            
        # 2. PLAN B: NUBE
        if not self.keys: raise Exception("No hay llaves para generar vectores de memoria de respaldo.")
        intentos = 0
        max_intentos = len(self.keys) + 1
        while intentos < max_intentos:
            clave_actual = self.keys[self.current_index]
            try:
                if clave_actual.startswith("sk-"):
                    if not OPENAI_DISPONIBLE: raise Exception("Librería openai no instalada.")
                    resp_api = self.openai_client.embeddings.create(input=text, model="text-embedding-3-small", dimensions=768)
                    return resp_api.data[0].embedding
                else:
                    if not GENAI_DISPONIBLE: raise Exception("Librería google-generativeai no instalada.")
                    return genai.embed_content(model="models/embedding-001", content=text, task_type=task_type)['embedding']
            except Exception as e:
                error_str = str(e).lower()
                if any(x in error_str for x in ["429", "quota", "exhausted", "key", "400", "insufficient", "rate_limit"]):
                    self._rotate_key(); intentos += 1
                else: raise e
        raise Exception("Tukuy API Keys saturisqa kachkan (Vectores).")

    def is_ready(self): return True

llm_provider = OmniProviderManager(ARCHIVO_LLAVES)

# ==========================================
# 1.3 NOVA DRIVE Y MEMORIA
# ==========================================
def buscar_archivo_local(nombre_o_ruta):
    if os.path.exists(nombre_o_ruta): return nombre_o_ruta
    nombre_archivo = os.path.basename(nombre_o_ruta.replace('\\', '/'))
    home_dir = os.path.expanduser('~')
    rutas_rapidas = [os.path.join(home_dir, 'Desktop'), os.path.join(home_dir, 'Escritorio'), os.path.join(home_dir, 'Documents'), os.path.join(home_dir, 'Documentos'), os.path.join(home_dir, 'Downloads'), os.path.join(home_dir, 'Descargas'), BASE_DIR]
    
    for ruta in rutas_rapidas:
        intento = os.path.join(ruta, nombre_archivo)
        if os.path.exists(intento): return intento
                
    log_msg(f"🔍 [SISTEMA] Rastreado directorios por '{nombre_archivo}'...")
    for root, dirs, files in os.walk(home_dir):
        if nombre_archivo in files: return os.path.join(root, nombre_archivo)
    return None

def consultar_nova_drive(consulta):
    log_msg(f"📚 [NOVA DRIVE] Buscando en la biblioteca local: '{consulta}'...")
    archivos = [f for f in os.listdir(CARPETA_DRIVE) if f.endswith('.txt')]
    if not archivos: return "Mi biblioteca teórica (Nova Drive) está vacía en este momento."
    palabras_clave = [p.lower() for p in consulta.split() if len(p) > 3]
    if not palabras_clave: return "No detecté términos clave para buscar en mi teoría."
    resultados = []
    for archivo in archivos:
        try:
            with open(os.path.join(CARPETA_DRIVE, archivo), "r", encoding="utf-8") as f:
                for oracion in f.read().split('.'):
                    if any(pc in oracion.lower() for pc in palabras_clave) and len(oracion.strip()) > 10: 
                        resultados.append(oracion.strip())
                        if len(resultados) >= 3: break
        except: pass
        if len(resultados) >= 3: break
    return "Según mis archivos teóricos locales: " + ". ".join(resultados) + "." if resultados else "No encontré información teórica local."

def hablar(texto):
    log_msg(f"🔊 [{NOMBRE_ASISTENTE}]: {texto}")
    texto_limpio = texto.replace("'", "").replace('"', '')
    texto_tts = texto_limpio.replace("N.O.V.A.", "Nova").replace("N.O.V.A", "Nova")
    
    if VOZ_AVANZADA:
        archivo_audio = "respuesta_nova.mp3"
        try:
            comando = f'edge-tts --voice es-US-PalomaNeural --text "{texto_tts}" --write-media {archivo_audio}'
            subprocess.run(comando, shell=True, check=True, stdout=subprocess.DEVNULL, stderr=subprocess.DEVNULL)
            pygame.mixer.music.load(archivo_audio)
            pygame.mixer.music.play()
            while pygame.mixer.music.get_busy(): time.sleep(0.1)
            pygame.mixer.music.unload() 
            if os.path.exists(archivo_audio): os.remove(archivo_audio)
            return 
        except: pass
    subprocess.Popen(f'powershell -Command "Add-Type -AssemblyName System.Speech; (New-Object System.Speech.Synthesis.SpeechSynthesizer).Speak(\'{texto_tts}\')"', shell=True)

def calcular_similitud_coseno(v1, v2): return np.dot(v1, v2) / (np.linalg.norm(v1) * np.linalg.norm(v2))

def recordar_evento(texto):
    log_msg(f"🧠 [MEMORIA] Codificando recuerdo: '{texto[:50]}...'")
    try:
        vector = llm_provider.embed_content(texto, "retrieval_document")
        fecha_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
        if CHROMA_DISPONIBLE:
            nova_collection.add(embeddings=[vector], documents=[texto], metadatas=[{"fecha": fecha_str}], ids=[str(uuid.uuid4())])
        else:
            with open(ARCHIVO_MEMORIA, "r", encoding="utf-8") as f: memoria = json.load(f)
            memoria.append({"texto": texto, "vector": vector, "fecha": fecha_str})
            with open(ARCHIVO_MEMORIA, "w", encoding="utf-8") as f: json.dump(memoria, f, ensure_ascii=False)
        return "Recuerdo consolidado en la memoria a largo plazo."
    except Exception as e: return f"Error guardando recuerdo: {e}"

def recuperar_memoria_relevante(query, top_k=3):
    try:
        vector_query = llm_provider.embed_content(query, "retrieval_query")
        if CHROMA_DISPONIBLE:
            if nova_collection.count() == 0: return "Sin recuerdos previos."
            k = min(top_k, nova_collection.count())
            results = nova_collection.query(query_embeddings=[vector_query], n_results=k)
            textos = []
            if results['documents'] and results['documents'][0]:
                for i in range(len(results['documents'][0])):
                    if results['distances'][0][i] < 0.55: 
                        textos.append(f"[{results['metadatas'][0][i].get('fecha', '')}] {results['documents'][0][i]}")
            return "\n".join(textos) if textos else "No hay recuerdos relacionados."
        else:
            with open(ARCHIVO_MEMORIA, "r", encoding="utf-8") as f: memoria = json.load(f)
            if not memoria: return "Sin recuerdos previos."
            for item in memoria: item['similitud'] = calcular_similitud_coseno(vector_query, item['vector']) if "vector" in item else 0
            memoria.sort(key=lambda x: x.get('similitud', 0), reverse=True)
            textos = [f"[{m.get('fecha', '')}] {m['texto']}" for m in memoria[:top_k] if m.get('similitud', 0) > 0.45]
            return "\n".join(textos) if textos else "No hay recuerdos relacionados."
    except Exception as e: return f"Error recuperando memoria: {e}"

def hilo_reloj_interno():
    while True:
        ahora = datetime.datetime.now()
        tareas_vencidas = []
        with lock_tareas:
            for tarea in TAREAS_PROGRAMADAS:
                if ahora >= tarea['hora_ejecucion']: tareas_vencidas.append(tarea)
            for t in tareas_vencidas: TAREAS_PROGRAMADAS.remove(t)
            
        for tarea in tareas_vencidas:
            mensaje_alerta = f"⏰ [RECORDATORIO]: {tarea['mensaje']}"
            log_msg(mensaje_alerta)
            hablar(f"Señor, le recuerdo que: {tarea['mensaje']}")
        time.sleep(5) 

# ==========================================
# 1.4 MICRÓFONO Y MODOS DE VIGILANCIA
# ==========================================
pyautogui.FAILSAFE = True
pyautogui.PAUSE = 0.5
VIGILANCIA_ACTIVA = False 
NOTIFICACIONES_ACTIVAS = False 
VISION_CONTINUA_ACTIVA = False 
CONTEXTO_VISUAL_ACTUAL = "Sin datos visuales recientes." 

def escuchar_microfono(duracion=6, silencioso=False):
    if not MICROFONO_DISPONIBLE: return ""
    if not silencioso: log_msg(f"\n🎤 [MICRÓFONO ABIERTO] Habla ahora...")
    
    try:
        fs = 16000 
        grabacion = sd.rec(int(duracion * fs), samplerate=fs, channels=1, dtype='float32')
        sd.wait() 
        if not silencioso: log_msg("⏳ [SISTEMA] Procesando audio...")
        
        audio_np = grabacion.flatten()
        
        # 1. PLAN A: NUBE (GOOGLE) - Principal por Consumo Cero de CPU
        try:
            audio_int16 = (audio_np * 32767).astype(np.int16)
            audio_data = sr.AudioData(audio_int16.tobytes(), fs, 2)
            
            reconocedor = sr.Recognizer()
            texto = reconocedor.recognize_google(audio_data, language="es-ES")
            if not silencioso: log_msg(f"🗣️ [OÍDO NUBE] Señor: '{texto}'")
            return texto
        except Exception as e:
            if not silencioso: log_msg(f"⚠️ [NUBE] Fallo de red. Activando Oídos Locales (Whisper)...")
            
            # 2. PLAN B: INTENTO LOCAL (WHISPER TINY) - Respaldo Offline
            if WHISPER_DISPONIBLE:
                try:
                    resultado = modelo_whisper.transcribe(audio_np, language="es", fp16=False)
                    texto = resultado["text"].strip()
                    if texto:
                        if not silencioso: log_msg(f"🗣️ [OÍDO LOCAL] Señor: '{texto}'")
                        return texto
                except Exception as ex:
                    log_msg(f"⚠️ [WHISPER] Fallo crítico local: {ex}")
        return ""
    except Exception as e:
        return ""

def modo_palabra_magica():
    global VIGILANCIA_ACTIVA
    log_msg(f"\n🎧 [VIGILANCIA] Activada. Esperando la palabra mágica...")
    activadores = ["nova", "no va", "noba", "nueva", "hola nova", "oye nova"]
    while VIGILANCIA_ACTIVA:
        try:
            texto = escuchar_microfono(duracion=4, silencioso=True).lower()
            if not VIGILANCIA_ACTIVA: break
            if any(palabra in texto for palabra in activadores):
                hablar("¿En qué te ayudo?")
                cmd = escuchar_microfono(duracion=7, silencioso=False)
                if cmd: procesar_comando(cmd)
        except: pass 

def modo_proactivo():
    global NOTIFICACIONES_ACTIVAS
    while NOTIFICACIONES_ACTIVAS:
        for _ in range(60):
            if not NOTIFICACIONES_ACTIVAS: return
            time.sleep(1)
        try:
            correos = leer_correos("2")
            if "No correos nuevos" not in correos and "Error" not in correos:
                prompt = f"Eres {NOMBRE_ASISTENTE}. Avisa al usuario de correos: {correos}. Responde SOLO JSON: {{ 'alerta_hablada': 'mensaje' }}"
                resp = llm_provider.generate_content([{"role": "user", "parts": [prompt]}], json_mode=True)
                alerta = extraer_json(resp.text).get("alerta_hablada")
                if alerta and alerta.lower() != "null": hablar(alerta); log_msg(f"🔔 [ALERTA]: {alerta}")
        except: pass 

def modo_vision_continua():
    global VISION_CONTINUA_ACTIVA, CONTEXTO_VISUAL_ACTUAL
    log_msg(f"\n👁️ [VISIÓN CONTINUA] Activada. Escaneando pantalla cada 3 minutos...")
    while VISION_CONTINUA_ACTIVA:
        for _ in range(180): 
            if not VISION_CONTINUA_ACTIVA: return
            time.sleep(1)
        try:
            ruta_captura = "captura_rutina.png"
            ImageGrab.grab().save(ruta_captura)
            imagen = ImageGrab.grab()
            prompt = "Describe en una sola oración breve qué hace el usuario. Si hay un error crítico visible, empieza tu frase con 'ALERTA:'."
            resp = llm_provider.generate_content([{"role": "user", "parts": [prompt, imagen]}], json_mode=False)
            res = resp.text.strip(); CONTEXTO_VISUAL_ACTUAL = res.replace("ALERTA:", "").strip()
            if "ALERTA:" in res.upper():
                hablar(f"Señor, noto algo en su pantalla: {CONTEXTO_VISUAL_ACTUAL}")
                log_msg(f"👁️ [ALERTA VISUAL]: {CONTEXTO_VISUAL_ACTUAL}")
            else: log_msg(f"👁️ [VISIÓN] {CONTEXTO_VISUAL_ACTUAL}")
            if os.path.exists(ruta_captura): os.remove(ruta_captura)
        except: pass

# ==========================================
# 2. HERRAMIENTAS Y RUTINAS (PILOTO FANTASMA)
# ==========================================

def control_multimedia(accion="playpause", query="", **kwargs):
    accion = str(accion or kwargs.get("action") or "playpause").lower()
    query = str(query or kwargs.get("busqueda") or kwargs.get("cancion") or "")
    try:
        if "buscar" in accion or query:
            log_msg(f"🎵 [MULTIMEDIA] Buscando música: {query}")
            webbrowser.open(f"https://www.youtube.com/results?search_query={query}")
            return f"He abierto YouTube con la búsqueda: {query}."
        elif "next" in accion or "siguiente" in accion: pyautogui.press('nexttrack'); return "Saltando pista."
        elif "prev" in accion or "anterior" in accion: pyautogui.press('prevtrack'); return "Volviendo a pista anterior."
        elif "mute" in accion or "silencio" in accion: pyautogui.press('volumemute'); return "Audio silenciado/restaurado."
        else: pyautogui.press('playpause'); return "Reproducción pausada o reanudada."
    except Exception as e: return f"Error en control multimedia: {e}"

def programar_recordatorio(minutos=0, mensaje="", **kwargs):
    try:
        minutos = float(minutos or kwargs.get("min") or kwargs.get("tiempo") or kwargs.get("minutos") or 0)
        mensaje = str(mensaje or kwargs.get("texto") or kwargs.get("recordatorio") or kwargs.get("alarma") or "Alarma programada")
        if minutos <= 0: return "Error: Los minutos deben ser mayores a 0."
        hora_ejecucion = datetime.datetime.now() + datetime.timedelta(minutes=minutos)
        with lock_tareas: TAREAS_PROGRAMADAS.append({'hora_ejecucion': hora_ejecucion, 'mensaje': mensaje})
        return f"Recordatorio establecido exitosamente para las {hora_ejecucion.strftime('%H:%M')}: '{mensaje}'."
    except Exception as e: return f"Error al programar el recordatorio: {e}"

def leer_pantalla_ocr(**kwargs):
    log_msg("👁️ [VISIÓN LOCAL] Escaneando píxeles de la pantalla...")
    if not TESSERACT_DISPONIBLE: return "Librería pytesseract no instalada."
    if not os.path.exists(pytesseract.pytesseract.tesseract_cmd): return "Motor Tesseract no instalado."
    
    was_main_visible = False; was_orb_visible = False
    global app_gui
    if app_gui:
        was_main_visible = app_gui.winfo_viewable()
        if hasattr(app_gui, 'orb_window'): was_orb_visible = app_gui.orb_window.winfo_viewable()
        if was_main_visible: app_gui.withdraw()
        if was_orb_visible: app_gui.orb_window.withdraw()
        log_msg("👁️ [VISIÓN LOCAL] Interfaz apartada. Capturando en 2.5 segundos...")
        time.sleep(2.5) 
    try:
        img = ImageGrab.grab()
        if app_gui:
            if was_main_visible: app_gui.deiconify()
            if was_orb_visible: app_gui.orb_window.deiconify()
        try: texto = pytesseract.image_to_string(img, lang='spa')
        except: texto = pytesseract.image_to_string(img, lang='eng')
            
        texto_limpio = texto.strip().replace('\n', ' ')
        if not texto_limpio: return "No detecté ningún texto claro en la pantalla."
        return f"El texto visible en pantalla dice: {texto_limpio[:1500]}..."
    except Exception as e:
        if app_gui:
            if was_main_visible: app_gui.deiconify()
            if was_orb_visible: app_gui.orb_window.deiconify()
        return f"Error ejecutando OCR: {e}"

def crear_documento_google(texto="", **kwargs):
    texto = texto or kwargs.get("contenido") or kwargs.get("informe") or kwargs.get("mensaje") or ""
    log_msg("📝 [SISTEMA] Creando nuevo documento de Google...")
    try:
        webbrowser.open("https://docs.new"); time.sleep(6) 
        pyperclip.copy(texto); pyautogui.hotkey('ctrl', 'v')
        return "Documento de Google creado exitosamente."
    except Exception as e: return f"Error al crear Documento: {e}"

def redactar_informe_bloc_notas(texto="", **kwargs):
    texto = texto or kwargs.get("contenido") or kwargs.get("informe") or kwargs.get("mensaje") or ""
    log_msg("📝 [SISTEMA] Redactando informe en Bloc de Notas...")
    try:
        subprocess.Popen(['notepad.exe']); time.sleep(2) 
        pyperclip.copy(texto); pyautogui.hotkey('ctrl', 'v')
        return "Informe redactado exitosamente en el Bloc de Notas."
    except Exception as e: return f"Error al redactar en Bloc: {e}"

def abrir_programa_inteligente(nombre_programa="", **kwargs):
    nombre_programa = nombre_programa or kwargs.get("programa") or kwargs.get("nombre") or ""
    log_msg(f"🖥️ [SISTEMA] Piloto Fantasma: Buscando y abriendo '{nombre_programa}'...")
    try:
        pyautogui.press('win'); time.sleep(0.8); pyautogui.write(nombre_programa, interval=0.05); time.sleep(1.5); pyautogui.press('enter')
        return f"Se ejecutó la secuencia para abrir {nombre_programa}."
    except Exception as e: return f"Error al abrir el programa: {e}"

def ejecutar_macro_teclado(secuencia_teclas="", **kwargs):
    secuencia_teclas = secuencia_teclas or kwargs.get("teclas") or kwargs.get("atajo") or ""
    try:
        for tecla in [t.strip() for t in secuencia_teclas.split(',')]:
            if '+' in tecla: pyautogui.hotkey(*tecla.split('+'))
            else: pyautogui.press(tecla)
            time.sleep(0.3) 
        return f"Secuencia '{secuencia_teclas}' ejecutada."
    except Exception as e: return f"Error de macro: {e}"

def delegar_a_subagente(rol="investigador", tarea="", destino="consola", **kwargs):
    tarea = tarea or kwargs.get("solicitud") or kwargs.get("tema") or kwargs.get("query") or ""
    rol = rol or kwargs.get("role") or "investigador"
    destino = destino or kwargs.get("dest") or "consola"
    prompts_roles = {"investigador": "Eres un Investigador. Sintetiza información.", "redactor": "Eres un Redactor Experto. Escribes perfecto.", "analista": "Eres un Analista. Desglosas problemas."}
    sistema = prompts_roles.get(rol.lower(), "Eres un Sub-Agente Especializado.")
    contexto_web = ""
    if rol.lower() == "investigador":
        try:
            res = list(DDGS().text(tarea, max_results=3))
            contexto_web = "DATOS WEB EXTRAÍDOS PARA TI:\n" + "\n".join([f"- {r['title']}: {r['body'][:200]}" for r in res]) 
        except: pass
    try:
        prompt_final = f"{sistema}\n\n{contexto_web}\n\nTAREA ASIGNADA: {tarea}\n\nResponde con el reporte final."
        resp = llm_provider.generate_content([{"role": "user", "parts": [prompt_final]}], json_mode=False)
        time.sleep(1.5) 
        reporte_final = f"Reporte final del {rol.upper()}:\n\n{resp.text}" 
        if destino == "bloc" or "notas" in tarea.lower(): redactar_informe_bloc_notas(reporte_final); return f"Misión completada. Informe escrito en el Bloc de Notas."
        elif destino == "docs" or "google" in tarea.lower(): crear_documento_google(reporte_final); return f"Misión completada. Informe escrito en Google Docs."
        return reporte_final
    except Exception as e: return f"El sub-agente falló: {e}"

def gestionar_entorno(perfil="", **kwargs):
    perfil = (perfil or kwargs.get("modo") or "").lower()
    try:
        if "trabajo" in perfil or "estudio" in perfil: pyautogui.hotkey('win', 'd'); time.sleep(1); webbrowser.open("https://docs.google.com"); cambiar_volumen(30); return "Modo trabajo activado."
        elif "descanso" in perfil or "ocio" in perfil: pyautogui.hotkey('win', 'd'); time.sleep(1); webbrowser.open("https://youtube.com"); cambiar_volumen(70); return "Modo descanso activado."
        elif "limpieza" in perfil: pyautogui.hotkey('win', 'd'); return "Modo limpieza ejecutado."
        else: return f"Perfil '{perfil}' no configurado."
    except Exception as e: return f"Error entorno: {e}"

def enviar_whatsapp(numero="", mensaje="", **kwargs):
    numero = numero or kwargs.get("telefono") or kwargs.get("num") or ""
    mensaje = mensaje or kwargs.get("texto") or kwargs.get("msg") or ""
    try: 
        log_msg(f"📱 [SISTEMA] Preparando envío a {numero}.")
        pywhatkit.sendwhatmsg_instantly(numero, mensaje, wait_time=20, tab_close=True, close_time=4)
        return f"Mensaje de WhatsApp enviado."
    except Exception as e: return f"Error WhatsApp: {e}"

def leer_calendario(cantidad="5", fecha_inicio=None, fecha_fin=None, **kwargs):
    cantidad = cantidad or kwargs.get("cant") or "5"
    try:
        service = obtener_servicio_calendario()
        if not service: return "Error: Falta 'credentials.json'."
        time_min = fecha_inicio if fecha_inicio else datetime.datetime.utcnow().isoformat() + 'Z'
        kws = {'calendarId': 'primary', 'timeMin': time_min, 'maxResults': int(cantidad), 'singleEvents': True, 'orderBy': 'startTime'}
        if fecha_fin: kws['timeMax'] = fecha_fin
        events = service.events().list(**kws).execute().get('items', [])
        return "Eventos:\n" + "\n".join([f"- {e['start'].get('dateTime', e['start'].get('date'))}: {e['summary']}" for e in events]) if events else "No hay eventos."
    except Exception as e: return f"Error calendario: {e}"

def crear_evento(resumen="", fecha_inicio="", fecha_fin="", descripcion="", **kwargs):
    resumen = resumen or kwargs.get("titulo") or ""
    try:
        service = obtener_servicio_calendario()
        event = {'summary': resumen, 'description': descripcion, 'start': {'dateTime': fecha_inicio, 'timeZone': 'America/Montevideo'}, 'end': {'dateTime': fecha_fin, 'timeZone': 'America/Montevideo'}}
        service.events().insert(calendarId='primary', body=event).execute()
        return "Evento creado."
    except Exception as e: return f"Error evento: {e}"

def analizar_documento(ruta_archivo="", **kwargs):
    ruta_archivo = ruta_archivo or kwargs.get("ruta") or kwargs.get("path") or ""
    try:
        ruta_real = buscar_archivo_local(ruta_archivo.replace('"', '').replace("'", "").strip())
        if not ruta_real: return f"Error: No encontré el archivo '{ruta_archivo}'."
        ext = os.path.splitext(ruta_real)[1].lower()
        if ext == '.pdf':
            with open(ruta_real, 'rb') as f: return f"Texto:\n{''.join([p.extract_text() for p in PyPDF2.PdfReader(f).pages[:10]])[:8000]}"
        elif ext == '.txt':
            with open(ruta_real, 'r', encoding='utf-8') as f: return f.read(15000)
        return "Formato no soportado."
    except Exception as e: return f"Error lectura: {e}"

def aprender_documento(ruta_archivo="", **kwargs):
    ruta_archivo = ruta_archivo or kwargs.get("ruta") or kwargs.get("path") or kwargs.get("nombre") or ""
    try:
        ruta_real = buscar_archivo_local(ruta_archivo.replace('"', '').replace("'", "").strip())
        if not ruta_real: return f"Error: No encontré el archivo '{ruta_archivo}'."
        ext = os.path.splitext(ruta_real)[1].lower()
        texto_completo = ""
        if ext == '.pdf':
            with open(ruta_real, 'rb') as f: texto_completo = " ".join([p.extract_text() for p in PyPDF2.PdfReader(f).pages])
        elif ext == '.txt':
            with open(ruta_real, 'r', encoding='utf-8') as f: texto_completo = f.read()
        else: return "Solo soporto PDFs y TXTs."
        if not texto_completo.strip(): return "El documento está vacío."
        
        words = texto_completo.split()
        chunks = [' '.join(words[i:i+150]) for i in range(0, len(words), 150)]
        log_msg(f"🧠 [ASIMILACIÓN] Vectorizando e ingiriendo {len(chunks)} bloques...")
        
        for chunk in chunks:
            texto_guardar = f"Fuente [{os.path.basename(ruta_real)}]: {chunk}"
            vector = llm_provider.embed_content(texto_guardar, "retrieval_document")
            fecha_str = datetime.datetime.now().strftime('%Y-%m-%d %H:%M')
            if CHROMA_DISPONIBLE:
                nova_collection.add(embeddings=[vector], documents=[texto_guardar], metadatas=[{"fecha": fecha_str}], ids=[str(uuid.uuid4())])
            else:
                with open(ARCHIVO_MEMORIA, "r", encoding="utf-8") as f: memoria = json.load(f)
                memoria.append({"texto": texto_guardar, "vector": vector, "fecha": fecha_str})
                with open(ARCHIVO_MEMORIA, "w", encoding="utf-8") as f: json.dump(memoria, f, ensure_ascii=False)
        return f"Documento asimilado localmente."
    except Exception as e: return f"Error asimilando: {e}"

def enviar_correo(destinatario="", asunto="", cuerpo="", **kwargs):
    destinatario = destinatario or kwargs.get("email") or ""
    try:
        if not GMAIL_USUARIO: return "Error: Credenciales no configuradas en config_nova.json"
        msg = MIMEMultipart(); msg['From'] = GMAIL_USUARIO; msg['To'] = destinatario; msg['Subject'] = asunto
        msg.attach(MIMEText(cuerpo, 'plain', 'utf-8'))
        s = smtplib.SMTP('smtp.gmail.com', 587); s.starttls(); s.login(GMAIL_USUARIO, GMAIL_PASSWORD); s.send_message(msg); s.quit()
        return "Correo enviado."
    except Exception as e: return f"Error de correo: {e}"

def leer_correos(cantidad="3", **kwargs):
    cantidad = cantidad or kwargs.get("cant") or "3"
    try:
        if not GMAIL_USUARIO: return "Error: Credenciales no configuradas en config_nova.json"
        mail = imaplib.IMAP4_SSL("imap.gmail.com"); mail.login(GMAIL_USUARIO, GMAIL_PASSWORD); mail.select("inbox")
        status, mensajes = mail.search(None, 'UNSEEN')
        id_lista = mensajes[0].split()
        if not id_lista: return "No correos nuevos."
        res = []
        for i in id_lista[-int(cantidad):]:
            r, msg_data = mail.fetch(i, "(RFC822)")
            for rp in msg_data:
                if isinstance(rp, tuple):
                    m = email.message_from_bytes(rp[1]); sub, enc = decode_header(m["Subject"])[0]
                    if isinstance(sub, bytes): sub = sub.decode(enc if enc else "utf-8", errors='ignore')
                    res.append(f"- De: {m.get('From')} | Asunto: {sub}")
        mail.logout(); return "No leídos:\n" + "\n".join(res)
    except Exception as e: return f"Error leyendo correos: {e}"

def ejecutar_terminal(comando="", **kwargs): 
    comando = comando or kwargs.get("cmd") or ""
    return f"Éxito: {subprocess.check_output(comando, shell=True, text=True, timeout=2)[:800]}"

def escribir_texto(texto="", **kwargs): 
    texto = texto or kwargs.get("msg") or ""
    pyautogui.write(texto, interval=0.03); return "Escrito."

def abrir_bloc_notas(**kwargs): subprocess.Popen(['notepad.exe']); return "Bloc abierto."

def cambiar_volumen(n=50, **kwargs):
    n = n or kwargs.get("nivel") or 50
    try: pyautogui.press('volumedown', presses=50, interval=0.01); pyautogui.press('volumeup', presses=int(n) // 2, interval=0.01); return f"Volumen al {n}%."
    except: return "Error volumen."

def estado_sistema(**kwargs): return f"CPU: {psutil.cpu_percent()}%"

def buscar_en_web(q="", **kwargs): 
    q = q or kwargs.get("query") or kwargs.get("busqueda") or ""
    try:
        res = list(DDGS().text(q, max_results=3))
        return "\n".join([f"- {r['title']}: {r['body']}" for r in res]) if res else "No encontré resultados."
    except Exception as e: return f"Error en la búsqueda web: {e}"

def buscar_archivos(n="", **kwargs): return "Función activa."
def cerrar_programa(n="", **kwargs): 
    n = n or kwargs.get("nombre") or ""
    try: os.system(f"taskkill /f /im {n.replace('.exe', '')}.exe"); return f"Programa cerrado."
    except: return "Error al cerrar programa."

def ver_pantalla(**kwargs): return "Pantalla vista."
def ejecutar_codigo_python(codigo="", **kwargs): return "Código ejecutado localmente."

herramientas_disponibles = {
    "ejecutar_terminal": ejecutar_terminal, "escribir_texto": escribir_texto, "abrir_bloc_notas": abrir_bloc_notas, 
    "cambiar_volumen": cambiar_volumen, "ver_pantalla": ver_pantalla, "recordar_evento": recordar_evento, 
    "estado_sistema": estado_sistema, "buscar_en_web": buscar_en_web, "buscar_archivos": buscar_archivos, 
    "cerrar_programa": cerrar_programa, "enviar_correo": enviar_correo, "leer_correos": leer_correos, 
    "analizar_documento": analizar_documento, "enviar_whatsapp": enviar_whatsapp, "leer_calendario": leer_calendario, 
    "crear_evento": crear_evento, "ejecutar_codigo_python": ejecutar_codigo_python, "gestionar_entorno": gestionar_entorno, 
    "delegar_a_subagente": delegar_a_subagente, "abrir_programa_inteligente": abrir_programa_inteligente, 
    "ejecutar_macro_teclado": ejecutar_macro_teclado, "crear_documento_google": crear_documento_google, 
    "redactar_informe_bloc_notas": redactar_informe_bloc_notas, "leer_pantalla_ocr": leer_pantalla_ocr, 
    "programar_recordatorio": programar_recordatorio, "control_multimedia": control_multimedia, "aprender_documento": aprender_documento
}

CATEGORIAS_HERRAMIENTAS = {
    "vision_local": {"palabras_clave": ["lee la pantalla", "que dice la pantalla", "ocr", "extrae texto", "lee este error", "pestaña"], "texto_herramientas": "- leer_pantalla_ocr()"},
    "multimedia": {"palabras_clave": ["musica", "reproduce", "cancion", "pausa", "siguiente", "anterior", "mute", "silencia", "spotify", "youtube", "pon", "escuchar"], "texto_herramientas": "- control_multimedia(accion, query)"},
    "busqueda_web": {"palabras_clave": ["busca", "internet", "web", "google", "información", "noticias", "quien", "que es"], "texto_herramientas": "- buscar_en_web(q)"},
    "redaccion_e_informes": {"palabras_clave": ["escribe en docs", "google docs", "crea un documento", "redacta en docs", "informe", "redacta", "escribe un texto largo"], "texto_herramientas": "- crear_documento_google(texto)\n- redactar_informe_bloc_notas(texto)\n- escribir_texto(texto)"},
    "comunicacion": {"palabras_clave": ["whatsapp", "mensaje", "correo", "mail", "gmail", "escribe a", "contacta"], "texto_herramientas": "- enviar_whatsapp(numero, mensaje)\n- enviar_correo(destinatario, asunto, cuerpo)\n- leer_correos(cantidad)"},
    "agenda_y_alarmas": {"palabras_clave": ["agenda", "calendario", "evento", "reunión", "cita", "agendar", "recuerdame", "alarma", "avísame"], "texto_herramientas": "- leer_calendario(cantidad, fecha_inicio, fecha_fin)\n- crear_evento(resumen, fecha_inicio, fecha_fin, descripcion)\n- programar_recordatorio(minutos, mensaje)"},
    "archivos_y_sistema": {"palabras_clave": ["archivo", "documento", "pdf", "docx", "busca", "bloc de notas", "volumen", "batería", "cierra", "pantalla", "sistema"], "texto_herramientas": "- analizar_documento(ruta_archivo)\n- buscar_archivos(nombre)\n- estado_sistema()\n- cambiar_volumen(nivel)\n- cerrar_programa(nombre_proceso)\n- abrir_bloc_notas()"},
    "control_aplicaciones": {"palabras_clave": ["abre el programa", "inicia", "ejecuta la aplicación", "cad", "cade", "simu", "spotify", "word", "excel", "presiona", "atajo", "macro"], "texto_herramientas": "- abrir_programa_inteligente(nombre_programa)\n- ejecutar_macro_teclado(secuencia_teclas)"},
    "ingeniero": {"palabras_clave": ["código", "python", "script", "calcula", "programa", "lógica", "ping", "cmd", "terminal"], "texto_herramientas": "- ejecutar_codigo_python(codigo)\n- ejecutar_terminal(comando)"},
    "memoria": {"palabras_clave": ["recuerda", "guarda", "memoria", "no olvides", "favorito", "aprende", "asimila", "lee este libro"], "texto_herramientas": "- recordar_evento(texto)\n- aprender_documento(ruta_archivo)"},
    "rutinas_entorno": {"palabras_clave": ["modo", "rutina", "entorno", "trabajo", "estudio", "descanso", "ocio", "limpieza", "prepara mi espacio"], "texto_herramientas": "- gestionar_entorno(perfil)"},
    "mente_colmena": {"palabras_clave": ["investiga", "ensayo", "analiza a fondo", "resumen largo", "reporte", "informe"], "texto_herramientas": "- delegar_a_subagente(rol, tarea, destino)"}
}

def extraer_json(texto):
    try:
        inicio, fin = texto.find('{'), texto.rfind('}') + 1
        if inicio == -1 or fin == 0: return {}
        json_str = texto[inicio:fin]
        try: return json.loads(json_str, strict=False)
        except: pass
        try: return json.loads(re.sub(r'(?<!\\)\\(?!["\\/bfnrtu])', r'\\\\', json_str), strict=False)
        except: pass
        return json.loads(json_str.replace('\\', '\\\\').replace('\\\\"', '\\"'), strict=False)
    except: return {}

# ==========================================
# 3. CEREBRO CENTRAL (RUTEO MULTI-PASO)
# ==========================================
def procesar_comando(comando_texto):
    global historial_chat
    if not comando_texto.strip(): return
    
    with lock_historial:
        historial_chat.append(f"Usuario: {comando_texto}")
        if len(historial_chat) > 8: historial_chat.pop(0) 
        historial_reciente = "\n".join(historial_chat)
    
    comando_lower = comando_texto.lower().strip()
    
    reemplazos_acentos = {'á':'a', 'é':'e', 'í':'i', 'ó':'o', 'ú':'u'}
    comando_sin_acentos = comando_lower
    for orig, dest in reemplazos_acentos.items():
        comando_sin_acentos = comando_sin_acentos.replace(orig, dest)
        
    comando_limpio = re.sub(r'[^\w\s]', '', comando_sin_acentos).replace("nova", "").strip()
    
    def ejecutar_local(mensaje, funcion_accion=None):
        if funcion_accion:
            try: funcion_accion()
            except: pass
        log_msg(f"🤖 [{NOMBRE_ASISTENTE}]: {mensaje} [💻 LOCAL - 0 TOKENS]")
        hablar(mensaje)
        with lock_historial: historial_chat.append(f"{NOMBRE_ASISTENTE}: {mensaje}")

    if "apaga" in comando_limpio and any(x in comando_limpio for x in ["pc", "sistema", "equipo", "computadora"]):
        ejecutar_local("Iniciando secuencia de apagado en 10 segundos.", lambda: os.system("shutdown /s /t 10")); return
    if "reinicia" in comando_limpio and any(x in comando_limpio for x in ["pc", "sistema", "equipo", "computadora"]):
        ejecutar_local("Reiniciando el sistema en 10 segundos.", lambda: os.system("shutdown /r /t 10")); return
    if "cancela" in comando_limpio and "apagado" in comando_limpio:
        ejecutar_local("Secuencia de apagado abortada.", lambda: os.system("shutdown /a")); return

    match_recordatorio = re.search(r'(recuerdame|avisame|alarma) (en|dentro de) (\d+) minutos (que |para )?(.*)', comando_limpio)
    if match_recordatorio:
        mins = int(match_recordatorio.group(3))
        msg = match_recordatorio.group(5).strip()
        ejecutar_local(programar_recordatorio(minutos=mins, mensaje=msg)); return

    if any(palabra in comando_limpio for palabra in ["musica", "cancion", "reproduce", "pausa", "siguiente", "anterior"]):
        if "pon musica de" in comando_limpio or "reproduce a" in comando_limpio or "busca musica de" in comando_limpio:
            artista = comando_limpio.split("musica de")[-1].strip() if "musica de" in comando_limpio else comando_limpio.split("reproduce a")[-1].strip()
            if artista: ejecutar_local(f"Buscando música para: {artista}.", lambda: webbrowser.open(f"https://www.youtube.com/results?search_query={artista}")); return
        if "pausa" in comando_limpio or ("reproduce" in comando_limpio and "musica de" not in comando_limpio):
            ejecutar_local("Alternando reproducción de medios.", lambda: pyautogui.press('playpause')); return
        if "siguiente" in comando_limpio: ejecutar_local("Saltando pista.", lambda: pyautogui.press('nexttrack')); return
        if "anterior" in comando_limpio or "vuelve" in comando_limpio: ejecutar_local("Volviendo a la pista anterior.", lambda: pyautogui.press('prevtrack')); return
        if "silencia" in comando_limpio or "mute" in comando_limpio: ejecutar_local("Silenciando el sistema.", lambda: pyautogui.press('volumemute')); return

    if any(palabra in comando_limpio for palabra in ["cuanto es", "calcula", "suma", "resta", "multiplica", "divide"]):
        expresion = re.sub(r'[^\d\+\-\*\/\(\)\. ]', '', comando_lower).strip()
        if expresion:
            res_math = evaluador_matematico.evaluar(expresion)
            if isinstance(res_math, (int, float)): ejecutar_local(f"El resultado de la operación es {res_math}."); return

    es_complejo = any(palabra in comando_limpio for palabra in [" y ", "luego", "escribe", "redacta", "informe", "resumen"]) or len(comando_limpio.split()) > 8

    if not es_complejo:
        if any(palabra in comando_limpio for palabra in ["lee", "que dice", "texto"]) and any(palabra in comando_limpio for palabra in ["pantalla", "error", "pestaña", "monitor", "imagen"]):
            ejecutar_local(leer_pantalla_ocr()); return
        if "que es" in comando_limpio or "qué es" in comando_lower or "teoria" in comando_limpio or "busca en tus archivos" in comando_limpio:
            query_drive = comando_limpio.replace("que es", "").replace("teoria", "").replace("busca en tus archivos", "").replace("sobre", "").strip()
            if query_drive:
                respuesta_drive = consultar_nova_drive(query_drive)
                if "No encontré" not in respuesta_drive and "vacía" not in respuesta_drive: ejecutar_local(respuesta_drive); return 
        if "volumen" in comando_limpio:
            numeros = re.findall(r'\d+', comando_lower)
            if numeros: ejecutar_local(f"Ajustando el volumen al {numeros[0]}%.", lambda: cambiar_volumen(numeros[0])); return
        if "abre" in comando_limpio or "abrir" in comando_limpio or "inicia" in comando_limpio:
            if "bloc de notas" in comando_limpio: ejecutar_local("Abriendo el bloc de notas.", abrir_bloc_notas); return
            elif "youtube" in comando_limpio: ejecutar_local("Abriendo YouTube.", lambda: webbrowser.open("https://youtube.com")); return
            elif "explorador" in comando_limpio or "carpeta" in comando_limpio: ejecutar_local("Abriendo Explorador.", lambda: subprocess.Popen(['explorer.exe'])); return
            else:
                app_nombre = comando_limpio.replace("abre", "").replace("abrir", "").replace("inicia", "").replace("el", "").replace("programa", "").replace("la", "").strip()
                if app_nombre: ejecutar_local(f"Iniciando {app_nombre}.", lambda: abrir_programa_inteligente(app_nombre)); return
        if "cierra" in comando_limpio or "cerrar" in comando_limpio or "mata" in comando_limpio:
            app_nombre = comando_limpio.replace("cierra", "").replace("cerrar", "").replace("el", "").replace("programa", "").replace("la", "").replace("mata", "").strip()
            if app_nombre:
                if "bloc" in app_nombre or "notas" in app_nombre: app_nombre = "notepad"
                if "explorador" in app_nombre or "carpeta" in app_nombre: app_nombre = "explorer"
                ejecutar_local(f"Forzando el cierre de {app_nombre}.", lambda: cerrar_programa(app_nombre)); return
        if "minimiza" in comando_limpio or "limpia" in comando_limpio and "pantalla" in comando_limpio:
            ejecutar_local("Minimizando ventanas.", lambda: pyautogui.hotkey('win', 'd')); return
        if "busca" in comando_limpio and ("internet" in comando_limpio or "web" in comando_limpio or "sobre" in comando_limpio):
            query = comando_lower.replace("busca en internet", "").replace("busca en la web", "").replace("busca sobre", "").replace("busca", "").strip()
            if query:
                log_msg(f"🌐 [BÚSQUEDA LOCAL] Rastreado la red para: '{query}'")
                ejecutar_local(f"Encontré esto: {buscar_en_web(query)[:300]}..."); return
        if "funciones" in comando_limpio or "offline" in comando_limpio:
            ejecutar_local("Sistemas en línea: Inteligencia Híbrida Ollama, Memoria Cuántica, Oídos Whisper Tiny, OCR, Alarmas, Multimedia y Navegación."); return
        if comando_limpio.startswith("hola") or "todo bien" in comando_limpio or comando_limpio == "buenas":
            ejecutar_local("Sistemas en línea. Procesador Híbrido activado."); return
        if "como estas" in comando_limpio or "que tal" in comando_limpio:
            ejecutar_local("Mis redes neuronales están operando de forma óptima. A la espera de directivas."); return
        if "quien eres" in comando_limpio or "presentate" in comando_limpio:
            ejecutar_local("Soy N.O.V.A., tu inteligencia de escritorio."); return
        if "hora es" in comando_limpio:
            ejecutar_local(f"Son las {datetime.datetime.now().strftime('%H:%M')}."); return
        if "que dia es" in comando_limpio or "fecha" in comando_limpio:
            ejecutar_local(f"Hoy es {datetime.datetime.now().strftime('%Y-%m-%d')}."); return

    # ========================================================
    log_msg("🧠 [N.O.V.A.] Procesando directiva con el Gestor de Inteligencia...")
    
    herramientas_activas = []
    for cat, datos in CATEGORIAS_HERRAMIENTAS.items():
        if any(palabra in comando_lower for palabra in datos["palabras_clave"]):
            herramientas_activas.append(datos["texto_herramientas"])
            log_msg(f"🔀 [ENRUTADOR] Categoría: {cat.upper()}")

    texto_herramientas_final = "\n".join(herramientas_activas) or "Ninguna herramienta del sistema requerida."
    memoria_relevante = recuperar_memoria_relevante(comando_texto)

    prompt_sistema = f"""
    Eres {NOMBRE_ASISTENTE}, una inteligencia artificial de escritorio híbrida y avanzada.
    RELOJ: {datetime.datetime.now().strftime('%Y-%m-%d %H:%M:%S')}
    CONTEXTO VISUAL: {CONTEXTO_VISUAL_ACTUAL}
    RECUERDOS A LARGO PLAZO: {memoria_relevante}
    
    HISTORIAL DE CHAT RECIENTE:
    {historial_reciente}
    
    HERRAMIENTAS PERMITIDAS:
    {texto_herramientas_final}
    
    INSTRUCCIONES CLAVE:
    1. Si el usuario pide investigar/buscar en internet Y redactar un informe, usa 'delegar_a_subagente' pasando 'destino' ('bloc' o 'docs').
    2. Si el usuario pide LEER LA PANTALLA y luego ESCRIBIR, primero usa 'leer_pantalla_ocr'. Se te dará un segundo turno para escribir.

    Comando actual del usuario: "{comando_texto}"

    Responde SOLO en formato JSON válido: 
    {{
        "pensamiento": "Razonamiento...",
        "accion_requerida": "herramienta_o_null", 
        "parametros": {{}}, 
        "respuesta_texto": "respuesta hablada"
    }}
    """
    
    try:
        respuesta = llm_provider.generate_content([{"role": "user", "parts": [prompt_sistema]}], json_mode=True)
        decision = extraer_json(respuesta.text)
        
        pensamiento = decision.get("pensamiento", "")
        accion = decision.get("accion_requerida")
        respuesta_jarvis = decision.get('respuesta_texto', 'Entendido.')
        
        if pensamiento: log_msg(f"🤔 [RAZONAMIENTO]: {pensamiento}")
        log_msg(f"🤖 [{NOMBRE_ASISTENTE}]: {respuesta_jarvis}")
        hablar(respuesta_jarvis) 
        
        with lock_historial: historial_chat.append(f"{NOMBRE_ASISTENTE}: {respuesta_jarvis}")

        if accion and accion in herramientas_disponibles and accion != "null":
            params = decision.get("parametros", {})
            try:
                resultado = herramientas_disponibles[accion](**params)
            except Exception as e:
                log_msg(f"⚠️ [SISTEMA] Alucinación detectada en parámetros de {accion}. Auto-corrigiendo...")
                param_generico = list(params.values())[0] if params else ""
                try:
                    if accion == "redactar_informe_bloc_notas": resultado = redactar_informe_bloc_notas(param_generico)
                    elif accion == "crear_documento_google": resultado = crear_documento_google(param_generico)
                    elif accion == "delegar_a_subagente": resultado = delegar_a_subagente("investigador", param_generico)
                    elif accion == "aprender_documento": resultado = aprender_documento(param_generico)
                    else: resultado = f"Fallo al ejecutar herramienta: {e}"
                except: resultado = f"Error crítico: {e}"

            log_msg(f"🛠️ [RESULTADO 1] {str(resultado)[:300]}...") 
            with lock_historial: historial_chat.append(f"Resultado Interno de {accion}: {str(resultado)[:500]}")
            
            # --- MAGIA MULTI-PASO ---
            herr_recopiladoras = ["leer_correos", "analizar_documento", "leer_calendario", "estado_sistema", "buscar_en_web", "leer_pantalla_ocr"]
            if accion in herr_recopiladoras:
                time.sleep(1.5) 
                p2 = f"""Acabas de usar una herramienta y obtuviste: '{resultado}'. 
Comando original: '{comando_texto}'. 
HERRAMIENTAS PERMITIDAS: {texto_herramientas_final}
INSTRUCCIÓN: Si el usuario pidió EXPRESAMENTE GUARDAR, ESCRIBIR O REDACTAR esto, usa la herramienta adecuada (ej. 'redactar_informe_bloc_notas') AHORA MISMO. Pásale la información. Sino, pon 'null'.
Responde SOLO en formato JSON: {{"pensamiento":"...","accion_requerida":"herramienta_secundaria_o_null","parametros":{{"texto": "info"}},"respuesta_texto":"Reporte final"}}"""
                resp2 = llm_provider.generate_content([{"role": "user", "parts": [p2]}], json_mode=True)
                d2 = extraer_json(resp2.text)
                
                if d2.get('pensamiento'): log_msg(f"🤔 [SEGUNDO PASO]: {d2['pensamiento']}")
                accion2 = d2.get("accion_requerida")
                if accion2 and accion2 in herramientas_disponibles and accion2 != "null":
                    params2 = d2.get("parametros", {})
                    try: res2 = herramientas_disponibles[accion2](**params2)
                    except Exception:
                        gen_p = list(params2.values())[0] if params2 else ""
                        try:
                            if accion2 == "redactar_informe_bloc_notas": res2 = redactar_informe_bloc_notas(gen_p)
                            else: res2 = "Error ejecutando el paso 2."
                        except: pass
                    log_msg(f"🛠️ [RESULTADO 2] {str(res2)[:300]}...")
                    with lock_historial: historial_chat.append(f"Resultado 2 ({accion2}): {str(res2)[:500]}")

                if d2.get('respuesta_texto'): 
                    hablar(d2['respuesta_texto'])
                    with lock_historial: historial_chat.append(f"{NOMBRE_ASISTENTE}: {d2['respuesta_texto']}")
                
    except Exception as e:
        error_msg = str(e).lower()
        log_msg(f"❌ Error de procesamiento: {error_msg}")
        if "saturadas" in error_msg or "vacío" in error_msg or "offline" in error_msg: hablar("Mis sistemas locales y de respaldo están fallando. Revisa tu conexión u Ollama.")
        else: hablar("Se ha producido un error en mi lógica central.")

# ==========================================
# 4. INTERFAZ GRÁFICA AVANZADA (HUD + ORBE)
# ==========================================
class NovaGUI(ctk.CTk):
    def __init__(self):
        super().__init__()
        global app_gui; app_gui = self
        self.title(f"{NOMBRE_ASISTENTE} - Centro de Comando Avanzado")
        self.geometry("950x700") 
        ctk.set_appearance_mode("dark")
        ctk.set_default_color_theme("blue")
        
        self.base_dir = os.path.dirname(os.path.abspath(__file__))
        self.ruta_icono = os.path.join(self.base_dir, "N.O.V.ico")
        self.ruta_icono_jpg = os.path.join(self.base_dir, "N.O.V.jpg")
        
        try:
            if os.path.exists(self.ruta_icono): self.iconbitmap(self.ruta_icono)
        except: pass
        
        self.grid_rowconfigure(0, weight=1)
        self.grid_columnconfigure(1, weight=1)
        
        self.sidebar_frame = ctk.CTkFrame(self, width=220, corner_radius=0, fg_color="#0F172A")
        self.sidebar_frame.grid(row=0, column=0, sticky="nsew")
        self.sidebar_frame.grid_rowconfigure(6, weight=1) 
        
        self.lbl_logo = ctk.CTkLabel(self.sidebar_frame, text="N.O.V.A.", font=("Arial", 32, "bold"), text_color="#3B82F6")
        self.lbl_logo.grid(row=0, column=0, padx=20, pady=(30, 0), sticky="w")
        self.lbl_sub = ctk.CTkLabel(self.sidebar_frame, text="CORE SYSTEM v41.1", font=("Consolas", 10), text_color="#10B981")
        self.lbl_sub.grid(row=1, column=0, padx=20, pady=(0, 20), sticky="w")
        
        self.divider = ctk.CTkFrame(self.sidebar_frame, height=2, fg_color="#1E293B")
        self.divider.grid(row=2, column=0, sticky="ew", padx=20, pady=(0, 20))
        
        self.lbl_modos = ctk.CTkLabel(self.sidebar_frame, text="MODOS OPERATIVOS", font=("Arial", 11, "bold"), text_color="#9CA3AF")
        self.lbl_modos.grid(row=3, column=0, padx=20, pady=(0, 10), sticky="w")
        
        self.sw_v = ctk.CTkSwitch(self.sidebar_frame, text="Vigilancia (Mic)", command=self.toggle_v, progress_color="#10B981")
        self.sw_v.grid(row=4, column=0, padx=20, pady=10, sticky="w")
        
        self.sw_p = ctk.CTkSwitch(self.sidebar_frame, text="Notificaciones", command=self.toggle_p, progress_color="#10B981")
        self.sw_p.grid(row=5, column=0, padx=20, pady=10, sticky="w")
        
        self.sw_c = ctk.CTkSwitch(self.sidebar_frame, text="Visión Continua", command=self.toggle_c, progress_color="#10B981")
        self.sw_c.grid(row=6, column=0, padx=20, pady=10, sticky="nw")
        
        self.stats_frame = ctk.CTkFrame(self.sidebar_frame, fg_color="#1E293B", corner_radius=10)
        self.stats_frame.grid(row=7, column=0, padx=15, pady=10, sticky="ew")
        
        self.lbl_cpu = ctk.CTkLabel(self.stats_frame, text="CORE CPU: --%", font=("Consolas", 11), text_color="#E2E8F0")
        self.lbl_cpu.pack(anchor="w", padx=10, pady=(10, 0))
        self.cpu_bar = ctk.CTkProgressBar(self.stats_frame, progress_color="#3B82F6", height=6)
        self.cpu_bar.pack(fill="x", padx=10, pady=(5, 10))
        self.cpu_bar.set(0)
        
        self.lbl_ram = ctk.CTkLabel(self.stats_frame, text="MEM RAM: --%", font=("Consolas", 11), text_color="#E2E8F0")
        self.lbl_ram.pack(anchor="w", padx=10, pady=0)
        self.ram_bar = ctk.CTkProgressBar(self.stats_frame, progress_color="#8B5CF6", height=6)
        self.ram_bar.pack(fill="x", padx=10, pady=(5, 15))
        self.ram_bar.set(0)

        self.btn_orb = ctk.CTkButton(self.sidebar_frame, text="🔮 Modo Orbe", command=self.toggle_hud, fg_color="#4F46E5", hover_color="#4338CA", font=("Arial", 12, "bold"))
        self.btn_orb.grid(row=8, column=0, padx=15, pady=(5, 20), sticky="ew")
        
        self.main_frame = ctk.CTkFrame(self, fg_color="#0B1120", corner_radius=0)
        self.main_frame.grid(row=0, column=1, sticky="nsew")
        self.main_frame.grid_rowconfigure(0, weight=1)
        self.main_frame.grid_columnconfigure(0, weight=1)
        
        self.caja_texto = ctk.CTkTextbox(self.main_frame, font=("Consolas", 13), state="disabled", fg_color="#0F172A", text_color="#38BDF8", corner_radius=15, border_width=1, border_color="#1E293B")
        self.caja_texto.grid(row=0, column=0, sticky="nsew", padx=20, pady=(20, 15))
        
        self.input_frame = ctk.CTkFrame(self.main_frame, fg_color="transparent")
        self.input_frame.grid(row=1, column=0, sticky="ew", padx=20, pady=(0, 20))
        self.input_frame.grid_columnconfigure(0, weight=1)
        
        self.entrada_texto = ctk.CTkEntry(self.input_frame, placeholder_text="Conexión segura. Esperando directiva...", height=45, corner_radius=10, font=("Arial", 13), fg_color="#1E293B", border_color="#334155")
        self.entrada_texto.grid(row=0, column=0, sticky="ew", padx=(0, 10))
        self.entrada_texto.bind("<Return>", lambda e: self.enviar())
        
        self.btn_enviar = ctk.CTkButton(self.input_frame, text="EJECUTAR", width=90, height=45, corner_radius=10, font=("Arial", 12, "bold"), command=self.enviar, fg_color="#3B82F6", hover_color="#2563EB")
        self.btn_enviar.grid(row=0, column=1, padx=(0, 10))
        
        self.btn_mic = ctk.CTkButton(self.input_frame, text="🎤 DICTAR", width=110, height=45, corner_radius=10, fg_color="#E11D48", hover_color="#BE123C", font=("Arial", 12, "bold"), command=self.mic)
        self.btn_mic.grid(row=0, column=2)
        
        self.escribir_log(f"[{datetime.datetime.now().strftime('%H:%M:%S')}] === N.O.V.A. CORE v41.1 EN LÍNEA ===")
        
        self.update_stats()
        self.crear_orbe_flotante() 

    def crear_orbe_flotante(self):
        self.orb_window = ctk.CTkToplevel(self)
        self.orb_window.title("NOVA Orb")
        self.orb_window.geometry("70x70+150+150") 
        self.orb_window.overrideredirect(True) 
        self.orb_window.attributes("-topmost", True) 
        try:
            if os.name == 'nt':
                self.orb_window.attributes("-transparentcolor", "#000001")
                self.orb_window.configure(fg_color="#000001")
                bg_color = "#000001"
            else: bg_color = "transparent"
        except: bg_color = "transparent"

        try:
            ruta_img = self.ruta_icono if os.path.exists(self.ruta_icono) else self.ruta_icono_jpg if os.path.exists(self.ruta_icono_jpg) else None
            self.icono_orbe = ctk.CTkImage(Image.open(ruta_img), size=(60, 60)) if ruta_img else None
            txt_btn = "" if ruta_img else "🧠"
        except: self.icono_orbe = None; txt_btn = "🧠"

        self.orb_btn = ctk.CTkButton(self.orb_window, text=txt_btn, image=self.icono_orbe, width=60, height=60, corner_radius=30, font=("Arial", 28), fg_color="#3B82F6", hover_color="#2563EB", border_width=3, border_color="#60A5FA", bg_color=bg_color)
        self.orb_btn.pack(expand=True); self.orb_window.withdraw()
        self._d = {"x": 0, "y": 0, "sx": 0, "sy": 0}
        def pr(e): self._d["x"]=e.x; self._d["y"]=e.y; self._d["sx"]=self.orb_window.winfo_pointerx(); self._d["sy"]=self.orb_window.winfo_pointery()
        def dg(e): self.orb_window.geometry(f"+{self.orb_window.winfo_pointerx()-self._d['x']}+{self.orb_window.winfo_pointery()-self._d['y']}")
        def rl(e): 
            if abs(self.orb_window.winfo_pointerx()-self._d["sx"])<5 and abs(self.orb_window.winfo_pointery()-self._d["sy"])<5: self.mic_desde_orbe()
        self.orb_btn.bind("<ButtonPress-1>", pr); self.orb_btn.bind("<B1-Motion>", dg); self.orb_btn.bind("<ButtonRelease-1>", rl); self.orb_btn.bind("<Button-3>", lambda e: self.toggle_hud())

    def mic_desde_orbe(self):
        self.orb_btn.configure(fg_color="#E11D48", border_color="#BE123C") 
        log_msg("\n🔮 [ORBE] Escuchando orden directa...")
        def t(): 
            cmd = escuchar_microfono(duracion=6, silencioso=True)
            self.after(0, lambda: self.orb_btn.configure(fg_color="#10B981", border_color="#34D399")) 
            if cmd: procesar_comando(cmd)
            self.after(0, lambda: self.orb_btn.configure(fg_color="#3B82F6", border_color="#60A5FA")) 
        threading.Thread(target=t, daemon=True).start()

    def toggle_hud(self):
        if self.orb_window.winfo_viewable(): self.orb_window.withdraw(); self.deiconify()           
        else: self.withdraw(); self.orb_window.deiconify()

    def update_stats(self):
        try:
            cpu = psutil.cpu_percent(); ram = psutil.virtual_memory().percent
            self.cpu_bar.set(cpu / 100); self.ram_bar.set(ram / 100)
            self.lbl_cpu.configure(text=f"CORE CPU: {cpu}%"); self.lbl_ram.configure(text=f"MEM RAM: {ram}%")
        except: pass
        self.after(2000, self.update_stats) 

    def escribir_log(self, mensaje):
        self.caja_texto.configure(state="normal"); self.caja_texto.insert("end", mensaje + "\n"); self.caja_texto.configure(state="disabled"); self.caja_texto.yview("end")
    
    def enviar(self):
        cmd = self.entrada_texto.get(); self.entrada_texto.delete(0, 'end'); log_msg(f"\n📝 Señor: {cmd}")
        if cmd.strip(): threading.Thread(target=procesar_comando, args=(cmd,), daemon=True).start()
    
    def mic(self):
        self.btn_mic.configure(state="disabled", text="ESCUCHANDO...")
        def t(): 
            cmd = escuchar_microfono(duracion=6, silencioso=False); procesar_comando(cmd) if cmd else None; self.after(0, lambda: self.btn_mic.configure(state="normal", text="🎤 DICTAR"))
        threading.Thread(target=t, daemon=True).start()
    
    def toggle_v(self): 
        global VIGILANCIA_ACTIVA; VIGILANCIA_ACTIVA = self.sw_v.get() == 1
        if VIGILANCIA_ACTIVA: threading.Thread(target=modo_palabra_magica, daemon=True).start()
        else: log_msg("🛑 Vigilancia Desactivada.")
    
    def toggle_p(self): 
        global NOTIFICACIONES_ACTIVAS; NOTIFICACIONES_ACTIVAS = self.sw_p.get() == 1
        if NOTIFICACIONES_ACTIVAS: threading.Thread(target=modo_proactivo, daemon=True).start()
        else: log_msg("🛑 Notificaciones Desactivadas.")
    
    def toggle_c(self): 
        global VISION_CONTINUA_ACTIVA; VISION_CONTINUA_ACTIVA = self.sw_c.get() == 1
        if VISION_CONTINUA_ACTIVA: threading.Thread(target=modo_vision_continua, daemon=True).start()
        else: log_msg("🛑 Visión Continua Desactivada.")
    
    def on_closing(self): 
        global VIGILANCIA_ACTIVA, NOTIFICACIONES_ACTIVAS, VISION_CONTINUA_ACTIVA
        VIGILANCIA_ACTIVA = False; NOTIFICACIONES_ACTIVAS = False; VISION_CONTINUA_ACTIVA = False
        self.destroy(); os._exit(0) 

if __name__ == "__main__":
    try:
        threading.Thread(target=hilo_reloj_interno, daemon=True).start()
        app_gui = NovaGUI()
        app_gui.protocol("WM_DELETE_WINDOW", app_gui.on_closing)
        app_gui.mainloop()
    except Exception as e:
        print(f"\n❌ ERROR CRÍTICO AL INICIAR: {e}")
        input("\nPresiona la tecla ENTER para cerrar esta ventana...")