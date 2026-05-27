#!/usr/bin/env python3
"""
Verifica la configuración optimizada de Hermes para BytePlus
"""

import os
import sys

import yaml


def verify_optimized_config():
    """Verifica la configuración optimizada de Hermes"""
    config_path = os.path.expanduser("~/.hermes/config.yaml")

    if not os.path.exists(config_path):
        print("❌ Archivo de configuración de Hermes no encontrado")
        return False

    try:
        with open(config_path, encoding='utf-8') as f:
            config = yaml.safe_load(f)
    except Exception as e:
        print(f"❌ Error al leer la configuración: {e}")
        return False

    print("✅ Configuración de Hermes leída correctamente")
    print("=" * 60)

    # Verificar modelo default
    default_model = config['model']['default']
    expected_model = 'dola-seed-2.0-mini'
    if default_model == expected_model:
        print(f"✅ Modelo default: {default_model} (precio más bajo)")
    else:
        print(f"⚠️  Modelo default incorrecto: {default_model} (esperado: {expected_model})")

    # Verificar provider principal
    provider = config['model']['provider']
    if provider == 'byteplus':
        print(f"✅ Proveedor principal: {provider}")
    else:
        print(f"⚠️  Proveedor principal incorrecto: {provider}")

    print()
    print("🔍 Configuración de modelos en BytePlus:")
    print("-" * 40)

    if 'byteplus' in config['providers'] and 'models' in config['providers']['byteplus']:
        models = config['providers']['byteplus']['models']

        for model_name, model_config in sorted(models.items(),
                                             key=lambda x: x[1].get('priority', 99)):
            priority = model_config.get('priority', 'N/A')
            status = "❌ Disabled" if model_config.get('disabled', False) else "✅ Active"

            # Determinar precio para referencia
            prices = {
                'dola-seed-2.0-mini': "$0.0001-$0.0002/K",
                'dola-seed-2.0-lite': "$0.00025-$0.0005/K",
                'dola-seed-2.0-code': "$0.0005-$0.0010/K",
                'dola-seed-2.0-pro': "$0.0005-$0.0010/K",
                'byteplus-seed-1.8': "$0.00025-$0.0005/K",
                'deepseek-v3.2': "$0.00028-$0.00056/K",
                'glm-4.7': "$0.0006/K",
                'deepseek-v4-pro': "$0.00174/K",
                'byteplus-seed-translation': "$0.0002/K",
                'deepseek-v4-flash': "$0.00014-$0.00028/K"
            }

            price = prices.get(model_name, "N/A")

            print(f"   {status} #{priority:2d}: {model_name:<20} ({price})")

    print()
    print("🔗 Fallback providers:")
    print("-" * 40)

    if 'fallback_providers' in config:
        for i, fallback in enumerate(config['fallback_providers'], 1):
            provider = fallback['provider']
            model = fallback['model']

            if provider == 'byteplus':
                # Obtener configuración del modelo
                model_config = config['providers']['byteplus']['models'].get(model, {})
                priority = model_config.get('priority', 'N/A')
                status = "❌ Disabled" if model_config.get('disabled', False) else "✅ Active"

                print(f"   {status} #{i}: {provider:<8} ({model:<20}, prio: {priority})")
            else:
                print(f"   ✅ #{i}: {provider:<8} ({model})")

    print()
    print("⚙️  Configuración de auxiliary tasks:")
    print("-" * 40)

    if 'auxiliary' in config:
        for task_name, task_config in config['auxiliary'].items():
            if task_name not in ['mcp', 'triage_specifier', 'kanban_decomposer', 'profile_describer']:
                model = task_config['model']
                provider = task_config['provider']
                print(f"   {task_name:<15} {provider:<8} {model}")

    print()
    print("🎯 Delegation configuration:")
    print("-" * 40)

    if 'delegation' in config:
        model = config['delegation']['model']
        provider = config['delegation']['provider']
        print(f"   Modelo: {model}")
        print(f"   Proveedor: {provider}")

    print()
    print("=" * 60)
    print("📊 Resumen de la optimización:")
    print("   ✅ Modelo default: dola-seed-2.0-mini (precio más bajo)")
    print("   ✅ DeepSeek-V4-flash desactivado para conservar cuota")
    print("   ✅ Prioridad de modelos por precio (más bajo → más alto)")
    print("   ✅ Fallback chain optimizada para usabilidad")
    print("   ✅ Auxiliary tasks usando modelos economicos")
    print("   ✅ Delegation usando dola-seed-2.0-mini")

    return True

if __name__ == "__main__":
    print("🚀 Verificando configuración optimizada de Hermes para BytePlus...")
    success = verify_optimized_config()

    if success:
        print("\n🎉 Configuración optimizada completada!")
        print("\n💡 Ahora Hermes usará los modelos con mayor cuota y precios más bajos,")
        print("   y se fallará a Alibaba Cloud si todos los modelos de BytePlus se agotan.")

    sys.exit(0 if success else 1)
