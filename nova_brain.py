import os
import json
from flask import Flask, request, jsonify
from groq import Groq

# Inicializar Flask (el servidor web ligero)
app = Flask(__name__)

# CONFIGURACIÓN
# Obtén tu API KEY gratis en https://console.groq.com
# Puedes guardarla en una variable de entorno para seguridad: export GROQ_API_KEY='tu_key'
GROQ_API_KEY = os.getenv("GROQ_API_KEY", "TU_API_KEY_AQUI") 

client = Groq(api_key=GROQ_API_KEY)

# Modelo rápido y potente (Llama 3.1 8B es excelente y barato/free en Groq)
MODEL_NAME = "llama-3.1-8b-instant"

# Instrucción del sistema para que NOVA actúe como un traductor de intenciones
SYSTEM_PROMPT = """
Eres NOVA, un asistente inteligente tipo JARVIS. 
Tu ÚNICA función es recibir texto del usuario y devolver un objeto JSON estricto con la acción a realizar.
NO respondas con texto conversacional, solo JSON.

Formato de salida OBLIGATORIO:
{
    "accion": "tipo_de_accion",
    "parametro": "detalle_opcional",
    "respuesta_hablada": "lo_que_debes_decir_al_usuario"
}

Tipos de acción soportados:
- "abrir_app": parametro = nombre del programa (ej: "chrome", "notepad", "calculadora")
- "buscar_web": parametro = términos de búsqueda
- "ejecutar_comando": parametro = comando de terminal (solo si es seguro)
- "decir": parametro = texto a decir (si solo quieres hablar)
- "error": si no entiendes la petición

Ejemplo de entrada: "Abre Google Chrome y busca noticias de tecnología"
Ejemplo de salida: {"accion": "abrir_app", "parametro": "chrome", "respuesta_hablada": "Abriendo Chrome para buscar noticias."}
"""

@app.route('/procesar', methods=['POST'])
def procesar_comando():
    data = request.json
    usuario_input = data.get('mensaje', '')

    if not usuario_input:
        return jsonify({"error": "No se recibió mensaje"}), 400

    try:
        # Llamada a la IA de Groq
        chat_completion = client.chat.completions.create(
            messages=[
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": usuario_input}
            ],
            model=MODEL_NAME,
            temperature=0.1, # Baja temperatura para respuestas más deterministas
            max_tokens=200,
            response_format={"type": "json_object"} # Forzar salida JSON
        )

        respuesta_ia = chat_completion.choices[0].message.content
        
        # Parsear la respuesta para asegurar que es JSON válido
        resultado = json.loads(respuesta_ia)
        
        print(f"Usuario: {usuario_input}")
        print(f"NOVA Decidió: {resultado}")
        
        return jsonify(resultado)

    except Exception as e:
        error_msg = str(e)
        print(f"Error: {error_msg}")
        return jsonify({
            "accion": "error",
            "parametro": error_msg,
            "respuesta_hablada": "Lo siento, tuve un problema procesando tu orden."
        }), 500

if __name__ == '__main__':
    print("🚀 NOVA Brain iniciado en modo servidor...")
    print("Escuchando en http://localhost:5000")
    # debug=True permite recargar cambios, host='0.0.0.0' permite conexiones externas (útil para ngrok/colab)
    app.run(host='0.0.0.0', port=5000, debug=True)