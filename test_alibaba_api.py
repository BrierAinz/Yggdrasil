#!/usr/bin/env python3
"""
Prueba la conexión con la API de Alibaba Cloud
"""

import sys


sys.path.insert(0, "/mnt/d/Proyectos/Yggdrasil/Asgard/lilith-core")

from lilith_core.config import Config
from lilith_core.providers.registry import ProviderRegistry


def test_alibaba_api():
    """Prueba la conexión con la API de Alibaba Cloud"""
    print("🔍 Probando conexión con la API de Alibaba Cloud...")

    try:
        # Crear configuración
        config = Config()

        # Seleccionar perfil Alibaba
        config.set("active_profile", "alibaba")

        # Obtener registrador de proveedores
        registry = ProviderRegistry(config=config)

        print(f"✅ Perfil activo: {registry.get_active_profile_name()}")

        # Obtener proveedor Alibaba
        provider = registry.get_active_provider()

        print(f"✅ Proveedor obtenido: {type(provider).__name__}")

        # Probar la conexión con un mensaje simple
        print("🔄 Enviando prueba de conexión...")

        messages = [
            {"role": "system", "content": "Eres una asistente útil que responde de forma concisa."},
            {
                "role": "user",
                "content": "Hola, ¿cómo estás? Responde en español en una sola frase.",
            },
        ]

        # Obtener respuesta
        import asyncio

        response = asyncio.run(provider.complete(messages))

        print("✅ Conexión exitosa!")
        print(f"📝 Respuesta: {response.get('content', 'No hay respuesta')}")

        # Verificar uso de tokens
        if "usage" in response:
            usage = response["usage"]
            print("📊 Uso de tokens:")
            print(f"   - Prompt: {usage.get('prompt_tokens', 0)}")
            print(f"   - Completion: {usage.get('completion_tokens', 0)}")
            print(f"   - Total: {usage.get('total_tokens', 0)}")

        # Prueba de listado de modelos
        print("\n🔍 Probando listado de modelos...")
        try:
            # Esto es una prueba; la mayoría de proveedores no exponen este método directamente
            # Pero podemos intentar obtener la información de la configuración
            profile = registry.get_profile("alibaba")
            if "models" in profile and "list" in profile["models"]:
                print(f"✅ Modelos disponibles: {len(profile['models']['list'])}")
                print(f"   Modelos: {', '.join(profile['models']['list'])}")
        except Exception as e:
            print(f"⚠️ No se puede listar modelos directamente: {e}")

        return True

    except Exception as e:
        print(f"❌ Error al conectar con Alibaba Cloud: {e}")
        import traceback

        print(f"💡 Detalles: {traceback.format_exc()}")
        return False


if __name__ == "__main__":
    success = test_alibaba_api()
    sys.exit(0 if success else 1)
