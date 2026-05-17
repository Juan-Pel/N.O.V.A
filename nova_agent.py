import requests
import subprocess
import platform
import json
import sys

# CONFIGURACIÓN
# Aquí pones la URL de tu NOVA Brain.
# Si lo ejecutas localmente: http://localhost:5000/procesar
# Si lo subes a la nube (Colab/Ngrok/Render): https://tu-url-ngrok.io/procesar
BRAIN_URL = "http://localhost:5000/procesar"

def ejecutar_accion(accion, parametro):
    """Ejecuta comandos nativos del sistema operativo según la decisión de la IA"""
    sistema = platform.system()
    print(f"🤖 Ejecutando acción: {accion} | Parametro: {parametro}")

    try:
        if accion == "decir":
            # Solo imprime la respuesta (aquí podrías integrar TTS luego)
            print(f"💬 NOVA dice: {parametro}")
            return True

        elif accion == "abrir_app":
            if sistema == "Windows":
                subprocess.Popen(["start", parametro], shell=True)
            elif sistema == "Darwin": # macOS
                subprocess.Popen(["open", parametro])
            else: # Linux
                subprocess.Popen(parametro, shell=True)
            print(f"✅ Aplicación '{parametro}' iniciada.")
            return True

        elif accion == "buscar_web":
            import webbrowser
            url = f"https://www.google.com/search?q={parametro}"
            webbrowser.open(url)
            print(f"✅ Buscando en web: {parametro}")
            return True

        elif accion == "ejecutar_comando":
            # ⚠️ PRECAUCIÓN: Solo ejecutar comandos seguros validados por la IA
            print(f"⚠️ Ejecutando comando: {parametro}")
            resultado = subprocess.run(parametro, shell=True, capture_output=True, text=True)
            print(f"Salida: {resultado.stdout}")
            return True

        elif accion == "error":
            print(f"❌ Error reportado por NOVA: {parametro}")
            return False
            
        else:
            print(f"⚠️ Acción desconocida: {accion}")
            return False

    except Exception as e:
        print(f"❌ Fallo al ejecutar: {e}")
        return False

def escuchar_y_actuar():
    """Bucle principal del agente"""
    print("🎙️  NOVA Agent listo. Escribe un comando (o 'salir' para terminar):")
    
    while True:
        try:
            entrada_usuario = input("> ")
            
            if entrada_usuario.lower() in ["salir", "exit", "quit"]:
                print("👋 Apagando NOVA...")
                break

            if not entrada_usuario.strip():
                continue

            # Enviar al cerebro en la nube
            payload = {"mensaje": entrada_usuario}
            print("📡 Enviando a NOVA Brain...")
            
            respuesta = requests.post(BRAIN_URL, json=payload, timeout=10)
            
            if respuesta.status_code == 200:
                datos = respuesta.json()
                
                # Decir lo que la IA respondió
                if "respuesta_hablada" in datos:
                    print(f"💬 {datos['respuesta_hablada']}")
                
                # Ejecutar la acción
                accion = datos.get("accion", "error")
                parametro = datos.get("parametro", "")
                ejecutar_accion(accion, parametro)
            else:
                print(f"❌ Error de conexión con el cerebro: {respuesta.text}")

        except requests.exceptions.ConnectionError:
            print("❌ No se puede conectar con NOVA Brain. ¿Está encendido el servidor?")
        except Exception as e:
            print(f"❌ Error inesperado: {e}")

if __name__ == "__main__":
    # Verificar dependencias mínimas
    try:
        import requests
    except ImportError:
        print("Instalando dependencia mínima (requests)...")
        subprocess.check_call([sys.executable, "-m", "pip", "install", "requests"])
    
    escuchar_y_actuar()