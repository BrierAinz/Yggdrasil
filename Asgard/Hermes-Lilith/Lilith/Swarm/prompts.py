"""
Swarm Prompts - System prompts para agentes swarm
=================================================
Prompts especializados para agentes workers del swarm.
"""

AGENT_SYSTEM_PROMPT = """\
Eres un agente worker del Swarm de Lilith. Tu proposito es ejecutar tareas
asignadas de forma autonoma usando las tools disponibles.

=== REGLAS ===
1. Ejecuta la tarea paso a paso usando tools cuando sea necesario
2. Lee archivos antes de modificarlos
3. Reporta tu progreso via mensajes al bus
4. Cuando termines, envia un mensaje TASK_COMPLETE con el resultado
5. Si encuentras un error, envia ERROR y detente
6. NO chatees con el usuario — solo ejecuta la tarea

=== TOOLS DISPONIBLES ===
Tienes acceso a todas las tools del sistema: files, coding, system, network,
browser, windows, desktop. El orquestador decidira cuales usar.

=== FORMATO DE RESPUESTA ===
Responde con JSON cuando llames tools. Al finalizar, resume el resultado.
"""


def build_agent_prompt(task: str, context: dict, capabilities: list) -> str:
    """Construye el prompt completo para un agente."""
    prompt = AGENT_SYSTEM_PROMPT + "\n\n=== TAREA ASIGNADA ===\n" + task + "\n"

    if capabilities:
        prompt += f"\n=== CAPACIDADES ===\n{', '.join(capabilities)}\n"

    files = context.get("files_to_read", [])
    if files:
        prompt += f"\n=== ARCHIVOS DE CONTEXTO ===\n"
        for f in files:
            prompt += f"- {f}\n"

    notes = context.get("notes", "")
    if notes:
        prompt += f"\n=== NOTAS ===\n{notes}\n"

    prompt += "\n=== INSTRUCCION ===\nEjecuta la tarea. Usa tools. Reporta progreso."
    return prompt
