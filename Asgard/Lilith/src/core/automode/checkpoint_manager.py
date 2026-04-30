"""
CheckpointManager: Sistema de checkpointing para tareas autónomas.
Guarda y recupera estado de ejecución.
"""
import json
import shutil
from dataclasses import asdict, dataclass
from datetime import datetime
from pathlib import Path
from typing import Any, Dict, List, Optional


@dataclass
class Checkpoint:
    """Representa un checkpoint de ejecución."""

    task_id: str
    step_number: int
    timestamp: str
    plan_state: List[Dict]
    completed_steps: List[Dict]
    context: Dict[str, Any]
    artifacts: List[str]
    metadata: Dict[str, Any]


class CheckpointManager:
    """
    Gestiona checkpoints para tareas en AutoMode.

    Características:
    - Guarda estado cada N pasos
    - Recupera desde último checkpoint
    - Gestiona artifacts generados
    - Mueve tareas entre active/completed/failed
    """

    def __init__(self, task_id: str):
        self.task_id = task_id
        self.muspelheim_root = Path("D:/Proyectos/Yggdrasil/Muspelheim/AutoMode")
        self.task_dir = self.muspelheim_root / "active" / task_id
        self.task_dir.mkdir(parents=True, exist_ok=True)

        self.artifacts_dir = self.task_dir / "artifacts"
        self.artifacts_dir.mkdir(exist_ok=True)

        self._checkpoints_cache: List[Path] = []

    def save_checkpoint(
        self,
        step_number: int,
        plan_state: List[Dict],
        completed_steps: List[Dict],
        context: Dict[str, Any],
        metadata: Optional[Dict] = None,
    ) -> Path:
        """
        Guarda checkpoint del estado actual.

        Args:
            step_number: Número de paso actual
            plan_state: Estado del plan (steps pendientes)
            completed_steps: Steps ya completados
            context: Contexto de ejecución
            metadata: Metadata adicional

        Returns:
            Path al archivo de checkpoint guardado
        """
        checkpoint_id = f"checkpoint_{step_number:03d}"
        checkpoint_path = self.task_dir / f"{checkpoint_id}.json"

        checkpoint = Checkpoint(
            task_id=self.task_id,
            step_number=step_number,
            timestamp=datetime.now().isoformat(),
            plan_state=plan_state,
            completed_steps=completed_steps,
            context=context,
            artifacts=self._list_artifacts(),
            metadata=metadata or {},
        )

        # Guardar como JSON
        checkpoint_data = asdict(checkpoint)
        checkpoint_path.write_text(
            json.dumps(checkpoint_data, indent=2, ensure_ascii=False), encoding="utf-8"
        )

        # Actualizar cache
        if checkpoint_path not in self._checkpoints_cache:
            self._checkpoints_cache.append(checkpoint_path)

        # Log
        print(f"[CheckpointManager] Saved: {checkpoint_id}.json (step {step_number})")

        return checkpoint_path

    def load_latest_checkpoint(self) -> Optional[Checkpoint]:
        """
        Carga el checkpoint más reciente.

        Returns:
            Checkpoint más reciente o None si no hay
        """
        checkpoints = self._get_all_checkpoints()

        if not checkpoints:
            return None

        # Ordenar por número de step
        latest_path = max(checkpoints, key=lambda p: self._extract_step_number(p))

        try:
            data = json.loads(latest_path.read_text(encoding="utf-8"))
            checkpoint = Checkpoint(**data)

            print(
                f"[CheckpointManager] Loaded: {latest_path.name} (step {checkpoint.step_number})"
            )
            return checkpoint

        except Exception as e:
            print(f"[CheckpointManager] Error loading checkpoint: {e}")
            return None

    def load_checkpoint_by_number(self, step_number: int) -> Optional[Checkpoint]:
        """
        Carga checkpoint específico por número de paso.
        """
        checkpoint_path = self.task_dir / f"checkpoint_{step_number:03d}.json"

        if not checkpoint_path.exists():
            return None

        try:
            data = json.loads(checkpoint_path.read_text(encoding="utf-8"))
            return Checkpoint(**data)
        except Exception as e:
            print(f"[CheckpointManager] Error loading checkpoint {step_number}: {e}")
            return None

    def save_artifact(self, filename: str, content: str) -> Path:
        """
        Guarda artifact generado durante ejecución.

        Args:
            filename: Nombre del archivo
            content: Contenido a guardar

        Returns:
            Path al artifact guardado
        """
        # Sanitizar nombre
        safe_filename = Path(filename).name
        artifact_path = self.artifacts_dir / safe_filename

        # Evitar sobreescribir
        counter = 1
        original_path = artifact_path
        while artifact_path.exists():
            stem = original_path.stem
            suffix = original_path.suffix
            artifact_path = self.artifacts_dir / f"{stem}_{counter:03d}{suffix}"
            counter += 1

        artifact_path.write_text(content, encoding="utf-8")

        print(f"[CheckpointManager] Artifact saved: {artifact_path.name}")

        return artifact_path

    def save_artifact_binary(self, filename: str, content: bytes) -> Path:
        """Guarda artifact binario."""
        safe_filename = Path(filename).name
        artifact_path = self.artifacts_dir / safe_filename

        counter = 1
        original_path = artifact_path
        while artifact_path.exists():
            stem = original_path.stem
            suffix = original_path.suffix
            artifact_path = self.artifacts_dir / f"{stem}_{counter:03d}{suffix}"
            counter += 1

        artifact_path.write_bytes(content)

        print(f"[CheckpointManager] Artifact saved (binary): {artifact_path.name}")

        return artifact_path

    def get_artifact(self, filename: str) -> Optional[Path]:
        """
        Obtiene path a artifact.
        """
        artifact_path = self.artifacts_dir / filename
        if artifact_path.exists():
            return artifact_path
        return None

    def list_all_checkpoints(self) -> List[Dict]:
        """
        Lista todos los checkpoints con metadata.
        """
        checkpoints = []

        for path in self._get_all_checkpoints():
            try:
                data = json.loads(path.read_text(encoding="utf-8"))
                checkpoints.append(
                    {
                        "step_number": data.get("step_number"),
                        "timestamp": data.get("timestamp"),
                        "filename": path.name,
                        "completed_count": len(data.get("completed_steps", [])),
                    }
                )
            except Exception:
                continue

        return sorted(checkpoints, key=lambda x: x["step_number"])

    def move_to_completed(self, final_report: Optional[str] = None) -> Path:
        """
        Mueve tarea a carpeta de completadas.

        Args:
            final_report: Reporte final opcional

        Returns:
            Path al directorio destino
        """
        # Guardar reporte final si existe
        if final_report:
            report_path = self.task_dir / "final_report.md"
            report_path.write_text(final_report, encoding="utf-8")

        # Mover directorio
        dest_dir = self.muspelheim_root / "completed" / self.task_id

        if dest_dir.exists():
            shutil.rmtree(dest_dir)

        shutil.move(str(self.task_dir), str(dest_dir))

        print(f"[CheckpointManager] Task moved to completed: {self.task_id}")

        return dest_dir

    def move_to_failed(self, error_report: str) -> Path:
        """
        Mueve tarea a carpeta de fallidas.

        Args:
            error_report: Reporte de error

        Returns:
            Path al directorio destino
        """
        # Guardar reporte de error
        error_path = self.task_dir / "error_report.md"
        error_path.write_text(error_report, encoding="utf-8")

        # Mover directorio
        dest_dir = self.muspelheim_root / "failed" / self.task_id

        if dest_dir.exists():
            shutil.rmtree(dest_dir)

        shutil.move(str(self.task_dir), str(dest_dir))

        print(f"[CheckpointManager] Task moved to failed: {self.task_id}")

        return dest_dir

    def _get_all_checkpoints(self) -> List[Path]:
        """Obtiene lista de todos los archivos de checkpoint."""
        if not self.task_dir.exists():
            return []

        return sorted(self.task_dir.glob("checkpoint_*.json"))

    def _list_artifacts(self) -> List[str]:
        """Lista nombres de artifacts."""
        if not self.artifacts_dir.exists():
            return []

        return [f.name for f in self.artifacts_dir.iterdir() if f.is_file()]

    def _extract_step_number(self, checkpoint_path: Path) -> int:
        """Extrae número de paso del nombre de archivo."""
        try:
            # checkpoint_001.json -> 1
            stem = checkpoint_path.stem  # checkpoint_001
            parts = stem.split("_")
            if len(parts) >= 2:
                return int(parts[-1])
        except (ValueError, IndexError):
            pass
        return 0

    def get_task_summary(self) -> Dict:
        """
        Obtiene resumen de la tarea.
        """
        checkpoints = self.list_all_checkpoints()
        latest = self.load_latest_checkpoint()

        return {
            "task_id": self.task_id,
            "checkpoints_count": len(checkpoints),
            "latest_step": latest.step_number if latest else 0,
            "artifacts_count": len(self._list_artifacts()),
            "status": "active"
            if (self.muspelheim_root / "active" / self.task_id).exists()
            else "unknown",
        }
