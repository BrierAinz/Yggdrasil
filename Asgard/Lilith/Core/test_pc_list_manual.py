"""
Test manual para verificar que pc_list realmente ejecuta el PC Agent.
Ejecutar desde Core/:  python test_pc_list_manual.py
"""
import sys
from pathlib import Path

# Asegurar que el path raíz está disponible
project_root = Path(__file__).resolve().parent
sys.path.insert(0, str(project_root))


def test_pc_list():
    """Prueba pc_list directamente en el ToolRegistry."""
    print("=" * 60)
    print("TEST: Verificar pc_list ToolRegistry")
    print("=" * 60)

    try:
        from src.core.tools.registry import create_default_registry

        print("\n1. Creando registry...")
        reg = create_default_registry(project_root)
        print(f"   ✓ Registry creado")

        print("\n2. Obteniendo tool pc_list...")
        tool = reg.get("pc_list")
        print(f"   ✓ Tool: {tool}")
        print(f"   ✓ Nombre: {tool.name}")
        print(f"   ✓ Descripción: {tool.get_description()}")

        print("\n3. Ejecutando pc_list con path='descargas'...")
        result = tool.run({"path": "descargas"})
        print(f"   ✓ Resultado type: {type(result)}")

        # Manejar diferentes formatos de resultado
        if hasattr(result, "success"):
            print(f"   ✓ Success: {result.success}")
            print(
                f"   ✓ Output: {str(result.output)[:200]}..."
                if result.output
                else "   ✓ Output: (vacío)"
            )
            if hasattr(result, "error") and result.error:
                print(f"   ✗ Error: {result.error}")
        else:
            # ToolResult dict
            print(f"   ✓ Result: {result}")

    except Exception as e:
        print(f"\n   ✗ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("TEST COMPLETADO")
    print("=" * 60)
    return True


def test_pc_agent_direct():
    """Prueba PCAgent directamente sin el registry."""
    print("\n" + "=" * 60)
    print("TEST: PCAgent directo")
    print("=" * 60)

    try:
        from src.core.pc_agent import PCAgent

        print("\n1. Creando PCAgent...")
        pc = PCAgent(project_root)
        print(f"   ✓ PCAgent creado")

        print("\n2. Listando descargas...")
        import os

        downloads_path = os.path.expandvars(r"C:\Users\Game_\Downloads")
        result = pc.list_dir(downloads_path)
        print(f"   ✓ Success: {result.success}")
        print(
            f"   ✓ Output:\n{result.output[:500]}..."
            if result.output
            else "   ✓ Output: (vacío)"
        )
        if not result.success:
            print(f"   ✗ Error: {result.output}")

    except Exception as e:
        print(f"\n   ✗ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("TEST COMPLETADO")
    print("=" * 60)
    return True


def test_planner():
    """Prueba el Planner con un mensaje de listado."""
    print("\n" + "=" * 60)
    print("TEST: Planner con 'dime que archivos hay en descargas'")
    print("=" * 60)

    try:
        from src.core.learning import LearningEngine, LocalIntentClassifier
        from src.core.memory import MemoryManager
        from src.core.planner import Planner

        print("\n1. Creando Planner...")
        memory_manager = MemoryManager(project_root)
        learning_engine = LearningEngine(memory_manager)
        local_classifier = LocalIntentClassifier(project_root)
        planner = Planner(
            memory_manager=memory_manager,
            learning_engine=learning_engine,
            local_intent_classifier=local_classifier,
        )
        print(f"   ✓ Planner creado")

        test_message = "dime que archivos hay en descargas"
        print(f"\n2. Planificando: '{test_message}'")
        result = planner.plan(test_message, role="owner")
        steps = getattr(result, "steps", result) or []
        print(f"   ✓ Steps generados: {[s.tool_name for s in steps]}")
        print(f"   ✓ Confidence: {getattr(result, 'confidence', 'N/A')}")
        print(f"   ✓ Reason: {getattr(result, 'confidence_reason', 'N/A')}")

        for i, step in enumerate(steps):
            print(f"\n   Step {i+1}: {step.tool_name}")
            print(f"   Params: {step.params}")

    except Exception as e:
        print(f"\n   ✗ ERROR: {e}")
        import traceback

        traceback.print_exc()
        return False

    print("\n" + "=" * 60)
    print("TEST COMPLETADO")
    print("=" * 60)
    return True


if __name__ == "__main__":
    print("\n" + "#" * 60)
    print("# TEST MANUAL PC_LIST")
    print("#" * 60 + "\n")

    test_planner()
    test_pc_list()
    test_pc_agent_direct()

    print("\n" + "#" * 60)
    print("# TODOS LOS TESTS FINALIZADOS")
    print("#" * 60)
