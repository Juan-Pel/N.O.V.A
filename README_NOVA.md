# NOVA 2.0 - Instalación Rápida

Este proyecto consta de dos partes: el **Cerebro** (en la nube/local) y el **Agente** (en tu dispositivo).

## Paso 1: Obtener API Key Gratuita
1. Ve a [console.groq.com](https://console.groq.com)
2. Regístrate gratis (puedes usar tu cuenta de Google/GitHub).
3. Crea una nueva API Key.
4. Copia esa clave.

## Paso 2: Instalar Dependencias
Necesitas Python instalado. Abre tu terminal y ejecuta:

```bash
pip install flask groq requests
```

## Paso 3: Configurar el Cerebro (`nova_brain.py`)
Abre el archivo `nova_brain.py` y busca la línea:
```python
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "TU_API_KEY_AQUI")
```
Reemplaza `"TU_API_KEY_AQUI"` con la clave que copiaste en el Paso 1, o mejor aún, usa una variable de entorno:

**En Windows (PowerShell):**
```powershell
$env:GROQ_API_KEY="tu_clave_aqui"
python nova_brain.py
```

**En Linux/Mac:**
```bash
export GROQ_API_KEY="tu_clave_aqui"
python nova_brain.py
```

## Paso 4: Ejecutar el Sistema

### Terminal 1: Encender el Cerebro
Ejecuta el servidor que procesará la IA:
```bash
python nova_brain.py
```
Verás: `🚀 NOVA Brain iniciado... Escuchando en http://localhost:5000`

### Terminal 2: Encender el Agente
Abre otra terminal y ejecuta el agente que controla tu PC:
```bash
python nova_agent.py
```

## Paso 5: ¡Pruébalo!
En la terminal del agente, escribe comandos naturales como:
- *"Abre el bloc de notas"*
- *"Busca en google cómo hacer tortilla de patatas"*
- *"Dime la hora actual"*
- *"Abre Chrome"*

## ¿Cómo llevarlo a la nube totalmente?
Si quieres que el cerebro viva en internet para acceder desde cualquier lado:
1. Sube `nova_brain.py` a **Google Colab** o usa **ngrok** en tu PC.
2. Si usas ngrok:
   ```bash
   pip install pyngrok
   # En el código de nova_brain.py, añade esto antes de app.run():
   # from pyngrok import ngrok
   # public_url = ngrok.connect(5000)
   # print(f"URL Pública: {public_url}")
   # BRAIN_URL = str(public_url) + "/procesar" (en el agente)
   ```
3. Cambia la variable `BRAIN_URL` en `nova_agent.py` por la URL pública que te den.

¡Listo! Tienes un JARVIS gratuito, ligero y potente.