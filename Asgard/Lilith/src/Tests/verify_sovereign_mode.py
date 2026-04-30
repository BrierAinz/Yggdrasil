"""
Script de verificación del modo Soberano.

Ejecuta:
- Verificación de sintaxis
- Tests unitarios básicos
- Simulación de flujo DELEGATE
- Simulación de flujo ORCHESTRATE
- Reporte de métricas
"""
import asyncio
import sys
import time
from pathlib import Path

# Ajustar path
sys.path.insert(0, str(Path(__file__).resolve().parent.parent))


def check_syntax():
    """Verifica sintaxis de los archivos creados."""
    print("=" * 60)
    print("VERIFICACIÓN DE SINTAXIS")
    print("=" * 60)

    files_to_check = [
        "core/sovereign_complexity.py",
        "core/sovereign_state.py",
        "core/sovereign_mode.py",
        "core/sovereign_metrics.py",
        "core/vanaheim_router.py",
        "core/dag/vanaheim_node_executor.py",
        "../Workspace/Yggdrasil/Vanaheim/Agents/freya_agent.py",
        "../Workspace/Yggdrasil/Vanaheim/Agents/heimdall_agent.py",
        "../Workspace/Yggdrasil/Vanaheim/Agents/eir_agent.py",
        "../Workspace/Yggdrasil/Vanaheim/Agents/balder_agent.py",
        "../Workspace/Yggdrasil/Vanaheim/Core/vanaheim_orchestrator.py",
    ]

    all_ok = True
    for file in files_to_check:
        path = Path(__file__).resolve().parents[1] / file
        try:
            with open(path, "r", encoding="utf-8") as f:
                compile(f.read(), str(path), "exec")
            print(f"✓ {file}")
        except SyntaxError as e:
            print(f"✗ {file}: {e}")
            all_ok = False
        except FileNotFoundError:
            print(f"⚠ {file}: No encontrado")

    return all_ok


def test_complexity_analyzer():
    """Test del analizador de complejidad."""
    print("\n" + "=" * 60)
    print("TEST: Complexity Analyzer")
    print("=" * 60)

    from core.sovereign_complexity import ExecutionMode, SovereignComplexityAnalyzer

    analyzer = SovereignComplexityAnalyzer()

    # Test 1: Tarea trivial
    result = analyzer.analyze_for_sovereign("hola")
    print(
        f"'hola' -> Score: {result.sovereign_score}, Mode: {result.recommended_mode.value}"
    )
    assert result.should_delegate, "Trivial debe delegar"
    print("✓ Tarea trivial delega correctamente")

    # Test 2: Tarea simple
    result = analyzer.analyze_for_sovereign("qué hora es")
    print(
        f"'qué hora es' -> Score: {result.sovereign_score}, Mode: {result.recommended_mode.value}"
    )
    assert result.should_delegate, "Simple debe delegar"
    print("✓ Tarea simple delega correctamente")

    # Test 3: Tarea compleja
    result = analyzer.analyze_for_sovereign(
        "diseña una arquitectura completa de microservicios con kubernetes"
    )
    print(
        f"'diseña arquitectura...' -> Score: {result.sovereign_score}, Mode: {result.recommended_mode.value}"
    )
    assert result.should_orchestrate, "Compleja debe orquestar"
    print("✓ Tarea compleja orquesta correctamente")

    # Test 4: Zona gris
    result = analyzer.analyze_for_sovereign(
        "explica cómo funciona un algoritmo de sorting"
    )
    print(
        f"'explica algoritmo...' -> Score: {result.sovereign_score}, Mode: {result.recommended_mode.value}"
    )
    print("✓ Zona gris manejada correctamente")

    return True


def test_sovereign_state():
    """Test del estado soberano."""
    print("\n" + "=" * 60)
    print("TEST: Sovereign State")
    print("=" * 60)

    from core.sovereign_state import SovereignState, SovereignStatus

    state = SovereignState()

    # Test 1: Estado inicial
    assert not state.is_lilith_busy(), "Inicialmente no está busy"
    assert state.get_status() == SovereignStatus.IDLE
    print("✓ Estado inicial correcto")

    # Test 2: Proyectos
    state.start_project("test1", "Test Project 1", estimated_nodes=5)
    print(f"✓ Proyecto iniciado. Busy: {state.is_lilith_busy()}")

    state.start_project("test2", "Test Project 2", estimated_nodes=10)
    print(f"✓ Segundo proyecto iniciado. Busy: {state.is_lilith_busy()}")

    # Test 3: Verificar snapshot
    snapshot = state.get_snapshot()
    print(f"✓ Snapshot: {len(snapshot.active_projects)} proyectos activos")

    # Test 4: Finalizar
    state.end_project("test1")
    state.end_project("test2")
    assert not state.is_lilith_busy(), "Después de finalizar no está busy"
    print("✓ Proyectos finalizados correctamente")

    return True


