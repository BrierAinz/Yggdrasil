"""
Lilith Visual Analyzer v1.0
Allows Lilith to "see" the screen, analyze UI, and debug visual issues.
"""

import base64
import logging
import os
import subprocess
import time
from datetime import datetime
from typing import Any, Dict, Optional

logger = logging.getLogger("VisualAnalyzer")


class VisualAnalyzer:
    """
    Captures screenshots and uses vision LLMs to analyze them.
    Useful for UI debugging, verifying layout, and "seeing" what the user sees.
    """

    def __init__(self, llm_client=None):
        # Vision capabilities temporarily disabled - Gemini provider removed
        self.llm = llm_client
        self.temp_dir = os.path.join(os.getcwd(), "temp", "screenshots")
        os.makedirs(self.temp_dir, exist_ok=True)
        logger.info("VisualAnalyzer initialized")

    def capture_screen(self) -> Optional[str]:
        """
        Captures the primary screen using PowerShell.
        Returns the path to the saved screenshot.
        """
        timestamp = datetime.now().strftime("%Y%m%d_%H%M%S")
        filepath = os.path.join(self.temp_dir, f"screenshot_{timestamp}.png")

        logger.info(f"Capturing screen to {filepath}...")

        # PowerShell command to capture screen
        ps_cmd = f"""
        Add-Type -AssemblyName System.Windows.Forms
        $screen = [System.Windows.Forms.Screen]::PrimaryScreen
        $top    = $screen.Bounds.Top
        $left   = $screen.Bounds.Left
        $width  = $screen.Bounds.Width
        $height = $screen.Bounds.Height
        $bitmap = New-Object System.Drawing.Bitmap($width, $height)
        $graphics = [System.Drawing.Graphics]::FromImage($bitmap)
        $graphics.CopyFromScreen($left, $top, 0, 0, $bitmap.Size)
        $bitmap.Save("{filepath}")
        $graphics.Dispose()
        $bitmap.Dispose()
        """

        try:
            subprocess.run(
                ["powershell", "-Command", ps_cmd], check=True, capture_output=True
            )
            if os.path.exists(filepath):
                return filepath
        except Exception as e:
            logger.error(f"Failed to capture screen: {e}")

        return None

    def analyze_ui(
        self, prompt: str, screenshot_path: Optional[str] = None
    ) -> Dict[str, Any]:
        """
        Takes a screenshot (if not provided) and analyzes it with the LLM.
        """
        path = screenshot_path or self.capture_screen()
        if not path:
            return {"success": False, "error": "No se pudo capturar la pantalla."}

        try:
            with open(path, "rb") as image_file:
                encoded_string = base64.b64encode(image_file.read()).decode("utf-8")

            analysis = self.llm.generate_text(
                prompt=prompt,
                image_data=encoded_string,
                mime_type="image/png",
                system_prompt="Eres un experto en QA y diseÃ±o de UI/UX. Analiza la imagen proporcionada y responde a la solicitud del usuario con precisiÃ³n tÃ©cnica.",
            )

            return {"success": True, "analysis": analysis, "screenshot_path": path}
        except Exception as e:
            logger.error(f"Analysis failed: {e}")
            return {"success": False, "error": str(e)}

    def run(self, action: str, **kwargs) -> Dict[str, Any]:
        """Tool interface for registry"""
        if action == "analyze_screen":
            prompt = kwargs.get(
                "prompt",
                "Describe quÃ© ves en la pantalla y si hay algÃºn error visible.",
            )
            return self.analyze_ui(prompt)
        elif action == "capture_only":
            path = self.capture_screen()
            return (
                {"success": True, "path": path}
                if path
                else {"success": False, "error": "Capture failed"}
            )

        return {"success": False, "error": f"Unknown action: {action}"}
