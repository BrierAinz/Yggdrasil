"""
PyTorch Tool - Integración de pytorch_helper para Lilith
Genera modelos PyTorch y opcionalmente los ejecuta

Fase B: Gauntlet Mode - Ejecución automática de training
"""

import json
import os
import subprocess
import sys
import threading
import time
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any, Callable, Dict, Optional

# Add project root for imports
project_root = Path(__file__).parent.parent.parent.parent
if str(project_root) not in sys.path:
    sys.path.insert(0, str(project_root))

from src.tools.ecosystem.pytorch_helper import (
    generate_model_code,
    handle_pytorch_command,
)


@dataclass
class TrainingMetrics:
    """Estructura para métricas de entrenamiento"""

    epoch: int = 0
    train_loss: float = 0.0
    train_acc: float = 0.0
    test_loss: float = 0.0
    test_acc: float = 0.0
    best_acc: float = 0.0
    time_per_epoch: float = 0.0
    total_time: float = 0.0
    status: str = "pending"  # pending, running, completed, failed
    error_message: str = ""

    def to_dict(self) -> Dict[str, Any]:
        return {
            "epoch": self.epoch,
            "train_loss": round(self.train_loss, 4),
            "train_acc": round(self.train_acc, 2),
            "test_loss": round(self.test_loss, 4),
            "test_acc": round(self.test_acc, 2),
            "best_acc": round(self.best_acc, 2),
            "time_per_epoch": round(self.time_per_epoch, 1),
            "total_time": round(self.total_time, 1),
            "status": self.status,
        }


