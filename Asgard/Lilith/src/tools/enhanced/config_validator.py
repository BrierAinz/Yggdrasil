"""
Lilith ConfigValidator Tool v2.0
Validates settings.json against schema
"""

import json
import os
from typing import Any, Dict, List


class ConfigValidator:
    """Validates configuration files"""

    def __init__(self):
        self.schema = {
            "type": "object",
            "required": ["config_version", "llm", "system"],
            "properties": {
                "config_version": {"type": "integer"},
                "llm": {
                    "type": "object",
                    "required": ["provider", "model"],
                    "properties": {
                        "provider": {
                            "type": "string",
                            "enum": ["ollama", "grok", "venice", "kimi"],
                        },
                        "model": {"type": "string"},
                        "system_prompt": {"type": "string"},
                    },
                },
                "system": {
                    "type": "object",
                    "properties": {
                        "memory_window": {
                            "type": "integer",
                            "minimum": 10,
                            "maximum": 1000,
                        },
                        "max_tool_runtime_sec": {
                            "type": "integer",
                            "minimum": 10,
                            "maximum": 600,
                        },
                    },
                },
            },
        }

    def validate_config(self, config_path: str) -> Dict[str, Any]:
        """Validate a config file against schema"""
        errors = []
        warnings = []

        if not os.path.exists(config_path):
            errors.append(f"File not found: {config_path}")
            return {"valid": False, "errors": errors, "warnings": warnings}

        try:
            with open(config_path, "r", encoding="utf-8") as f:
                config = json.load(f)

            # Basic validation
            if not isinstance(config.get("config_version"), int):
                errors.append("config_version must be an integer")

            if "llm" not in config:
                errors.append("Missing required section: llm")
            else:
                llm = config["llm"]
                if llm.get("provider") not in ["ollama", "grok", "venice", "kimi"]:
                    warnings.append(f"Unknown provider: {llm.get('provider')}")
                if not llm.get("model"):
                    errors.append("llm.model is required")

            if "system" in config:
                system = config["system"]
                if "memory_window" in system:
                    mw = system["memory_window"]
                    if not isinstance(mw, int) or mw < 10 or mw > 1000:
                        warnings.append(f"memory_window ({mw}) should be 10-1000")

            return {
                "valid": len(errors) == 0,
                "errors": errors,
                "warnings": warnings,
                "schema_compliant": len(errors) + len(warnings) == 0,
            }

        except json.JSONDecodeError as e:
            errors.append(f"Invalid JSON: {e}")
            return {"valid": False, "errors": errors, "warnings": []}
        except Exception as e:
            errors.append(f"Validation error: {e}")
            return {"valid": False, "errors": errors, "warnings": []}

    def check_recommended(self, config: Dict[str, Any]) -> List[str]:
        """Check recommended but optional settings"""
        recommendations = []

        if "safety" not in config:
            recommendations.append(
                "Consider adding 'safety' section with approval_timeout_sec"
            )

        if "logging" not in config:
            recommendations.append(
                "Consider adding 'logging' section for debug control"
            )

        return recommendations

    def execute(self, command: str) -> str:
        """Execute validation command"""
        parts = command.split()
        if len(parts) < 2:
            return "[ERROR] Usage: validate <path>"

        config_path = parts[1]

        try:
            result = self.validate_config(config_path)

            if not result["valid"]:
                lines = ["Configuration INVALID:"]
                for error in result["errors"]:
                    lines.append(f"  - ERROR: {error}")
                for warning in result["warnings"]:
                    lines.append(f"  - WARNING: {warning}")
                return "\n".join(lines)
            else:
                lines = ["Configuration VALID"]
                if result["warnings"]:
                    lines.append("with warnings:")
                    for warning in result["warnings"]:
                        lines.append(f"  - WARNING: {warning}")
                else:
                    lines.append("!")

                recommendations = self.check_recommended(json.load(open(config_path)))
                if recommendations:
                    lines.append("")
                    lines.append("Recommendations:")
                    for rec in recommendations:
                        lines.append(f"  - {rec}")

                return "\n".join(lines)

        except Exception as e:
            return f"[ERROR] Validation failed: {e}"


if __name__ == "__main__":
    import sys

    validator = ConfigValidator()

    if len(sys.argv) > 1:
        cmd = " ".join(sys.argv[1:])
        print(validator.execute(cmd))
    else:
        print("ConfigValidator tool ready")
        # Test on default config
        test_path = os.path.join(
            os.path.dirname(__file__), "..", "..", "Config", "settings.json"
        )
        if os.path.exists(test_path):
            result = validator.validate_config(test_path)
            print(f"Test: Config is {'VALID' if result['valid'] else 'INVALID'}")
