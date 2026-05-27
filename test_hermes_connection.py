#!/usr/bin/env python3
"""
Prueba directa de la API de Alibaba Cloud desde Hermes
"""

import asyncio
import os
import sys


def test_alibaba_from_hermes():
    """Prueba la API de Alibaba Cloud desde Hermes"""
    print("🔍 Prueba directa de la API de Alibaba Cloud desde Hermes...")

    # Configurar entorno
    os.environ['LILITH_PROFILE'] = 'alibaba'

    try:
        # Importar componentes de Hermes/Lilith
        sys.path.insert(0, '/mnt/d/Proyectos/Yggdrasil/Asgard/lilith-core')

        from lilith_core.config import Config
        from lilith_core.providers.registry import ProviderRegistry

        # Crear configuración
        config = Config()

        # Obtener registrador de proveedores
        registry = ProviderRegistry(config=config)

        print(f"✅ Perfil activo: {registry.get_active_profile_name()}")

        # Obtener proveedor Alibaba
        provider = registry.get_active_provider()

        print(f"✅ Proveedor obtenido: {type(provider).__name__}")

        # Probar la conexión
        messages = [
            {
                "role": "system",
                "content": "Eres una asistente útil que responde de forma concisa."
            },
            {
                "role": "user",
                "content": "Hola, ¿qué es Hermes? Responde en español en una sola frase."
            }
        ]

        response = asyncio.run(provider.complete(messages))

        print("✅ Conexión exitosa!")
        print(f"📝 Respuesta: {response.get('content', 'No hay respuesta')}")

        if "usage" in response:
            usage = response["usage"]
            print("📊 Uso de tokens:")
            print(f"   - Prompt: {usage.get('prompt_tokens', 0)}")
            print(f"   - Completion: {usage.get('completion_tokens', 0)}")
            print(f"   - Total: {usage.get('total_tokens', 0)}")

        return True

    except Exception as e:
        print(f"❌ Error: {e}")
        import traceback
        print(f"💡 Detalles: {traceback.format_exc()}")
        return False

if __name__ == "__main__":
    success = test_alibaba_from_hermes()

    if success:
        print("\n🎉 Integración de Alibaba Cloud en Hermes completada con éxito!")
        print("\n📊 Resumen:")
        print("   - API Key: sk-sp-D.DRPL.TD1I.MEUCIQCpBrur5a0ii6S201Ur8xwQq6rtIfTl1QPrzQo4bSp5iQIgJumLo/Q1QYi3a0vWr9Kv28TZeP73ovKCAEpPZv2TlRE=")
        print("   - Endpoint: https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1")
        print("   - Region: Singapore")
        print("   - Modelo default: qwen3.6-plus")
        print("   - Posición en fallback chain: #2 (después de BytePlus)")

    sys.exit(0 if success else 1)
