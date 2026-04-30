"""
Smoke test: modo por canal y pendientes de sesión.
- Fija modo 'arquitecto' en un canal de prueba y comprueba que [Modo_Activo] llega al bloque.
- Añade un pendiente y comprueba que [Pendientes_de_sesion] lo incluye.
Ejecutar desde Core: python -m Backend.api.smoke_discord_blocks
"""
import sys
from pathlib import Path

# Asegurar path
ROOT = Path(__file__).resolve().parent.parent.parent
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))


def main():
    from src.core.attention_stack import add, get_pending, get_pending_block
    from src.core.mode_store import get_mode, get_mode_overlay, set_mode

    channel_id = "smoke_test_channel_999"
    thread_id = None

    # 1) Modo arquitecto
    ok = set_mode(ROOT, channel_id, thread_id, "arquitecto")
    assert ok, "set_mode(arquitecto) falló"
    mode_overlay = get_mode_overlay(ROOT, channel_id, thread_id)
    assert (
        "[Modo_Activo]" in mode_overlay
    ), f"[Modo_Activo] no está en el bloque: {mode_overlay[:200]}"
    assert (
        "arquitecto" in mode_overlay.lower() or "ARQUITECTO" in mode_overlay
    ), f"arquitecto no aparece: {mode_overlay[:200]}"
    print("[OK] Modo arquitecto: bloque [Modo_Activo] generado correctamente.")

    # 2) Pendiente
    item_id = add(ROOT, channel_id, thread_id, "Revisar PR de seguridad")
    assert item_id, "add(pendiente) falló"
    block = get_pending_block(ROOT, channel_id, thread_id)
    assert (
        "[Pendientes_de_sesion]" in block
    ), f"[Pendientes_de_sesion] no está: {block[:200]}"
    assert "Revisar PR" in block, f"Texto del pendiente no está: {block[:200]}"
    print(
        "[OK] Pendiente añadido: bloque [Pendientes_de_sesion] generado correctamente."
    )

    print("Smoke test pasó: modo y pendientes listos para inyección en prompt.")


if __name__ == "__main__":
    main()