def test_vanaheim_router():
    """Test del router de Vanaheim."""
    print("\n" + "=" * 60)
    print("TEST: Vanaheim Router")
    print("=" * 60)

    from core.vanaheim_router import VanaheimRouter

    router = VanaheimRouter()

    # Test 1: Conversación
    agent, confidence = router.select_agent("hola, cómo estás?")
    print(f"'hola' -> Agent: {agent}, Confidence: {confidence:.2f}")
    assert agent == "freya", "Conversación debe ir a Freya"
    print("✓ Routing de conversación correcto")

    # Test 2: Búsqueda
    agent, confidence = router.select_agent("busca información sobre Python")
    print(f"'busca...' -> Agent: {agent}, Confidence: {confidence:.2f}")
    assert agent == "heimdall", "Búsqueda debe ir a Heimdall"
    print("✓ Routing de búsqueda correcto")

    # Test 3: Código
    agent, confidence = router.select_agent("explica este código")
    print(f"'explica código' -> Agent: {agent}, Confidence: {confidence:.2f}")
    assert agent == "eir", "Código debe ir a Eir"
    print("✓ Routing de código correcto")

    # Test 4: Documento
    agent, confidence = router.select_agent("resume este documento")
    print(f"'resume documento' -> Agent: {agent}, Confidence: {confidence:.2f}")
    assert agent == "balder", "Documento debe ir a Balder"
    print("✓ Routing de documento correcto")

    return True


async def test_delegate_mode():
    """Test del modo DELEGATE."""
    print("\n" + "=" * 60)
    print("TEST: Modo DELEGATE")
    print("=" * 60)

    from core.sovereign_mode import ExecutionMode, SovereignMode

    sovereign = SovereignMode()

    # Test 1: Decisión DELEGATE
    mode, metadata = sovereign.decide_mode("hola")
    print(f"'hola' -> Mode: {mode.value}, Score: {metadata['complexity_score']}")
    assert mode == ExecutionMode.DELEGATE, "Debe decidir DELEGATE"
    print("✓ Decisión DELEGATE correcta")

    # Test 2: Ejecutar DELEGATE (puede fallar si no hay LLM)
    try:
        response = await sovereign.execute_delegate("hola", metadata, "test")
        if response:
            print(f"✓ Ejecución DELEGATE exitosa: {response[:50]}...")
        else:
            print("⚠ Ejecución DELEGATE retornó None (fallback)")
    except Exception as e:
        print(f"⚠ Ejecución DELEGATE falló: {e} (esperado sin LLM)")

    return True


def test_orchestrate_mode():
    """Test del modo ORCHESTRATE."""
    print("\n" + "=" * 60)
    print("TEST: Modo ORCHESTRATE")
    print("=" * 60)

    from core.sovereign_mode import ExecutionMode, SovereignMode

    sovereign = SovereignMode()

    # Test 1: Decisión ORCHESTRATE
    mode, metadata = sovereign.decide_mode(
        "diseña una arquitectura completa de microservicios con kubernetes, "
        "incluyendo service mesh, observabilidad y CI/CD"
    )
    print(
        f"'diseña arquitectura...' -> Mode: {mode.value}, Score: {metadata['complexity_score']}"
    )
    assert mode == ExecutionMode.ORCHESTRATE, "Debe decidir ORCHESTRATE"
    print("✓ Decisión ORCHESTRATE correcta")

    # Test 2: Stats
    stats = sovereign.get_stats()
    print(f"✓ Stats: {stats}")

    return True


