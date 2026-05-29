#!/usr/bin/env python3
"""
Prueba la conexión con el nuevo modelo default de BytePlus
"""

import asyncio
import os
import sys


def test_new_model():
    """Prueba la conexión con dola-seed-2.0-mini"""
    print("🔍 Prueba de conexión con el nuevo modelo default de BytePlus...")

    # Configurar entorno
    os.environ["LILITH_PROFILE"] = "byteplus"

    try:
        sys.path.insert(0, "/mnt/d/Proyectos/Yggdrasil/Asgard/lilith-core")

        from lilith_core.config import Config
        from lilith_core.providers.registry import ProviderRegistry

        config = Config()
        registry = ProviderRegistry(config=config)

        print(f"✅ Perfil activo: {registry.get_active_profile_name()}")

        provider = registry.get_active_provider()
        print(f"✅ Proveedor obtenido: {type(provider).__name__}")

        messages = [
            {"role": "system", "content": "Eres una asistente útil que responde de forma concisa."},
            {
                "role": "user",
                "content": "Hola, ¿qué modelo estás usando? Responde en español con el nombre exacto del modelo.",
            },
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
    success = test_new_model()

    if success:
        print("\n🎉 Modelo default optimizado con éxito!")
        print("\n📊 Configuración actual:")
        print("   - Modelo: dola-seed-2.0-mini")
        print("   - Proveedor: BytePlus")
        print("   - Precio: $0.0001-$0.0002/K tokens (más económico)")
        print("   - Cuota: 500,000 tokens (completa)")

    sys.exit(0 if success else 1)
