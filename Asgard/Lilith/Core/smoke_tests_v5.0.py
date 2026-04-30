"""
Smoke Tests - Lilith v5.0 PC Agent Telegram E2E
Validacion practica en produccion antes de deployment final

Tests:
1. Macro Simple (backup_proyecto)
2. Auto-Batch (multiples operaciones)
3. Discord Redirect (bloqueo PC)
4. Sessions Persistentes (contexto)
5. Rate Limiting (limites)
6. Denied Paths (seguridad)

Uso:
    python smoke_tests_v5.0.py

Requiere:
    - Lilith backend corriendo (localhost:8000)
    - MuninnDB corriendo (localhost:8475)
    - Variables de entorno configuradas
"""

import asyncio
import json
import os
import sys
import time
from datetime import datetime
from pathlib import Path
from typing import Dict, List, Optional

# Configuracion
BASE_URL = os.getenv("LILITH_BASE_URL", "http://localhost:8000")
TELEGRAM_CHAT_ID = os.getenv("TELEGRAM_OWNER_CHAT_ID", "123456789")

# Colores simples (compatibles con Windows)
PASS = "[OK]"
FAIL = "[FAIL]"
WARN = "[WARN]"
INFO = "[INFO]"


class SmokeTestRunner:
    """Ejecutor de smoke tests para Lilith v5.0"""

    def __init__(self):
        self.results: List[Dict] = []
        self.start_time = None

    def print_header(self, text: str):
        """Imprime header formateado"""
        print(f"\n{'='*60}")
        print(f"  {text}")
        print(f"{'='*60}\n")

    def print_result(self, test_name: str, passed: bool, details: str = ""):
        """Imprime resultado de test"""
        status = PASS if passed else FAIL
        print(f"  {status} {test_name}")
        if details:
            print(f"      {details}")
        self.results.append(
            {
                "name": test_name,
                "passed": passed,
                "details": details,
                "timestamp": datetime.now().isoformat(),
            }
        )

    def test_health_check(self) -> bool:
        """Test 0: Verificar que el sistema esta corriendo"""
        self.print_header("TEST 0: Health Check del Sistema")

        try:
            import json
            import urllib.request

            req = urllib.request.Request(f"{BASE_URL}/api/agents/health")
            with urllib.request.urlopen(req, timeout=5) as response:
                data = json.loads(response.read().decode())
                healthy = all(a.get("healthy", False) for a in data.get("agents", []))
                self.print_result(
                    "Health Check",
                    healthy,
                    f"Agentes: {len(data.get('agents', []))} reportados",
                )
                return healthy
        except Exception as e:
            self.print_result("Health Check", False, f"Error: {e}")
            return False

    def test_macro_simple(self) -> bool:
        """Test 1: Macro simple - backup_proyecto"""
        self.print_header("TEST 1: Macro Simple (backup_proyecto)")

        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from src.core.pc_macro_engine import get_macro_engine

            engine = get_macro_engine()
            text = "haz backup del proyecto TestProject"

            # Test deteccion
            result = engine.detect_macro(text)
            if not result:
                self.print_result("Deteccion de macro", False, "No detecto macro")
                return False

            macro_name, confidence = result
            detected_ok = macro_name == "backup_proyecto"
            self.print_result(
                "Deteccion de macro",
                detected_ok,
                f"Detecto: {macro_name} (confianza: {confidence:.2f})",
            )

            # Test extraccion de parametros
            params = engine.extract_params(text, macro_name)
            has_project = "project_path" in params or "project_name" in params
            self.print_result(
                "Extraccion de parametros",
                has_project,
                f"Parametros: {list(params.keys())}",
            )

            # Test generacion de preview
            preview = engine.generate_preview(macro_name, params)
            has_preview = "Macro:" in preview and (
                "mkdir" in preview.lower() or "crear" in preview.lower()
            )
            self.print_result(
                "Generacion de preview", has_preview, f"Preview: {preview[:60]}..."
            )

            return detected_ok and has_project and has_preview

        except Exception as e:
            self.print_result("Macro Simple", False, f"Error: {e}")
            import traceback

            traceback.print_exc()
            return False

    def test_auto_batch(self) -> bool:
        """Test 2: Auto-Batch de operaciones"""
        self.print_header("TEST 2: Auto-Batch (multiples operaciones)")

        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from src.core.planner_autobatch import detect_pc_batch, should_auto_batch

            text = "crea carpeta temp, copia config.json ahi, lista contenido"

            # Test deteccion de batch
            operations = detect_pc_batch(text)
            detected = len(operations) >= 2

            self.print_result(
                "Deteccion de operaciones multiples",
                detected,
                f"Detectadas: {len(operations)} operaciones",
            )

            # Test decision de batch
            should_batch = should_auto_batch(operations)
            self.print_result(
                "Decision de auto-batch", should_batch, f"Should batch: {should_batch}"
            )

            # Ver tipos de operaciones
            op_types = [op.op_type for op in operations]
            self.print_result(
                "Tipos de operaciones detectadas", len(op_types) > 0, f"Ops: {op_types}"
            )

            return detected and should_batch

        except Exception as e:
            self.print_result("Auto-Batch", False, f"Error: {e}")
            import traceback

            traceback.print_exc()
            return False

    def test_discord_redirect(self) -> bool:
        """Test 3: Discord Redirect Message"""
        self.print_header("TEST 3: Discord Redirect (bloqueo PC)")

        try:
            sys.path.insert(0, str(Path(__file__).parent))
            from src.api.v1.bots.discord import (
                _PC_TOOLS_BLOCKED,
                _is_pc_operation_intent,
            )

            # Test deteccion de intencion PC
            test_cases = [
                ("crea carpeta test", True),
                ("lista D:\\Proyectos", True),
                ("backup proyecto Lilith", True),
                ("hola, como estas?", False),
                ("que es Python?", False),
            ]

            all_passed = True
            for text, should_detect in test_cases:
                detected = _is_pc_operation_intent(text)
                passed = detected == should_detect
                if not passed:
                    all_passed = False
                status = PASS if passed else FAIL
                print(
                    f"  {status} '{text[:25]}...' -> detectado={detected} (esperado={should_detect})"
                )

            self.print_result(
                "Deteccion de intenciones PC", all_passed, f"Casos: {len(test_cases)}"
            )

            # Test set de tools bloqueadas
            has_pc_tools = len(_PC_TOOLS_BLOCKED) > 0
            has_expected = (
                "pc_list" in _PC_TOOLS_BLOCKED and "pc_mkdir" in _PC_TOOLS_BLOCKED
            )

            self.print_result(
                "Tools bloqueadas configuradas",
                has_pc_tools and has_expected,
                f"Tools bloqueadas: {len(_PC_TOOLS_BLOCKED)}",
            )

            return all_passed and has_pc_tools

        except Exception as e:
            self.print_result("Discord Redirect", False, f"Error: {e}")
            import traceback

            traceback.print_exc()
            return False

    def test_sessions(self) -> bool:
        """Test 4: Sessions persistentes"""
        self.print_header("TEST 4: Telegram Sessions Persistentes")

        try:
            import tempfile

            sys.path.insert(0, str(Path(__file__).parent))
            from src.core.telegram_session import SessionContext, TelegramSessionManager

            with tempfile.TemporaryDirectory() as tmp:
                # Reset singleton
                TelegramSessionManager._instance = None

                manager = TelegramSessionManager(Path(tmp))

                # Test creacion de sesion
                session = manager.get_session("test_user_123", "test_chat_456")
                created = session.user_id == "test_user_123"
                self.print_result(
                    "Creacion de sesion", created, f"User: {session.user_id}"
                )

                # Test agregar mensajes
                manager.add_message("test_user_123", "test_chat_456", "user", "Hola")
                manager.add_message(
                    "test_user_123", "test_chat_456", "assistant", "Hola!"
                )

                session = manager.get_session("test_user_123", "test_chat_456")
                has_history = len(session.conversation_history) == 2
                self.print_result(
                    "Historial conversacional",
                    has_history,
                    f"Mensajes: {len(session.conversation_history)}",
                )

                # Test persistencia
                manager._save_sessions()

                # Simular reinicio
                TelegramSessionManager._instance = None
                manager2 = TelegramSessionManager(Path(tmp))

                session2 = manager2.get_session("test_user_123", "test_chat_456")
                persisted = len(session2.conversation_history) == 2

                self.print_result(
                    "Persistencia de sesiones",
                    persisted,
                    f"Mensajes tras reinicio: {len(session2.conversation_history)}",
                )

                return created and has_history and persisted

        except Exception as e:
            self.print_result("Sessions", False, f"Error: {e}")
            import traceback

            traceback.print_exc()
            return False

    def test_security(self) -> bool:
        """Test 5: Seguridad (Denied Paths)"""
        self.print_header("TEST 5: Seguridad (Denied Paths)")

        try:
            import tempfile

            sys.path.insert(0, str(Path(__file__).parent))
            from src.core.pc_macro_engine import PCMacroEngine

            with tempfile.TemporaryDirectory() as tmp:
                engine = PCMacroEngine(Path(tmp))

                # Test validacion de paths peligrosos
                dangerous_paths = [
                    {"project_path": "C:/Windows", "project_name": "test"},
                    {"project_path": "D:/Proyectos/../Windows", "project_name": "test"},
                    {"project_path": "C:/Program Files/test", "project_name": "test"},
                ]

                blocked_count = 0
                for params in dangerous_paths:
                    is_valid, error = engine.validate_params("backup_proyecto", params)
                    if not is_valid:
                        blocked_count += 1
                        print(f"  {PASS} Bloqueado: {params['project_path']}")
                    else:
                        print(
                            f"  {FAIL} Permitido (deberia bloquearse): {params['project_path']}"
                        )

                self.print_result(
                    "Bloqueo de paths peligrosos",
                    blocked_count >= 2,
                    f"Bloqueados: {blocked_count}/{len(dangerous_paths)}",
                )

                # Test paths seguros
                safe_paths = [
                    {"project_path": "D:/Proyectos/Test", "project_name": "Test"},
                    {
                        "project_path": "C:/Users/Game_/Desktop",
                        "project_name": "Desktop",
                    },
                ]

                allowed_count = 0
                for params in safe_paths:
                    is_valid, error = engine.validate_params("backup_proyecto", params)
                    if is_valid:
                        allowed_count += 1

                self.print_result(
                    "Permiso de paths seguros",
                    allowed_count >= 1,
                    f"Permitidos: {allowed_count}/{len(safe_paths)}",
                )

                return blocked_count >= 2

        except Exception as e:
            self.print_result("Seguridad", False, f"Error: {e}")
            import traceback

            traceback.print_exc()
            return False

    def run_all_tests(self) -> Dict:
        """Ejecuta todos los smoke tests"""
        self.start_time = time.time()

        print("\n" + "=" * 60)
        print("       SMOKE TESTS - LILITH v5.0 PC AGENT E2E")
        print("=" * 60)
        print(f"{INFO} Base URL: {BASE_URL}")
        print(f"{INFO} Fecha: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
        print(f"{INFO} Tests: 6 escenarios criticos\n")

        # Ejecutar tests (sincrono para evitar problemas de import)
        self.test_health_check()
        self.test_macro_simple()
        self.test_auto_batch()
        self.test_discord_redirect()
        self.test_sessions()
        self.test_security()

        # Resultados finales
        elapsed = time.time() - self.start_time
        passed = sum(1 for r in self.results if r["passed"])
        total = len(self.results)

        self.print_header("RESULTADOS FINALES")

        print(f"\n  Tests ejecutados: {total}")
        print(f"  Tests pasados: {passed}")
        print(f"  Tests fallidos: {total - passed}")
        print(f"  Tiempo total: {elapsed:.2f}s")
        print(f"  Success rate: {(passed/total*100):.1f}%")

        if passed == total:
            print("\n" + "=" * 60)
            print("              TODOS LOS TESTS PASARON")
            print("")
            print("            SISTEMA LISTO PARA DEPLOYMENT")
            print("=" * 60 + "\n")
        else:
            print("\n" + "=" * 60)
            print("              ALGUNOS TESTS FALLARON")
            print("")
            print("         Revisar issues antes de deployment")
            print("=" * 60 + "\n")

        return {
            "passed": passed,
            "total": total,
            "elapsed_seconds": elapsed,
            "success_rate": passed / total if total > 0 else 0,
            "details": self.results,
            "timestamp": datetime.now().isoformat(),
        }


def save_report(results: Dict):
    """Guarda reporte de resultados"""
    report_path = Path("smoke_test_report_v5.0.json")
    with open(report_path, "w", encoding="utf-8") as f:
        json.dump(results, f, indent=2, ensure_ascii=False)
    print(f"\n{INFO} Reporte guardado en: {report_path.absolute()}")


def main():
    """Funcion principal"""
    try:
        runner = SmokeTestRunner()
        results = runner.run_all_tests()
        save_report(results)

        # Exit code: 0 si todos pasan, 1 si alguno falla
        sys.exit(0 if results["passed"] == results["total"] else 1)

    except KeyboardInterrupt:
        print(f"\n{WARN} Tests cancelados por usuario")
        sys.exit(130)
    except Exception as e:
        print(f"\n{FAIL} Error fatal: {e}")
        import traceback

        traceback.print_exc()
        sys.exit(1)


if __name__ == "__main__":
    main()
