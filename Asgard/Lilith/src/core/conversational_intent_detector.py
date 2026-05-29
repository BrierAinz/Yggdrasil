"""
Lilith - Conversational Intent Detector
Convierte lenguaje natural a intenciÃ³n estructurada
"""

import json
import re
from pathlib import Path
from typing import Any, Dict, List, Optional


class DetectedIntent:
    """Represents a detected intent from natural language"""

    def __init__(self):
        self.intent_type: str = (
            "unknown"  # code_review, research, generate, system, etc.
        )
        self.target: Optional[str] = None  # file, URL, concept, etc.
        self.tool_suggestions: List[str] = []
        self.confidence: float = 0.0
        self.clarification_needed: bool = False
        self.extracted_constraints: List[str] = []
        self.natural_language: str = ""
        self.context_references: List[str] = []  # "este", "ese", etc.

    def to_dict(self) -> Dict[str, Any]:
        return {
            "intent_type": self.intent_type,
            "target": self.target,
            "tool_suggestions": self.tool_suggestions,
            "confidence": self.confidence,
            "clarification_needed": self.clarification_needed,
            "extracted_constraints": self.extracted_constraints,
            "natural_language": self.natural_language,
            "context_references": self.context_references,
        }


class ConversationalIntentDetector:
    """
    Convierte lenguaje natural a intenciÃ³n estructurada

    Input: "Oye, revisa este cÃ³digo"
    Output: {"intent": "code_review", "target": "current_context", "tools": ["CodeAnalyzer"], "confidence": 0.92}
    """

    def __init__(self):
        """Initialize with patterns and heuristics"""
        self.min_confidence_threshold = 0.6
        self.clarification_threshold = 0.75

        # Pattern-based detection (fast, no LLM needed for simple cases)
        self.intent_patterns = {
            "identity_query": [
                r"qui[eÃ©]n\s+(e|)res\s+t[uÃº]?\b",
                r"qui[eÃ©]n\s+eres\b",
                r"(presentate|identificate|quien eres|soy yo)\b",
                r"eres\s+(una|un)\s+(ia|inteligencia|asistente|bot|ai)\b",
                r"(what|who)\s+(are|is)\s+(you|this)\b",
            ],
            "farewell": [
                r"^(adi[oÃ³]s|bye|chao|ciao|nos vemos)\b",
                r"(hasta luego|hasta pronto|hasta maÃ±ana|hasta la proxima)\b",
                r"(see you|goodbye|farewell)\b",
                r"\b(bye bye|bye!|adi[oÃ³]s!)\b",
            ],
            "greeting": [
                r"^(buenos d[iÃ­]as|buenas tardes|buenas noches)\b",
                r"^(hola|hey|oye|buenas|hi|hello|al[oÃ³]h)\b",
                r"(c[oÃ³]mo\s+est[aÃ¡]s|how are you|que tal)\b",
                r"(good morning|good afternoon|good evening)\b",
            ],
            "general_conversation": [
                r"(gracias|thanks|thank you|muchas gracias)\b",
                r"(por favor|please)\b",
                r"(genial|excelente|muy bien|awesome|great)\b",
                r"(vale|ok|de acuerdo|sure|alright)\b",
                r"(cu[eÃ©]ntame|habla|dime algo)\b",
            ],
            "code_review": [
                r"revis(a|e|c|ar)\s+(el\s+)?c(o|Ã³)di(go?g?o?)",
                r"analiz(a|e|c|ar)\s+(el\s+)?c(o|Ã³)di(go?g?o?)",
                r"review\s+(the\s+)?cod(e|ing)",
                r"check\s+(the\s+)?cod(e|ing)",
                r"analyze\s+(the\s+)?cod(e|ing)",
            ],
            "code_security": [
                r"segu(?:ri)?dad\s+en\s+(el\s+)?c(o|Ã³)di(go?g?o?)",
                r"vulnerabilidades?\s+en\s+(el\s+)?c(o|Ã³)di(go?g?o?)",
                r"security\s+(in\s+the\s+)?cod(e|ing)",
            ],
            "research": [
                r"^investiga\s+(sobre|acerca\s+de)\s+(.+)$",
                r"^research\s+(.+)$",
                r"busca\s+datos\s+sobre\s+(.+)",
            ],
            "web_visit": [
                r"visita\s+(la\s+)?p(a|Ã¡)gina\s+(.+)",
                r"abre\s+(la\s+)?p(a|Ã¡)gina\s+(.+)",
                r"ve\s+a\s+(.+)",
                r"visit\s+(the\s+)?pag(e|ina)\s+(.+)",
            ],
            "generate": [
                r"cre(a|e|u|ar)\s+(una|un)\s+imagen\s+(.+)",
                r"gener(a|ar)\s+una\s+imagen\s+(.+)",
                r"make\s+an\s+image\s+(.+)",
                r"create\s+an?\s+image\s+(.+)",
            ],
            "system_execute": [
                r"ejecuta\s+(.+)",
                r"run\s+(.+)",
                r"execute\s+(.+)",
                r"launch\s+(.+)",
            ],
            "memory_query": [
                r"recuerdas\s+(.+)",
                r"qu[eÃ©]\s+sabes\s+sobre\s+(.+)",
                r"busca\s+en\s+memoria\s+(.+)",
            ],
            "code_edit": [
                r"edita\s+(el\s+archivo\s+)?(.+)",
                r"cambia\s+(.+)\s+por\s+(.+)\s+en\s+(.+)",
                r"sustituye\s+(.+)\s+con\s+(.+)\s+en\s+(.+)",
                r"edit\s+(the\s+file\s+)?(.+)",
                r"change\s+(.+)\s+to\s+(.+)\s+in\s+(.+)",
            ],
            "code_search": [
                r"busca\s+(el\s+)?texto\s+(.+)\s+en\s+(.+)",
                r"d[oÃ³]nde\s+se\s+usa\s+(.+)",
                r"grep\s+(.+)",
                r"find\s+in\s+files\s+(.+)",
            ],
            # NUEVOS: Skills autÃ³nomas de gestiÃ³n de archivos y proyectos
            "file_read": [
                r"lee\s+(el\s+)?(archivo|fichero)\s+(.+)",
                r"mu[eÃ©]strame\s+(el\s+)?(contenido\s+de\s+)?(.+?\.(py|js|ts|json|md|txt|yaml|yml|xml|ini|cfg|toml))",
                r"abre\s+(el\s+)?archivo\s+(.+)",
                r"cat\s+(.+)",
                r"qu[eÃ©]\s+(hay|contiene)\s+en\s+(.+)",
                r"read\s+(the\s+)?file\s+(.+)",
                r"show\s+me\s+(the\s+)?content\s+of\s+(.+)",
                r"open\s+(the\s+)?file\s+(.+)",
            ],
            "file_write": [
                r"(crea|escribe|guarda)\s+(un\s+)?(archivo|fichero)\s+(llamado\s+)?(.+?\.(py|js|ts|json|md|txt))",
                r"crea\s+(un\s+archivo\s+con\s+)?(.+)",
                r"write\s+(a\s+)?file\s+(called\s+)?(.+)",
                r"create\s+(a\s+)?file\s+(named\s+)?(.+)",
                r"guarda\s+esto\s+en\s+(.+)",
                r"save\s+this\s+to\s+(.+)",
            ],
            "file_list": [
                # MÃ¡s especÃ­ficos - requieren palabras clave de directorio/listado
                r"lista\s+(los\s+)?(archivos|ficheros)\s+(en\s+|de\s+)?(.+)",
                r"mu[eÃ©]strame\s+(los\s+)?(archivos|ficheros|directorios)\s+(que\s+hay\s+)?(en\s+|de\s+)?(.+)",
                r"qu[eÃ©]\s+(archivos|ficheros)\s+hay\s+(en\s+|dentro\s+de\s+)?(.+)",
                r"qu[eÃ©]\s+hay\s+(en\s+|dentro\s+de\s+)?(.+?)(\s|$)",
                r"list\s+(the\s+)?files\s+(in\s+|inside\s+)?(.+)",
                r"show\s+me\s+(the\s+)?files?\s+(in\s+|inside\s+)?(.+)",
                r"ls\s+(.+)",
                r"dir\s+(.+)",
                r"directorio\s+(.+)",
                r"carpeta\s+(.+)",
                r"folder\s+(.+)",
                r"directory\s+(.+)",
            ],
            "file_search": [
                r"busca\s+(archivos?|ficheros?)\s+(llamados?|con\s+nombre|que\s+se\s+llamen)\s+(.+)",
                r"encuentra\s+(todos\s+los\s+)?archivos?\s+(que\s+contengan|con)\s+(.+)",
                r"search\s+for\s+files?\s+(named|called)\s+(.+)",
                r"find\s+files?\s+(containing|with)\s+(.+)",
                r"d[oÃ³]nde\s+(est[aÃ¡]|se\s+encuentra)\s+(.+\.(py|js|ts|json|md|txt))",
                r"where\s+is\s+(the\s+)?file\s+(.+)",
            ],
            "project_scan": [
                # Escaneo/anÃ¡lisis de proyecto completo (no archivos individuales)
                r"analiza\s+(este\s+|el\s+)?(proyecto|projecto|repo|repositorio|c[oÃ³]digo)\b",
                r"analiza\s+(el\s+)?c[oÃ³]digo\s+(del\s+proyecto|de\s+este\s+proyecto|base)\b",
                r"escanea\s+(este\s+|el\s+)?(proyecto|projecto|c[oÃ³]digo|repo|repositorio)\b",
                r"qu[eÃ©]\s+(tipo\s+de\s+)?proyecto\s+es\s+(este\s+)?",
                r"dime\s+(sobre\s+)?(la\s+)?estructura\s+(de\s+este\s+|del\s+)?(proyecto|repo|c[oÃ³]digo)",
                r"entien(d|de)\s+(este\s+|el\s+)?(proyecto|c[oÃ³]digo|repo)",
                r"entiende\s+(este\s+|el\s+)?(proyecto|c[oÃ³]digo|repo)",
                r"comprende\s+(este\s+|el\s+)?(proyecto|c[oÃ³]digo|repo)",
                r"scan\s+(this\s+|the\s+)?(project|codebase|repo|repository|code)\b",
                r"analyze\s+(this\s+|the\s+)?(project|codebase|repo|repository|code)\b",
                r"analyze\s+(the\s+)?code\s+(base|of\s+this\s+project)\b",
                r"what\s+(kind\s+of\s+)?project\s+is\s+(this\s+)?",
                r"tell\s+me\s+about\s+(the\s+)?structure\s+(of\s+this\s+project)?",
                r"detecta\s+(el\s+)?tipo\s+de\s+proyecto",
                r"detect\s+(the\s+)?project\s+type",
            ],
            "task_plan": [
                # PlanificaciÃ³n de tareas - evitar conflicto con file_write
                r"crea\s+(un\s+)?plan\s+(de\s+)?(trabajo|tareas|accion|implementacion)\b",
                r"crea\s+(un\s+)?plan\s+(para\s+)?(hacer|implementar|refactorizar|mejorar|desarrollar)\b",
                r"planifica\s+(la\s+|el\s+)?(.+?)(\s|$)",
                r"organiza\s+(esto|lo|todo)?\s*en\s+(pasos|tareas|etapas)",
                r"organize\s+into\s+(steps|tasks|phases)",
                r"organize\s+(this|it)\s+into\s+(steps|tasks|phases)",
                r"divid(e|ir)\s+(esto|en)\s+(tareas|pasos|etapas|fases)",
                r"divide\s+(en\s+)?(tareas|pasos|etapas)",
                r"pasos\s+(para\s+)?(hacer|implementar)",
                r"create\s+(a\s+)?(work\s+)?plan\s+(for\s+)?(.+)",
                r"plan\s+(the\s+)?(implementation|refactoring|development)\b",
                r"break\s+(this|it|down)?\s+into\s+(tasks|steps|phases)",
                r"necesito\s+(un\s+)?plan\s+(para\s+)?(hacer|implementar)",
                r"quiero\s+organizar\s+(las\s+)?tareas",
                r"need\s+a\s+plan\s+(for\s+)?(.+)",
                r"steps\s+to\s+(do|implement|make)",
            ],
            # NUEVO: CodeRefactor patterns
            "refactor_code": [
                r"refactoriza\s+(el\s+)?c[oÃ³]digo",
                r"refactoriza\s+(la\s+)?funci[oÃ³]n\s+(.+)",
                r"refactor\s+(the\s+)?code",
                r"refactor\s+(the\s+)?function\s+(.+)",
                r"renombra\s+(la\s+)?funci[oÃ³]n\s+(.+)\s+a\s+(.+)",
                r"renombra\s+(la\s+)?variable\s+(.+)\s+a\s+(.+)",
                r"rename\s+(the\s+)?function\s+(.+)\s+to\s+(.+)",
                r"rename\s+(the\s+)?variable\s+(.+)\s+to\s+(.+)",
                r"cambia\s+(el\s+)?nombre\s+de\s+(.+)\s+a\s+(.+)",
                r"change\s+(the\s+)?name\s+of\s+(.+)\s+to\s+(.+)",
                r"extrae\s+(esta\s+)?funci[oÃ³]n",
                r"extrae\s+(este\s+)?m[eÃ©]todo",
                r"extract\s+(this\s+)?function",
                r"extract\s+(this\s+)?method",
                r"limpia\s+(los\s+)?imports",
                r"optimiza\s+(los\s+)?imports",
                r"clean\s+up\s+(the\s+)?imports",
                r"optimize\s+(the\s+)?imports",
                r"convierte\s+a\s+async",
                r"haz\s+(esta\s+)?funci[oÃ³]n\s+async",
                r"convert\s+to\s+async",
                r"make\s+(this\s+)?function\s+async",
                r"agrega\s+type\s+hints",
                r"add\s+type\s+hints",
                r"convierte\s+(el\s+)?loop\s+a\s+comprensi[oÃ³]n",
                r"convert\s+(the\s+)?loop\s+to\s+comprehension",
            ],
            # NUEVO: TestRunner patterns
            "run_tests": [
                r"ejecuta\s+(los\s+)?tests?",
                r"corre\s+(los\s+)?tests?",
                r"correr\s+(los\s+)?tests?",
                r"run\s+(the\s+)?tests?",
                r"ejecuta\s+(las\s+)?pruebas?",
                r"corre\s+(las\s+)?pruebas?",
                r"run\s+(the\s+)?test\s+ suite",
                r"pytest",
                r"unittest",
            ],
            "analyze_coverage": [
                r"analiza\s+(la\s+)?cobertura",
                r"chequea\s+(la\s+)?cobertura",
                r"muestrame\s+(la\s+)?cobertura",
                r"coverage\s+report",
                r"test\s+coverage",
                r"cobertura\s+de\s+tests?",
                r"cu[aÃ¡]l\s+es\s+(la\s+)?cobertura",
                r"qu[eÃ©]\s+tanto\s+cubre\s+(el\s+)?c[oÃ³]digo",
                r"code\s+coverage",
            ],
            "find_missing_tests": [
                r"encuentra\s+tests?\s+faltantes",
                r"busca\s+tests?\s+faltantes",
                r"qu[eÃ©]\s+(m[oÃ³]dulos?|archivos?)\s+no\s+tienen\s+tests?",
                r"missing\s+tests?",
                r"qu[eÃ©]\s+falta\s+testear",
                r"qu[eÃ©]\s+no\s+tiene\s+tests?",
                r"find\s+missing\s+tests?",
            ],
            # NUEVO: DependencyManager patterns
            "manage_dependencies": [
                r"instala\s+(el\s+)?(paquete\s+)?(.+)",
                r"agrega\s+(el\s+)?(paquete\s+)?(.+)",
                r"instalar\s+(el\s+)?(paquete\s+)?(.+)",
                r"agregar\s+(el\s+)?(paquete\s+)?(.+)",
                r"install\s+(the\s+)?(package\s+)?(.+)",
                r"add\s+(the\s+)?(package\s+)?(.+)",
                r"pip\s+install\s+(.+)",
                r"npm\s+install\s+(.+)",
            ],
            "update_dependencies": [
                r"actualiza\s+(las\s+)?dependencias?",
                r"actualiza\s+(los\s+)?(paquetes?|m[oÃ³]dulos?)",
                r"upgrade\s+(the\s+)?(packages?|dependencies?)",
                r"update\s+(the\s+)?(packages?|dependencies?)",
                r"pip\s+upgrade",
                r"npm\s+update",
            ],
            "audit_dependencies": [
                r"audita\s+(las\s+)?dependencias?",
                r"revisa\s+(las\s+)?dependencias?",
                r"auditor[iÃ­]a\s+de\s+seguridad",
                r"vulnerabilidades?\s+en\s+dependencias?",
                r"security\s+audit",
                r"audit\s+(the\s+)?(packages?|dependencies?)",
                r"check\s+(for\s+)?vulnerabilities",
                r"npm\s+audit",
            ],
            "list_dependencies": [
                r"lista\s+(las\s+)?dependencias?",
                r"muestrame\s+(las\s+)?dependencias?",
                r"qu[eÃ©]\s+(paquetes?|m[oÃ³]dulos?)\s+tengo\s+instalados?",
                r"list\s+(the\s+)?(packages?|dependencies?)",
                r"show\s+(the\s+)?(packages?|dependencies?)",
                r"qu[eÃ©]\s+dependencias?\s+tengo",
            ],
            "find_unused_deps": [
                r"dependencias?\s+no\s+usadas?",
                r"dependencias?\s+sin\s+uso",
                r"unused\s+dependencies?",
                r"find\s+unused\s+(packages?|dependencies?)",
                r"paquetes?\s+no\s+usados?",
            ],
            "search_package": [
                r"busca\s+(el\s+)?paquete\s+(.+)",
                r"encuentra\s+(el\s+)?paquete\s+(.+)",
                r"search\s+(for\s+)?(the\s+)?package\s+(.+)",
                r"info\s+(del\s+)?paquete\s+(.+)",
                r"informaci[oÃ³]n\s+(del\s+)?paquete\s+(.+)",
            ],
            # NUEVO: GitTools patterns
            "git_status": [
                r"estado\s+(del\s+)?repo",
                r"estado\s+de\s+git",
                r"git\s+status",
                r"qu[eÃ©]\s+cambios\s+hay",
                r"qu[eÃ©]\s+archivos\s+(han\s+)?cambiado",
                r"status\s+(of\s+)?(the\s+)?repo",
                r"working\s+tree\s+status",
            ],
            "git_log": [
                r"historial\s+(de\s+)?commits?",
                r"log\s+(de\s+)?git",
                r"git\s+log",
                r"^([uÃº]ltimos?\s+)?commits?\s*$",
                r"historia\s+(del\s+)?proyecto",
                r"commit\s+history",
                r"recent\s+commits?",
                r"show\s+(me\s+)?(the\s+)?log",
            ],
            "git_diff": [
                r"diff\s+(de\s+)?git",
                r"git\s+diff",
                r"diferencias?\s+(entre\s+)?commits?",
                r"qu[eÃ©]\s+cambi[oÃ³]",
                r"cambios\s+(hechos|realizados)",
                r"ver\s+cambios",
                r"show\s+(me\s+)?(the\s+)?diff",
                r"differences?\s+between",
            ],
            "git_branch": [
                r"ramas?\s+(de\s+)?git",
                r"git\s+branch",
                r"branches?",
                r"en\s+qu[eÃ©]\s+rama\s+estoy",
                r"cambiar\s+(a\s+)?(la\s+)?rama\s+(.+)",
                r"crear\s+rama\s+(.+)",
                r"switch\s+to\s+branch",
                r"create\s+branch",
                r"list\s+branches",
            ],
            "git_commit": [
                r"haz\s+(un\s+)?commit",
                r"hacer\s+commit",
                r"crear\s+commit",
                r"git\s+commit",
                r"commitear",
                r"commitear\s+cambios",
                r"commit\s+changes",
                r"make\s+a?\s*commit",
                r"guardar\s+cambios\s+(en\s+)?git",
                r"salvar\s+cambios",
            ],
            "git_clone": [
                r"clonar\s+repo",
                r"clonar\s+repositorio",
                r"git\s+clone",
                r"descargar\s+repo",
                r"clone\s+(the\s+)?repo",
                r"clone\s+repository",
            ],
            # NUEVO: WebBrowser patterns
            "web_visit": [
                r"visita\s+(la\s+)?(url\s+)?(.+)",
                r"abre\s+(la\s+)?(url\s+)?(.+)",
                r"navega\s+a\s+(.+)",
                r"ve\s+a\s+(.+)",
                r"entra\s+a\s+(.+)",
                r"visit\s+(the\s+)?(url\s+)?(.+)",
                r"open\s+(the\s+)?(url\s+)?(.+)",
                r"go\s+to\s+(.+)",
            ],
            "web_search": [
                r"busca\s+(en\s+)?(internet|google|la\s+web)\s+(.+)",
                r"busca\s+(.+)\s+en\s+(internet|google|la\s+web)",
                r"investiga\s+(?!a\s+fondo|profund)",
                r"busca\s+informaci[oÃ³]n\s+sobre\s+(.+)",
                r"search\s+(for\s+)?(.+)\s+on\s+(internet|google|web)",
                r"search\s+(for\s+)?(.+)",
                r"look\s+up\s+(.+)",
                r"google\s+(.+)",
            ],
            "web_extract_links": [
                r"extrae\s+(los\s+)?links\s+de\s+(.+)",
                r"obt[eÃ©]n\s+(los\s+)?enlaces\s+de\s+(.+)",
                r"dame\s+(los\s+)?links\s+de\s+(.+)",
                r"extract\s+(the\s+)?links\s+from\s+(.+)",
                r"get\s+(the\s+)?links\s+from\s+(.+)",
                r"qu[eÃ©]\s+links\s+hay\s+en\s+(.+)",
            ],
            "web_get_title": [
                r"t[iÃ­]tulo\s+de\s+la\s+p[aÃ¡]gina",
                r"t[iÃ­]tulo\s+de\s+(.+)",
                r"cu[aÃ¡]l\s+es\s+el\s+t[iÃ­]tulo",
                r"page\s+title",
                r"title\s+of\s+(.+)",
            ],
            # NUEVO: Research patterns
            "deep_research": [
                r"investiga\s+a\s+fondo\s+(.+)",
                r"investigaci[oÃ³]n\s+profunda\s+sobre\s+(.+)",
                r"deep\s+research\s+(.+)",
                r"investigate\s+thoroughly\s+(.+)",
                r"research\s+in\s+depth\s+(.+)",
                r"compila\s+informaci[oÃ³]n\s+sobre\s+(.+)",
                r"compile\s+information\s+about\s+(.+)",
                r"recopila\s+datos\s+sobre\s+(.+)",
                r"gather\s+information\s+about\s+(.+)",
            ],
            "fact_check": [
                r"verifica\s+(si\s+)?(.+)\s+es\s+(verdad|cierto|correcto)",
                r"fact\s+check[:\s]+(.+)",
                r"es\s+(verdad|cierto)\s+que\s+(.+)",
                r"es\s+cierto\s+que\s+(.+)",
                r"confirma\s+si\s+(.+)",
                r"confirm\s+if\s+(.+)",
                r"verifica\s+esta\s+afirmaci[oÃ³]n",
                r"verify\s+this\s+claim",
            ],
            "compare_sources": [
                r"compara\s+(las\s+)?fuentes",
                r"compara\s+informaci[oÃ³]n\s+de\s+(.+)",
                r"compara\s+(.+)\s+con\s+(.+)",
                r"qu[eÃ©]\s+diferencias\s+hay\s+entre\s+(.+)\s+y\s+(.+)",
                r"compare\s+(the\s+)?sources",
                r"compare\s+information\s+from\s+(.+)",
                r"compare\s+(.+)\s+with\s+(.+)",
                r"differences\s+between\s+(.+)\s+and\s+(.+)",
            ],
            "summarize_topic": [
                r"resume\s+el\s+tema\s+(.+)",
                r"resumen\s+de\s+(.+)",
                r"sintetiza\s+informaci[oÃ³]n\s+sobre\s+(.+)",
                r"synthesize\s+information\s+about\s+(.+)",
                r"resume\s+lo\s+que\s+sabes\s+sobre\s+(.+)",
                r"summarize\s+(the\s+)?topic[:\s]+(.+)",
                r"summary\s+of\s+(.+)",
                r"dame\s+un\s+resumen\s+de\s+(.+)",
                r"give\s+me\s+a\s+summary\s+of\s+(.+)",
            ],
            # NUEVO: DocManager patterns
            "generate_readme": [
                r"genera\s+(el\s+)?readme",
                r"crea\s+(el\s+)?readme",
                r"generate\s+(the\s+)?readme",
                r"create\s+(the\s+)?readme",
                r"haz\s+(el\s+)?readme",
                r"escribe\s+(el\s+)?readme",
                r"documentaci[oÃ³]n\s+general",
            ],
            "add_docstrings": [
                r"agrega\s+docstrings",
                r"a[nÃ±]ade\s+docstrings",
                r"add\s+docstrings",
                r"genera\s+docstrings",
                r"generate\s+docstrings",
                r"documenta\s+(el\s+)?c[oÃ³]digo",
                r"document\s+(the\s+)?code",
                r"faltan\s+docstrings",
            ],
            "generate_api_docs": [
                r"genera\s+(la\s+)?documentaci[oÃ³]n\s+(de\s+la\s+)?api",
                r"genera\s+(los\s+)?docs\s+de\s+la\s+api",
                r"generate\s+(the\s+)?api\s+documentation",
                r"documenta\s+(la\s+)?api",
                r"api\s+docs",
            ],
            "check_doc_coverage": [
                r"revisa\s+cobertura\s+de\s+documentaci[oÃ³]n",
                r"check\s+doc\s+coverage",
                r"cobertura\s+de\s+docs",
                r"documentaci[oÃ³]n\s+faltante",
                r"qu[eÃ©]\s+falta\s+documentar",
                r"missing\s+documentation",
            ],
            "update_changelog": [
                r"actualiza\s+(el\s+)?changelog",
                r"update\s+(the\s+)?changelog",
                r"a[nÃ±]ade\s+(al\s+)?changelog",
                r"agrega\s+(al\s+)?changelog",
                r"registra\s+cambios",
                r"log\s+de\s+cambios",
            ],
            # NUEVO: GraphManager patterns
            "dependency_graph": [
                r"grafo\s+(de\s+)?dependencias?",
                r"mapa\s+(de\s+)?dependencias?",
                r"dependency\s+graph",
                r"visualiza\s+(las\s+)?dependencias?",
                r"muestra\s+(las\s+)?dependencias?",
                r"que\s+depende\s+de\s+que",
                r"como\s+estan\s+conectados?\s+(los\s+)?(archivos?|modulos?)",
            ],
            "class_diagram": [
                r"diagrama\s+(de\s+)?clases?",
                r"class\s+diagram",
                r"visualiza\s+(las\s+)?clases?",
                r"jerarquia\s+de\s+clases?",
                r"herencia\s+de\s+clases?",
            ],
            "call_graph": [
                r"grafo\s+(de\s+)?llamadas?",
                r"call\s+graph",
                r"que\s+funciones?\s+llaman?\s+a\s+que",
                r"flujo\s+de\s+llamadas?",
                r"rastro\s+de\s+ejecucion",
            ],
            "project_structure": [
                r"estructura\s+del\s+proyecto",
                r"arbol\s+del\s+proyecto",
                r"organizacion\s+del\s+codigo",
                r"project\s+structure",
                r"como\s+esta\s+organizado\s+(el\s+)?proyecto",
            ],
            "metrics_chart": [
                r"grafico\s+de\s+metricas?",
                r"visualiza\s+(las\s+)?metricas?",
                r"estadisticas?\s+del\s+codigo",
                r"code\s+metrics?",
                r"complejidad\s+del\s+codigo",
                r"lines?\s+of\s+code",
            ],
            "coverage_heatmap": [
                r"heatmap\s+de\s+cobertura",
                r"mapa\s+de\s+calor\s+de\s+cobertura",
                r"visualiza\s+(la\s+)?cobertura",
                r"coverage\s+heatmap",
                r"que\s+(archivos?|partes?)\s+no\s+tienen\s+tests?",
            ],
        }

        # Constraint patterns
        self.constraint_patterns = [
            r"pero\s+enf(o|Ã³)c(a|Ã¡)(te|te|a)\s+en\s+(.+?)(?=\s|$|\.)",
            r"especialmente\s+en\s+(.+?)(?=\s|$|\.)",
            r"principalmente\s+en\s+(.+?)(?=\s|$|\.)",
            r"limit(a|Ã¡|ado)\s+a\s+(.+?)(?=\s|$|\.)",
            r"focus\s+on\s+(.+?)(?=\s|$|\.)",
            r"especially\s+in\s+(.+?)(?=\s|$|\.)",
            r"mainly\s+in\s+(.+?)(?=\s|$|\.)",
        ]

    def detect_intent(self, user_message: str, context: dict = None) -> DetectedIntent:
        """
        Detect intent from natural language message

        Args:
            user_message: The raw natural language input
            context: Optional context (previous messages, current session)

        Returns:
            DetectedIntent with structured information
        """
        result = DetectedIntent()
        result.natural_language = user_message

        # Normalize message
        normalized = self._normalize_message(user_message)

        # Pattern-based detection (fast, no LLM needed)
        pattern_detected = self._detect_with_patterns(normalized)

        if pattern_detected:
            result.intent_type = pattern_detected["intent_type"]
            result.confidence = pattern_detected["confidence"]
            result.tool_suggestions = pattern_detected["tool_suggestions"]
        else:
            # Use LLM for complex cases
            result = self._detect_with_llm(user_message, context)

        # Extract constraints (always)
        result.extracted_constraints = self._extract_constraints(normalized)
        result.context_references = self._extract_context_references(normalized)

        # Determine if clarification needed
        result.clarification_needed = self._needs_clarification(result)

        return result

    def _normalize_message(self, message: str) -> str:
        """Normalize message for pattern matching"""
        # Convert to lowercase
        normalized = message.lower()

        # Remove extra whitespace
        normalized = re.sub(r"\s+", " ", normalized)

        # Remove punctuation at edges
        normalized = normalized.strip(".,!?:;")

        return normalized

    def _detect_with_patterns(self, normalized_message: str) -> Optional[dict]:
        """Detect intent using pattern matching (fast, no LLM)"""
        best_match = None
        best_score = 0.0

        for intent_type, patterns in self.intent_patterns.items():
            for pattern in patterns:
                match = re.search(pattern, normalized_message, re.IGNORECASE)
                if match:
                    # Calculate confidence based on match quality
                    score = self._calculate_pattern_match_score(
                        intent_type, match, normalized_message
                    )

                    if score > best_score:
                        best_score = score
                        best_match = {
                            "intent_type": intent_type,
                            "confidence": score,
                            "tool_suggestions": self._suggest_tools_for_intent(
                                intent_type, match
                            ),
                        }

        # Return best match if it's above threshold
        if best_match and best_score >= self.min_confidence_threshold:
            return best_match

        return None

    def _calculate_pattern_match_score(
        self, intent_type: str, match: re.Match, full_message: str
    ) -> float:
        """Calculate confidence score based on pattern match quality"""
        # Start with base score
        score = 0.7

        # Bonus for match position (earlier = more likely intent)
        match_start = match.start()
        message_length = len(full_message)
        position_bonus = (1 - (match_start / message_length)) * 0.2
        score += position_bonus

        # Bonus for match specificity (more specific patterns = higher confidence)
        if "\\\\" in match.re.pattern or "\\\\" in str(match.re):
            score += 0.1  # Specific regex patterns

        # Penalty for message length (very long = less clear intent)
        if len(full_message) > 200:
            score -= 0.1

        # Contextual scoring - boost for specific keywords
        score = self._apply_contextual_scoring(intent_type, full_message, score)

        return min(0.95, max(score, 0.5))  # Clamp between 0.5 and 0.95

    def _apply_contextual_scoring(
        self, intent_type: str, message: str, current_score: float
    ) -> float:
        """Apply contextual scoring based on keywords in message"""
        message_lower = message.lower()

        # Keywords that strongly indicate specific intents
        contextual_keywords = {
            "file_read": [
                "contenido",
                "content",
                "leer",
                "read",
                "abrir",
                "open",
                "muestrame",
            ],
            "file_write": [
                "escribir",
                "write",
                "guardar",
                "save",
                "crear archivo",
                "create file",
            ],
            "file_list": [
                "lista",
                "list",
                "directorio",
                "directory",
                "carpeta",
                "folder",
                "en el directorio",
            ],
            "file_search": [
                "buscar archivo",
                "search file",
                "encontrar archivo",
                "find file",
                "donde esta",
            ],
            "project_scan": [
                "proyecto",
                "project",
                "estructura",
                "structure",
                "escanear",
                "scan",
                "codebase",
                "repositorio",
                "repo",
            ],
            "task_plan": [
                "plan",
                "tareas",
                "tasks",
                "pasos",
                "steps",
                "organizar",
                "organize",
                "planificar",
                "planning",
            ],
            "code_review": [
                "revisar codigo",
                "review code",
                "analizar codigo",
                "check code",
            ],
            "refactor_code": [
                "refactorizar",
                "refactor",
                "renombrar",
                "rename",
                "extraer",
                "extract",
                "optimizar",
                "optimize",
                "async",
                "type hints",
            ],
            # NUEVOS: DependencyManager
            "manage_dependencies": [
                "instalar",
                "install",
                "pip install",
                "npm install",
                "agregar paquete",
                "add package",
                "requirements.txt",
                "package.json",
            ],
            "update_dependencies": [
                "actualizar",
                "update",
                "upgrade",
                "pip upgrade",
                "npm update",
            ],
            "audit_dependencies": [
                "auditar",
                "audit",
                "vulnerabilidad",
                "vulnerability",
                "seguridad",
                "security",
            ],
            "list_dependencies": [
                "listar dependencias",
                "list dependencies",
                "paquetes instalados",
                "installed packages",
            ],
            "find_unused_deps": [
                "dependencias no usadas",
                "unused dependencies",
                "paquetes no usados",
            ],
            "search_package": [
                "buscar paquete",
                "search package",
                "info paquete",
                "package info",
            ],
            # NUEVOS: GitTools
            "git_status": [
                "estado git",
                "git status",
                "cambios en git",
                "working tree",
                "modified files",
                "staged files",
            ],
            "git_log": [
                "historial git",
                "git log",
                "commits recientes",
                "commit history",
                "log de git",
            ],
            "git_diff": [
                "diff git",
                "git diff",
                "diferencias",
                "cambios realizados",
                "quÃ© cambiÃ³",
            ],
            "git_branch": [
                "ramas git",
                "git branch",
                "branches",
                "cambiar rama",
                "crear rama",
                "switch branch",
            ],
            "git_commit": [
                "hacer commit",
                "git commit",
                "commitear",
                "guardar cambios git",
                "make commit",
            ],
            "git_clone": [
                "clonar repo",
                "git clone",
                "clonar repositorio",
                "download repo",
                "clone repository",
            ],
            # NUEVOS: WebBrowser
            "web_visit": [
                "visita",
                "visitar",
                "abre la url",
                "navega a",
                "open url",
                "visit page",
                "go to",
            ],
            "web_search": [
                "busca en internet",
                "busca en google",
                "investiga en",
                "search for",
                "google",
                "look up",
            ],
            "web_extract_links": [
                "extrae links",
                "get links",
                "extract links",
                "obtÃ©n enlaces",
                "links de",
            ],
            "web_get_title": [
                "tÃ­tulo de la pÃ¡gina",
                "page title",
                "tÃ­tulo del sitio",
                "tÃ­tulo de",
            ],
            # NUEVOS: Research
            "deep_research": [
                "investiga a fondo",
                "investigaciÃ³n profunda",
                "deep research",
                "compile information",
                "recopila datos",
            ],
            "fact_check": [
                "fact check",
                "verifica si es verdad",
                "es cierto que",
                "confirma si",
                "verify this claim",
            ],
            "compare_sources": [
                "compara fuentes",
                "compara informaciÃ³n",
                "compare sources",
                "differences between",
            ],
            "summarize_topic": [
                "resume el tema",
                "resumen de",
                "synthesize information",
                "summary of",
                "summarize topic",
            ],
            # NUEVOS: DocManager
            "generate_readme": [
                "genera readme",
                "crea readme",
                "generate readme",
                "haz readme",
                "documentacion general",
                "readme.md",
            ],
            "add_docstrings": [
                "agrega docstrings",
                "add docstrings",
                "documenta codigo",
                "faltan docstrings",
                "missing docs",
                "falta documentar",
            ],
            "generate_api_docs": [
                "genera documentacion api",
                "generate api documentation",
                "api docs",
                "documenta api",
            ],
            "check_doc_coverage": [
                "revisa cobertura documentacion",
                "check doc coverage",
                "documentacion faltante",
                "missing documentation",
            ],
            "update_changelog": [
                "actualiza changelog",
                "update changelog",
                "registra cambios",
                "log de cambios",
            ],
            # NUEVOS: GraphManager
            "dependency_graph": [
                "grafo de dependencias",
                "dependency graph",
                "visualiza dependencias",
                "mapa de dependencias",
            ],
            "class_diagram": [
                "diagrama de clases",
                "class diagram",
                "jerarquia de clases",
                "jerarquÃ­a de clases",
                "herencia",
            ],
            "call_graph": [
                "grafo de llamadas",
                "call graph",
                "flujo de llamadas",
                "rastro de ejecucion",
            ],
            "project_structure": [
                "estructura del proyecto",
                "project structure",
                "arbol del proyecto",
                "organizacion del codigo",
            ],
            "metrics_chart": [
                "grafico de metricas",
                "code metrics",
                "estadisticas del codigo",
                "complejidad",
            ],
            "coverage_heatmap": [
                "heatmap de cobertura",
                "coverage heatmap",
                "mapa de calor",
                "visualiza cobertura",
            ],
        }

        # Check if message contains keywords for this intent
        keywords = contextual_keywords.get(intent_type, [])
        for keyword in keywords:
            if keyword in message_lower:
                # Bonus for each matching keyword (max 0.15 total)
                current_score = min(0.95, current_score + 0.05)

        # Negative indicators - reduce score if conflicting keywords present
        negative_keywords = {
            "file_write": [
                "plan de",
                "plan for",
                "plan para",
                "readme",
                "docstring",
                "documentacion",
            ],  # "crea readme" no es file_write
            "code_review": [
                "escanea el proyecto",
                "scan project",
                "estructura del proyecto",
            ],
            "manage_dependencies": [
                "docstring",
                "documentacion",
                "api docs",
                "changelog",
            ],
        }

        neg_keywords = negative_keywords.get(intent_type, [])
        for keyword in neg_keywords:
            if keyword in message_lower:
                current_score -= 0.15  # Significant penalty

        return max(0.5, current_score)

    def _suggest_tools_for_intent(self, intent_type: str, match: re.Match) -> List[str]:
        """Suggest appropriate tools based on detected intent"""
        tool_mapping = {
            "code_review": ["CodeAnalyzer"],
            "code_security": ["CodeAnalyzer"],
            "research": ["Research", "WebBrowser"],
            "web_visit": ["WebBrowser"],
            "system_execute": ["SystemExecutor"],
            "generate": ["ImageProcessor"],
            "workflow": ["AutoWorkflowGenerator"],
            # NUEVOS: Skills autÃ³nomas
            "file_read": ["FileManager"],
            "file_write": ["FileManager"],
            "file_list": ["FileManager"],
            "file_search": ["FileManager"],
            "project_scan": ["ProjectScanner"],
            "task_plan": ["TaskTracker"],
            "refactor_code": ["CodeRefactor"],
            "run_tests": ["TestRunner"],
            "analyze_coverage": ["TestRunner"],
            "find_missing_tests": ["TestRunner"],
            # NUEVOS: DependencyManager
            "manage_dependencies": ["DependencyManager"],
            "update_dependencies": ["DependencyManager"],
            "audit_dependencies": ["DependencyManager"],
            "list_dependencies": ["DependencyManager"],
            "find_unused_deps": ["DependencyManager"],
            "search_package": ["DependencyManager"],
            # NUEVOS: GitTools
            "git_status": ["GitTools"],
            "git_log": ["GitTools"],
            "git_diff": ["GitTools"],
            "git_branch": ["GitTools"],
            "git_commit": ["GitTools"],
            "git_clone": ["GitTools"],
            # NUEVOS: WebBrowser
            "web_visit": ["WebBrowser"],
            "web_search": ["WebBrowser"],
            "web_extract_links": ["WebBrowser"],
            "web_get_title": ["WebBrowser"],
            # NUEVOS: Research
            "deep_research": ["Research"],
            "fact_check": ["Research"],
            "compare_sources": ["Research"],
            "summarize_topic": ["Research"],
            # NUEVOS: DocManager
            "generate_readme": ["DocManager"],
            "add_docstrings": ["DocManager"],
            "generate_api_docs": ["DocManager"],
            "check_doc_coverage": ["DocManager"],
            "update_changelog": ["DocManager"],
            # NUEVOS: GraphManager
            "dependency_graph": ["GraphManager"],
            "class_diagram": ["GraphManager"],
            "call_graph": ["GraphManager"],
            "project_structure": ["GraphManager"],
            "metrics_chart": ["GraphManager"],
            "coverage_heatmap": ["GraphManager"],
        }

        return tool_mapping.get(intent_type, [])

    def _extract_constraints(self, normalized_message: str) -> List[str]:
        """Extract constraint patterns from message"""
        constraints = []

        for pattern in self.constraint_patterns:
            matches = re.findall(pattern, normalized_message, re.IGNORECASE)
            constraints.extend(matches)

        return [c[1] if isinstance(c, tuple) else c for c in constraints if c]

    def _extract_context_references(self, normalized_message: str) -> List[str]:
        """Extract references to context ("este", "este archivo", etc.)"""
        references = []

        context_patterns = [
            r"este\s+(archivo|c(o|Ã³)di(go?g?o?)|proyecto)",
            r"ese\s+(archivo|c(o|Ã³)di(go?g?o?)|proyecto)",
            r"esto\s+(aqu(i|Ã­)|ahora|en\s+esto)",
            r"this\s+(file|code|project)",
            r"that\s+(file|code|project)",
            r"it\s+(here|now)",
        ]

        for pattern in context_patterns:
            matches = re.findall(pattern, normalized_message, re.IGNORECASE)
            references.extend(matches)

        return [ref[0] if isinstance(ref, tuple) else ref for ref in references if ref]

    def _needs_clarification(self, detected_intent: DetectedIntent) -> bool:
        """Determine if clarification is needed"""
        # Low confidence
        if detected_intent.confidence < self.clarification_threshold:
            return True

        # Missing target
        if not detected_intent.target and detected_intent.intent_type not in [
            "workflow",
            "system_execute",
        ]:
            return True

        # Too many context references (ambiguous)
        if len(detected_intent.context_references) > 2:
            return True

        return False

    def _detect_with_llm(
        self, user_message: str, context: dict = None
    ) -> DetectedIntent:
        """Use LLM for complex intent detection (fallback)"""
        result = DetectedIntent()
        result.natural_language = user_message

        # For now, return a safe default (we'll implement actual LLM call next)
        # This prevents system from failing completely

        # Check if message mentions code
        if any(
            word in user_message.lower()
            for word in ["cÃ³digo", "code", "file", "archivo"]
        ):
            result.intent_type = "code_review"
            result.tool_suggestions = ["CodeAnalyzer"]
            result.confidence = 0.6
        # Check if mentions searching
        elif any(
            word in user_message.lower()
            for word in ["busca", "search", "investiga", "research"]
        ):
            result.intent_type = "research"
            result.tool_suggestions = ["Research", "WebBrowser"]
            result.confidence = 0.6
        # Check if browsing
        elif any(
            word in user_message.lower()
            for word in ["visita", "visit", "abre", "open", "url", "pÃ¡gina"]
        ):
            result.intent_type = "web_visit"
            result.tool_suggestions = ["WebBrowser"]
            result.confidence = 0.6
        # Default to unknown
        else:
            result.intent_type = "unknown"
            result.confidence = 0.3
            result.clarification_needed = True

        return result

    def save_intent_analysis(
        self, user_message: str, detected_intent: DetectedIntent, session_id: str = None
    ):
        """Save intent analysis for learning"""
        log_entry = {
            "timestamp": time.time() if "time" in dir() else 0,
            "session_id": session_id,
            "user_message": user_message,
            "detected_intent": detected_intent.to_dict(),
            "success": None,  # Will be updated after execution
        }

        # Save to telemetry log
        log_path = Path("D:\\Proyectos\\Lilith\\Core\\memory\\intent_analysis.jsonl")
        log_path.parent.mkdir(parents=True, exist_ok=True)

        with open(log_path, "a", encoding="utf-8") as f:
            f.write(json.dumps(log_entry, ensure_ascii=False) + "\n")


# ============================================================================
# TESTS
# ============================================================================

if __name__ == "__main__":
    print("Conversational Intent Detector - Tests")
    print("=" * 60)

    detector = ConversationalIntentDetector()

    test_messages = [
        "Oye, revisa este cÃ³digo",
        "Busca informaciÃ³n sobre async en Python",
        "Visita la pÃ¡gina de Python",
        "Ejecuta el script de prueba",
        "Haz un commit de estos cambios",
        "Crea una imagen de un gato",
    ]

    for i, msg in enumerate(test_messages, 1):
        print(f"\nTest {i}: '{msg}'")
        intent = detector.detect_intent(msg)
        print(f"  Intent: {intent.intent_type}")
        print(f"  Confidence: {intent.confidence:.2f}")
        print(f"  Tools: {intent.tool_suggestions}")
        if intent.extracted_constraints:
            print(f"  Constraints: {intent.extracted_constraints}")

    print("\n[OK] Tests completed!")
