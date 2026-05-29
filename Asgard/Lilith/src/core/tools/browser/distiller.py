import logging

import markdownify
from readability import Document

logger = logging.getLogger(__name__)


def distill_html_to_markdown(raw_html: str) -> str:
    """
    Toma HTML crudo, extrae el artículo principal ignorando ruido (nav, footer)
    y lo convierte a un Markdown limpio y denso para el LLM.
    """
    if not raw_html or not raw_html.strip():
        return ""

    try:
        doc = Document(raw_html)
        clean_html = doc.summary()

        md_text = markdownify.markdownify(
            clean_html,
            heading_style="ATX",
            strip=["script", "style", "noscript", "iframe"],
        )

        lines = [line.strip() for line in md_text.split("\n")]
        compact_text = "\n".join(line for line in lines if line)

        return compact_text[:15000]
    except Exception as e:
        logger.error("Error destilando HTML: %s", e)
        return f"[Error en destilación de contenido: {e}]"