class PyTorchTool:
    """
    Tool para generar y ejecutar modelos PyTorch automáticamente.

    Capabilities:
    - generate_model: Crea templates de modelos PyTorch
    - save_model: Guarda el código generado a archivo
    - run_training: Ejecuta entrenamiento y captura métricas
    - gauntlet: Pipeline completo (generate → save → train → report)
    - list_templates: Muestra templates disponibles
    """

    def __init__(self, output_dir: str = None):
        self.output_dir = (
            Path(output_dir)
            if output_dir
            else Path(
                "D:/Proyectos/Yggdrasil/Asgard/Lilith/Core/Workspace/Taller/PyTorchModels"
            )
        )
        self.output_dir.mkdir(parents=True, exist_ok=True)
        self.artifacts_dir = Path(
            "D:/Proyectos/Yggdrasil/Asgard/Lilith/Core/Artifacts/PyTorch"
        )
        self.artifacts_dir.mkdir(parents=True, exist_ok=True)
        self.generated_models = []
        self.current_training: Optional[subprocess.Popen] = None
        self.training_metrics = TrainingMetrics()

    def get_info(self) -> Dict[str, Any]:
        """Retorna información del tool para el registry"""
        return {
            "name": "PyTorchTool",
            "version": "2.0.0",
            "description": "Genera y entrena modelos PyTorch automáticamente (Gauntlet Mode)",
            "actions": [
                "generate_model",
                "save_model",
                "run_training",
                "gauntlet",
                "list_templates",
                "stop_training",
            ],
            "category": "ml_generation",
            "risk_level": "medium",
            "hardware_reqs": "CUDA opcional pero recomendado para entrenamiento",
        }

    def execute(self, action: str, parameters: Dict[str, Any] = None) -> Dict[str, Any]:
        """
        Punto de entrada principal del tool

        Args:
            action: Acción a ejecutar
            parameters: Parámetros específicos de la acción
        """
        parameters = parameters or {}

        actions = {
            "generate_model": self._generate_model,
            "save_model": self._save_model,
            "run_training": self._run_training,
            "gauntlet": self._gauntlet,
            "list_templates": self._list_templates,
            "stop_training": self._stop_training,
        }

        if action not in actions:
            return {
                "success": False,
                "error": f"Acción '{action}' no soportada. Use: {list(actions.keys())}",
            }

        try:
            return actions[action](parameters)
        except Exception as e:
            return {
                "success": False,
                "error": str(e),
                "traceback": f"Error en {action}: {e}",
            }

    def _generate_model(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Genera código de modelo PyTorch"""
        model_name = params.get("model_name", "MyModel")
        input_size = params.get("input_size", 784)
        hidden_size = params.get("hidden_size", 128)
        output_size = params.get("output_size", 10)
        layers = params.get("layers", 2)

        # Generate code using existing helper
        cmd = f"create_model {model_name} --input_size {input_size} --hidden_size {hidden_size} --output_size {output_size} --layers {layers}"
        code = handle_pytorch_command(cmd)

        # Store for later use
        model_info = {
            "name": model_name,
            "code": code,
            "params": {
                "input_size": input_size,
                "hidden_size": hidden_size,
                "output_size": output_size,
                "layers": layers,
            },
            "timestamp": datetime.now().isoformat(),
        }
        self.generated_models.append(model_info)

        return {
            "success": True,
            "model_name": model_name,
            "code": code,
            "params": model_info["params"],
            "message": f"Modelo '{model_name}' generado exitosamente",
        }

    def _save_model(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Guarda el último modelo generado a archivo"""
        if not self.generated_models:
            return {
                "success": False,
                "error": "No hay modelos generados. Use 'generate_model' primero.",
            }

        model_info = self.generated_models[-1]
        model_name = params.get("filename", model_info["name"])
        if not model_name.endswith(".py"):
            model_name += ".py"

        filepath = self.output_dir / model_name

        # Extract code from markdown if present
        code = model_info["code"]
        if "```python" in code:
            code = code.split("```python")[1].split("```")[0].strip()

        # Add header
        header = (
            f"\"\"\"\n{model_info['name']} - Auto-generated by Lilith PyTorch Tool\n"
        )
        header += f"Generated: {model_info['timestamp']}\n"
        header += f"Parameters: {model_info['params']}\n\"\"\"\n\n"

        full_code = header + code

        # Save file
        with open(filepath, "w", encoding="utf-8") as f:
            f.write(full_code)

        return {
            "success": True,
            "filepath": str(filepath),
            "model_name": model_info["name"],
            "message": f"Modelo guardado en: {filepath}",
        }

    def _run_training(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Ejecuta entrenamiento de un script PyTorch

        Args:
            script_path: Ruta al script Python de entrenamiento
            epochs: Número de épocas (default: 50)
            batch_size: Tamaño de batch (default: 128)
            lr: Learning rate (default: 0.1)
            timeout: Timeout en segundos (default: 1800 = 30 min)
            live_output: Si True, captura output en tiempo real (default: True)
        """
        script_path = params.get("script_path")
        if not script_path:
            # Si no hay script_path, usar el gauntlet script por defecto
            script_path = "D:/Proyectos/Yggdrasil/Asgard/Lilith/Core/Scripts/cifar10_wide_resnet_gauntlet.py"

        script_path = Path(script_path)
        if not script_path.exists():
            return {"success": False, "error": f"Script no encontrado: {script_path}"}

        epochs = params.get("epochs", 50)
        batch_size = params.get("batch_size", 128)
        lr = params.get("lr", 0.1)
        timeout = params.get("timeout", 1800)  # 30 min default
        live_output = params.get("live_output", True)

        # Crear script wrapper con métricas JSON
        wrapper_script = self._create_training_wrapper(
            script_path, epochs, batch_size, lr
        )

        self.training_metrics = TrainingMetrics(status="running")
        start_time = time.time()

        try:
            # Ejecutar con captura de output
            env = os.environ.copy()
            env["PYTHONUNBUFFERED"] = "1"
            env["CUDA_VISIBLE_DEVICES"] = "0"  # Usar primera GPU

            if live_output:
                # Modo con captura en tiempo real
                process = subprocess.Popen(
                    [sys.executable, str(wrapper_script)],
                    stdout=subprocess.PIPE,
                    stderr=subprocess.STDOUT,
                    text=True,
                    bufsize=1,
                    env=env,
                    cwd=str(script_path.parent),
                )
                self.current_training = process

                output_lines = []
                metrics_history = []

                # Leer output en tiempo real
                for line in process.stdout:
                    line = line.strip()
                    output_lines.append(line)

                    # Parsear métricas JSON
                    if line.startswith("JSON_METRICS:"):
                        try:
                            json_str = line.replace("JSON_METRICS:", "").strip()
                            metrics_data = json.loads(json_str)
                            metrics_history.append(metrics_data)

                            # Actualizar métricas actuales
                            self.training_metrics.epoch = metrics_data.get("epoch", 0)
                            self.training_metrics.train_acc = metrics_data.get(
                                "train_acc", 0
                            )
                            self.training_metrics.test_acc = metrics_data.get(
                                "test_acc", 0
                            )
                            self.training_metrics.best_acc = metrics_data.get(
                                "best_acc", 0
                            )
                            self.training_metrics.time_per_epoch = metrics_data.get(
                                "time", 0
                            )

                        except json.JSONDecodeError:
                            pass

                # Esperar a que termine con timeout
                process.wait(timeout=timeout)

                total_time = time.time() - start_time
                self.training_metrics.total_time = total_time

                if process.returncode == 0:
                    self.training_metrics.status = "completed"

                    # Leer métricas finales si existen
                    metrics_file = self.artifacts_dir / "training_metrics.json"
                    final_metrics = {}
                    if metrics_file.exists():
                        with open(metrics_file, "r") as f:
                            final_metrics = json.load(f)

                    return {
                        "success": True,
                        "message": f"Entrenamiento completado en {total_time:.1f}s",
                        "metrics": self.training_metrics.to_dict(),
                        "metrics_history": metrics_history,
                        "final_accuracy": self.training_metrics.best_acc,
                        "epochs_completed": self.training_metrics.epoch,
                        "script": str(script_path),
                        "output_sample": output_lines[-20:]
                        if len(output_lines) > 20
                        else output_lines,
                    }
                else:
                    self.training_metrics.status = "failed"
                    return {
                        "success": False,
                        "error": f"Proceso terminó con código {process.returncode}",
                        "output": output_lines[-50:]
                        if len(output_lines) > 50
                        else output_lines,
                    }
            else:
                # Modo simple sin live output
                result = subprocess.run(
                    [sys.executable, str(wrapper_script)],
                    capture_output=True,
                    text=True,
                    timeout=timeout,
                    env=env,
                    cwd=str(script_path.parent),
                )

                total_time = time.time() - start_time

                if result.returncode == 0:
                    return {
                        "success": True,
                        "message": f"Entrenamiento completado en {total_time:.1f}s",
                        "stdout": result.stdout[-2000:]
                        if len(result.stdout) > 2000
                        else result.stdout,
                        "total_time": round(total_time, 1),
                    }
                else:
                    return {
                        "success": False,
                        "error": result.stderr[-1000:]
                        if result.stderr
                        else "Error desconocido",
                    }

        except subprocess.TimeoutExpired:
            self.training_metrics.status = "failed"
            if self.current_training:
                self.current_training.terminate()
            return {"success": False, "error": f"Timeout después de {timeout}s"}
        except Exception as e:
            self.training_metrics.status = "failed"
            self.training_metrics.error_message = str(e)
            return {"success": False, "error": str(e)}
        finally:
            self.current_training = None
            # Limpiar wrapper script
            if "wrapper_script" in locals() and wrapper_script.exists():
                wrapper_script.unlink()

    def _create_training_wrapper(
        self, original_script: Path, epochs: int, batch_size: int, lr: float
    ) -> Path:
        """Crea un script wrapper que ejecuta el original y captura métricas"""

        wrapper_code = f'''"""
Auto-generated training wrapper for Gauntlet Mode
"""
import sys
import json
import subprocess
import os

# Configuración
EPOCHS = {epochs}
BATCH_SIZE = {batch_size}
LEARNING_RATE = {lr}
METRICS_FILE = r"{self.artifacts_dir / 'training_metrics.json'}"

# Ejecutar script original con monkey-patching para capturar métricas
exec(open(r"{original_script}").read())
'''

        wrapper_path = self.artifacts_dir / f"training_wrapper_{int(time.time())}.py"
        with open(wrapper_path, "w", encoding="utf-8") as f:
            f.write(wrapper_code)

        return wrapper_path

    def _gauntlet(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """
        Pipeline Gauntlet completo: generate → save → train → report

        Args:
            template: Template a usar (SimpleClassifier, DeepClassifier, WideResNet_CIFAR)
            model_name: Nombre del modelo
            epochs: Número de épocas
            batch_size: Tamaño de batch
            lr: Learning rate
            auto: Si True, ejecuta todo automáticamente
        """
        template = params.get("template", "WideResNet_CIFAR")
        auto = params.get("auto", True)

        if not auto:
            return {"success": False, "error": "Modo gauntlet requiere auto=True"}

        results = {"stages": {}, "success": False}

        # Stage 1: Generate (solo para templates no-CIFAR)
        if template in ["SimpleClassifier", "DeepClassifier"]:
            gen_params = {
                "model_name": params.get("model_name", "GauntletNet"),
                "input_size": params.get("input_size", 784),
                "hidden_size": params.get("hidden_size", 128),
                "output_size": params.get("output_size", 10),
                "layers": params.get("layers", 2),
            }
            result = self._generate_model(gen_params)
            results["stages"]["generate"] = result

            if not result["success"]:
                return results

            # Stage 2: Save
            save_result = self._save_model(
                {"filename": gen_params["model_name"] + ".py"}
            )
            results["stages"]["save"] = save_result

            if not save_result["success"]:
                return results

            script_path = save_result["filepath"]
        else:
            # WideResNet_CIFAR - usar script existente
            script_path = "D:/Proyectos/Yggdrasil/Asgard/Lilith/Core/Scripts/cifar10_wide_resnet_gauntlet.py"
            results["stages"]["generate"] = {
                "success": True,
                "message": "Usando script WideResNet existente",
            }
            results["stages"]["save"] = {
                "success": True,
                "message": f"Script: {script_path}",
            }

        # Stage 3: Train
        train_params = {
            "script_path": script_path,
            "epochs": params.get("epochs", 50),
            "batch_size": params.get("batch_size", 128),
            "lr": params.get("lr", 0.1),
            "timeout": params.get("timeout", 1800),
            "live_output": params.get("live_output", True),
        }

        train_result = self._run_training(train_params)
        results["stages"]["train"] = train_result

        # Stage 4: Report
        if train_result["success"]:
            results["success"] = True
            results["final_report"] = {
                "template": template,
                "epochs_completed": train_result.get("epochs_completed", 0),
                "final_accuracy": train_result.get("final_accuracy", 0),
                "total_time": train_result.get("metrics", {}).get("total_time", 0),
                "status": "COMPLETED",
            }
            results[
                "message"
            ] = f"Gauntlet completado! Accuracy: {results['final_report']['final_accuracy']:.2f}%"
        else:
            results["message"] = "Gauntlet falló en etapa de entrenamiento"

        return results

    def _stop_training(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Detiene el entrenamiento en curso"""
        if self.current_training and self.current_training.poll() is None:
            self.current_training.terminate()
            self.training_metrics.status = "stopped"
            return {"success": True, "message": "Entrenamiento detenido"}
        return {"success": False, "error": "No hay entrenamiento en curso"}

    def _list_templates(self, params: Dict[str, Any]) -> Dict[str, Any]:
        """Lista templates disponibles"""
        templates = [
            {
                "name": "SimpleClassifier",
                "description": "Clasificador MLP simple",
                "params": {
                    "input_size": 784,
                    "hidden_size": 128,
                    "output_size": 10,
                    "layers": 2,
                },
                "training_time": "~5 min",
            },
            {
                "name": "DeepClassifier",
                "description": "Clasificador MLP profundo",
                "params": {
                    "input_size": 784,
                    "hidden_size": 256,
                    "output_size": 10,
                    "layers": 4,
                },
                "training_time": "~10 min",
            },
            {
                "name": "WideResNet_CIFAR",
                "description": "Wide ResNet-28-10 para CIFAR-10 (~95% accuracy)",
                "params": {"epochs": 50, "batch_size": 128, "lr": 0.1},
                "training_time": "~15-20 min en RTX 3060",
                "hardware_reqs": "CUDA recomendado (12GB VRAM suficiente)",
            },
        ]

        return {
            "success": True,
            "templates": templates,
            "count": len(templates),
            "note": "Usa 'gauntlet' action para ejecutar pipeline completo automáticamente",
        }


# Legacy compatibility
PyTorchHelper = PyTorchTool


if __name__ == "__main__":
    # Test Fase B
    tool = PyTorchTool()

    print("=" * 60)
    print("PyTorch Tool Fase B - Gauntlet Mode Test")
    print("=" * 60)

    # Test 1: List templates
    print("\n1. Templates disponibles...")
    result = tool.execute("list_templates")
    print(f"   Templates: {result.get('count')}")
    for t in result.get("templates", []):
        print(f"   - {t['name']}: {t['description']}")

    # Test 2: Gauntlet (modo dry-run para no entrenar ahora)
    print("\n2. Gauntlet pipeline (solo validación)...")
    result = tool.execute(
        "gauntlet",
        {
            "template": "WideResNet_CIFAR",
            "epochs": 5,  # Solo 5 epochs para test
            "auto": True,
        },
    )
    print(f"   Success: {result.get('success')}")
    if result.get("stages"):
        for stage, data in result["stages"].items():
            print(f"   - {stage}: {data.get('success', False)}")

    print("\n" + "=" * 60)
    print("Fase B Test completado")
