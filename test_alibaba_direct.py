#!/usr/bin/env python3
"""
Prueba directa de la API de Alibaba Cloud Token Plan
"""


import httpx


def test_alibaba_direct(api_key, base_url):
    """Prueba directa de la API de Alibaba Cloud Token Plan"""
    print(f"🔍 Probando API de Alibaba Cloud Token Plan con clave: {api_key[:10]}...")

    headers = {
        "Authorization": f"Bearer {api_key}",
        "Content-Type": "application/json"
    }

    payload = {
        "model": "qwen3.6-plus",
        "messages": [
            {
                "role": "system",
                "content": "Eres una asistente útil que responde de forma concisa."
            },
            {
                "role": "user",
                "content": "Hola, ¿cómo estás? Responde en español en una sola frase."
            }
        ],
        "max_tokens": 50,
        "temperature": 0.7
    }

    try:
        response = httpx.post(
            f"{base_url}/chat/completions",
            headers=headers,
            json=payload,
            timeout=60
        )

        print(f"📶 Código de estado: {response.status_code}")

        if response.status_code == 200:
            data = response.json()
            print("✅ Solicitud exitosa!")

            if "choices" in data and len(data["choices"]) > 0:
                print(f"📝 Respuesta: {data['choices'][0]['message']['content']}")

            if "usage" in data:
                print("📊 Uso de tokens:")
                print(f"   - Prompt: {data['usage']['prompt_tokens']}")
                print(f"   - Completion: {data['usage']['completion_tokens']}")
                print(f"   - Total: {data['usage']['total_tokens']}")

            return True
        else:
            print(f"❌ Error: {response.text}")
            return False

    except Exception as e:
        print(f"❌ Error de conexión: {e}")
        import traceback
        print(f"💡 Detalles: {traceback.format_exc()}")
        return False

def main():
    """Función principal para probar las API Keys"""

    # URL del endpoint Token Plan
    BASE_URL = "https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"

    # API Keys para probar
    api_keys = [
        "sk-249706f9b63f4c8f917a4daf087ed840",
        "sk-sp-D.DRPL.cn****BwNrNv9B9d75tG3"
    ]

    print("🚀 Iniciando pruebas de la API de Alibaba Cloud...")
    print("=" * 50)

    for i, api_key in enumerate(api_keys, 1):
        print(f"\n📋 Prueba {i}: API Key {api_key[:10]}...")

        success = test_alibaba_direct(api_key, BASE_URL)

        if success:
            print(f"✅ API Key {api_key[:10]} funciona correctamente")
            break
        else:
            print(f"❌ API Key {api_key[:10]} no funciona")

    print("\n" + "=" * 50)
    print("📊 Resumen de pruebas completado")

    return success

if __name__ == "__main__":
    success = main()
    exit_code = 0 if success else 1
    import sys
    sys.exit(exit_code)