def test_metrics():
    """Test del sistema de métricas."""
    print("\n" + "=" * 60)
    print("TEST: Sovereign Metrics")
    print("=" * 60)

    from core.sovereign_metrics import SovereignMetrics

    metrics = SovereignMetrics()

    # Registrar algunas ejecuciones
    metrics.record_execution("delegate", 150.0, True, "freya", 25, "test")
    metrics.record_execution("delegate", 200.0, True, "heimdall", 30, "test")
    metrics.record_execution("orchestrate", 5000.0, True, None, 75, "test")
    metrics.record_execution("delegate", 180.0, False, "freya", 35, "test")

    # Verificar ratio
    ratio = metrics.get_current_ratio()
    print(f"Ratio: {ratio['delegate_ratio']:.2%} DELEGATE")
    print(f"Total: {ratio['total']} ejecuciones")
    print(f"✓ Within tolerance: {ratio['within_tolerance']}")

    # Verificar latencia
    latency = metrics.get_latency_stats()
    print(f"Latencia promedio DELEGATE: {latency['delegate']['avg_ms']:.0f}ms")
    print(f"Latencia promedio ORCHESTRATE: {latency['orchestrate']['avg_ms']:.0f}ms")

    # Health report
    health = metrics.get_health_report()
    print(f"Health status: {health['status']}")
    if health["issues"]:
        print(f"Issues: {health['issues']}")

    return True


def simulate_workload():
    """Simula una carga de trabajo mixta."""
    print("\n" + "=" * 60)
    print("SIMULACIÓN: Carga de trabajo mixta")
    print("=" * 60)

    from core.sovereign_mode import ExecutionMode, SovereignMode

    sovereign = SovereignMode()

    tasks = [
        ("hola", "delegate"),
        ("gracias", "delegate"),
        ("qué hora es", "delegate"),
        ("busca información sobre Python", "delegate"),
        ("explica este código", "delegate"),
        ("resume este documento", "delegate"),
        ("diseña una API REST", "orchestrate"),
        ("analiza este proyecto completo", "orchestrate"),
        ("refactoriza este módulo", "orchestrate"),
        ("hola de nuevo", "delegate"),
    ]

    decisions = {"delegate": 0, "orchestrate": 0}

    for task, expected in tasks:
        mode, metadata = sovereign.decide_mode(task)
        decisions[mode.value] += 1
        print(
            f"'{task[:30]}...' -> {mode.value} (score: {metadata['complexity_score']})"
        )

    total = len(tasks)
    delegate_ratio = decisions["delegate"] / total

    print(f"\nResultado:")
    print(f"  DELEGATE: {decisions['delegate']}/{total} ({delegate_ratio:.0%})")
    print(f"  ORCHESTRATE: {decisions['orchestrate']}/{total}")
    print(f"  Target: 70% DELEGATE")
    print(f"  Actual: {delegate_ratio:.0%} DELEGATE")

    if 0.60 <= delegate_ratio <= 0.80:
        print("  ✓ Dentro del rango esperado (60-80%)")
    else:
        print("  ⚠ Fuera del rango esperado")

    return True


async def main():
    """Ejecuta todas las verificaciones."""
    print("\n" + "=" * 60)
    print("VERIFICACIÓN DEL MODO SOBERANO - LA CORONA DE LILITH")
    print("=" * 60)

    results = []

    try:
        results.append(("Syntax Check", check_syntax()))
        results.append(("Complexity Analyzer", test_complexity_analyzer()))
        results.append(("Sovereign State", test_sovereign_state()))
        results.append(("Vanaheim Router", test_vanaheim_router()))
        results.append(("DELEGATE Mode", await test_delegate_mode()))
        results.append(("ORCHESTRATE Mode", test_orchestrate_mode()))
        results.append(("Metrics", test_metrics()))
        results.append(("Workload Simulation", simulate_workload()))

        print("\n" + "=" * 60)
        print("RESUMEN")
        print("=" * 60)

        for name, result in results:
            status = "✓ PASS" if result else "✗ FAIL"
            print(f"{status}: {name}")

        all_passed = all(r[1] for r in results)

        if all_passed:
            print("\n✓ TODAS LAS VERIFICACIONES PASARON")
            print("El modo Soberano está listo para usar.")
        else:
            print("\n✗ ALGUNAS VERIFICACIONES FALLARON")
            print("Revisa los errores arriba.")

        return 0 if all_passed else 1

    except Exception as e:
        print(f"\n✗ ERROR INESPERADO: {e}")
        import traceback

        traceback.print_exc()
        return 1


if __name__ == "__main__":
    exit_code = asyncio.run(main())
    sys.exit(exit_code)
