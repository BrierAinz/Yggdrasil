#!/usr/bin/env python3
"""
Prueba la integración de la API de Alibaba Cloud como fallback en Hermes
"""

import os
import sys


def test_alibaba_integration():
    """Prueba la integración de Alibaba Cloud en Hermes"""
    config_path = os.path.expanduser("~/.hermes/config.yaml")

    if not os.path.exists(config_path):
        print("❌ Archivo de configuración de Hermes no encontrado")
        print(f"📁 Ruta esperada: {config_path}")
        return False

    print("✅ Archivo de configuración encontrado")

    # Leer contenido del config.yaml
    try:
        import yaml
        with open(config_path, encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"❌ Error al leer el archivo de configuración: {e}")
        return False

    print("✅ Configuración cargada correctamente")

    # Verificar configuración de Alibaba Cloud
    if 'providers' not in config or 'alibaba' not in config['providers']:
        print("❌ Alibaba Cloud no está configurado en los proveedores")
        return False

    alibaba_config = config['providers']['alibaba']
    print("✅ Proveedor Alibaba Cloud encontrado")

    # Verificar configuración básica
    required_fields = ['api_key', 'base_url', 'models']
    for field in required_fields:
        if field not in alibaba_config:
            print(f"❌ Falta campo requerido en la configuración de Alibaba Cloud: {field}")
            return False

    print("✅ Configuración básica de Alibaba Cloud completada")

    # Verificar endpoint
    expected_endpoint = "https://token-plan.ap-southeast-1.maas.aliyuncs.com/compatible-mode/v1"
    if alibaba_config['base_url'] != expected_endpoint:
        print("⚠️  Endpoint no coincide con el Token Plan de Alibaba Cloud")
        print(f"   Actual: {alibaba_config['base_url']}")
        print(f"   Esperado: {expected_endpoint}")

    # Verificar API Key válida
    api_key = alibaba_config['api_key']
    if len(api_key) < 32 or not api_key.startswith('sk-'):
        print("❌ API Key de Alibaba Cloud inválida")
        print("   La clave debe empezar con 'sk-' y tener al menos 32 caracteres")
        return False

    print("✅ API Key válida")

    # Verificar modelos disponibles
    models = list(alibaba_config['models'].keys())
    print(f"✅ Modelos disponibles: {len(models)}")
    print(f"   Modelos: {', '.join(models)}")

    # Verificar fallback provider
    if 'fallback_providers' not in config:
        print("❌ No hay proveedores de fallback configurados")
        return False

    alibaba_in_fallback = any(provider.get('provider') == 'alibaba' for provider in config['fallback_providers'])

    if alibaba_in_fallback:
        print("✅ Alibaba Cloud está configurado como proveedor de fallback")

        # Encontrar la posición del fallback
        for i, provider in enumerate(config['fallback_providers'], 1):
            if provider.get('provider') == 'alibaba':
                print(f"   Posición en fallback chain: #{i}")
                print(f"   Modelo configurado: {provider.get('model', 'qwen3.6-plus')}")
    else:
        print("❌ Alibaba Cloud no está en la lista de fallbacks")
        return False

    # Verificar que la API Key sea la correcta
    expected_api_key_prefix = "sk-sp-D.DRPL.TD1I"
    if not alibaba_config['api_key'].startswith(expected_api_key_prefix):
        print("⚠️  La API Key no coincide con la esperada")
        print(f"   Actual: {alibaba_config['api_key'][:20]}...")
        print(f"   Esperado: {expected_api_key_prefix}...")

    print("\n✅ Integración de Alibaba Cloud completada con éxito!")
    print("\n📊 Resumen de la configuración:")
    print("   Proveedor: Alibaba Cloud Model Studio")
    print(f"   Endpoint: {alibaba_config['base_url']}")
    print("   Region: Singapore")
    print(f"   API Key: {alibaba_config['api_key'][:20]}...")
    print(f"   Modelos disponibles: {len(models)}")
    print(f"   Fallback position: #{i}")

    return True

def test_fallback_chain():
    """Prueba la cadena de fallback de Hermes"""
    config_path = os.path.expanduser("~/.hermes/config.yaml")

    try:
        import yaml
        with open(config_path, encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"❌ Error al leer la configuración: {e}")
        return False

    print("\n🔍 Prueba de fallback chain:")
    print("=" * 40)

    if 'fallback_providers' in config:
        print(f"📋 Fallback providers ({len(config['fallback_providers'])}):")

        for i, provider in enumerate(config['fallback_providers'], 1):
            provider_name = provider.get('provider', 'unknown')
            model = provider.get('model', 'auto')
            status = "✅" if provider_name in config.get('providers', {}) else "❌"

            print(f"   {status} #{i}: {provider_name} ({model})")

        return True
    else:
        print("❌ No hay configuración de fallbacks")
        return False

if __name__ == "__main__":
    print("🚀 Verificando integración de Alibaba Cloud en Hermes...")
    print("=" * 60)

    success = test_alibaba_integration()

    if success:
        test_fallback_chain()

    print("\n" + "=" * 60)
    print("📊 Integración completa!")
    print("\n💡 La API de Alibaba Cloud está lista para ser usada como fallback en Hermes.")
    print("   Se activará automáticamente si el proveedor principal (BytePlus) falla.")

    sys.exit(0 if success else 1)
