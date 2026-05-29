#!/usr/bin/env python3
"""
Verifica la disponibilidad del endpoint de Alibaba Cloud Model Studio
"""

import time

import httpx


def test_endpoint(endpoint, api_key):
    """Prueba la disponibilidad de un endpoint"""
    headers = {"Authorization": f"Bearer {api_key}", "Content-Type": "application/json"}

    payload = {
        "model": "qwen3.6-plus",
        "messages": [
            {"role": "system", "content": "Eres una asistente útil que responde de forma concisa."},
            {
                "role": "user",
                "content": "Hola, ¿cómo estás? Responde en español en una sola frase.",
            },
        ],
        "max_tokens": 50,
        "temperature": 0.7,
    }

    try:
        response = httpx.post(
            f"{endpoint}/chat/completions", headers=headers, json=payload, timeout=60
        )

        return response.status_code, response.text

    except Exception as e:
        return None, str(e)


def main():
    """Función principal"""
    print("🔍 Verificando endpoints de Alibaba Cloud Model Studio...")
    print("=" * 60)

    api_keys = [
        ("sk-249706f9b63f4c8f917a4daf087ed840", "API Key 1"),
        ("sk-sp-D.DRPL.cn****BwNrNv9B9d75tG3", "API Key 2"),
    ]

    endpoints = [
        (
            "https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1",
            "Token Plan Standard",
        ),
        ("https://dashscope.aliyuncs.com/api/v1", "DashScope Standard"),
        ("https://dashscope.aliyuncs.com/compatible-mode/v1", "DashScope Compatible"),
        ("https://api.modelscope.cn/compatible-mode/v1", "ModelScope Compatible"),
        ("https://model.aliyuncs.com/compatible-mode/v1", "Aliyun Model Service"),
    ]

    for api_key, key_name in api_keys:
        print(f"\n🔑 Pruebas con {key_name}:")
        print("-" * 40)

        for endpoint, endpoint_name in endpoints:
            print(f"  🔗 Pruebas de {endpoint_name} ({endpoint})")

            status_code, response_text = test_endpoint(endpoint, api_key)

            if status_code is not None:
                print(f"    📶 Estado: {status_code}")
                if status_code == 200:
                    print("    ✅ Exito")
                elif status_code == 401:
                    print("    🔐 Error de autenticación")
                elif status_code == 404:
                    print("    🔍 Recurso no encontrado")
                else:
                    print(f"    ❌ Error: {status_code}")

                if len(response_text) > 200:
                    print(f"    📨 Respuesta: {response_text[:200]}...")
                else:
                    print(f"    📨 Respuesta: {response_text}")
            else:
                print(f"    ⚠️  No se puede conectar: {response_text}")

            time.sleep(2)

    print("\n" + "=" * 60)
    print("📊 Resumen de pruebas completado")
    print("\n💡 Observaciones:")
    print("  - Si todas las pruebas fallan, verifica:")
    print("    1. La validez de las API Keys")
    print("    2. Que las API Keys esten asociadas a la region correcta (Singapore)")
    print("    3. Que el endpoint esté disponible en tu región")
    print("    4. Que la API Key tenga permisos para acceder a los servicios requeridos")


if __name__ == "__main__":
    main()
