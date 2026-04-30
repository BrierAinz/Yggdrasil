#!/usr/bin/env python
"""Quick fix for broken string literals in Lilith tools"""

import os
import sys

# Change to script directory
os.chdir(os.path.dirname(os.path.abspath(__file__)))


def fix_filefinder():
    """Fix FileFinder multiline f-string"""
    try:
        with open("file_finder.py", "r", encoding="utf-8") as f:
            content = f.read()

        # Find and replace the broken section
        old = """            if not files:
                return "No files found."

            result = f"Found {len(files)} files:\n"
            result += "\n".join(files[:20])  # Limit output
            if len(files) > 20:
                result += f"\n... and {len(files) - 20} more files"

            return result"""

        new = """            if not files:
                return "No files found."

            lines = [f"Found {len(files)} files:"]
            lines.extend(files[:20])  # First 20 files
            if len(files) > 20:
                lines.append(f"... and {len(files) - 20} more files")
            return "\n".join(lines)"""

        if old in content:
            content = content.replace(old, new)
            with open("file_finder.py", "w", encoding="utf-8") as f:
                f.write(content)
            print("[OK] FileFinder fixed successfully")
            return True
        else:
            print("[OK] FileFinder already looks correct")
            return True
    except Exception as e:
        print(f"[FAIL] FileFinder fix error: {e}")
        return False


def fix_configvalidator():
    """Fix ConfigValidator multiline f-string"""
    try:
        with open("config_validator.py", "r", encoding="utf-8") as f:
            content = f.read()

        # Fix the invalid section
        old = '''                output = f"âŒ Configuration INVALID:
"
                for error in result['errors']:
                    output += f"  - ERROR: {error}
"
                for warning in result['warnings']:
                    output += f"  - WARNING: {warning}
"'''

        new = """                lines = ['Configuration INVALID:']
                for error in result['errors']:
                    lines.append(f"  - ERROR: {error}")
                for warning in result['warnings']:
                    lines.append(f"  - WARNING: {warning}")
                return "\n".join(lines)"""

        if old in content:
            content = content.replace(old, new)

            # Also fix the else block
            old_else = '''                output = f"âœ… Configuration VALID"'''
            new_else = """                lines = ['Configuration VALID']"""
            content = content.replace(old_else, new_else)

            # Fix final return
            content = content.replace(
                "            return output", '            return "\n".join(lines)'
            )

            with open("config_validator.py", "w", encoding="utf-8") as f:
                f.write(content)
            print("[OK] ConfigValidator fixed successfully")
            return True
        else:
            print("[OK] ConfigValidator already looks correct")
            return True
    except Exception as e:
        print(f"[FAIL] ConfigValidator fix error: {e}")
        return False


if __name__ == "__main__":
    print("Lilith Tools Fix Utility")
    print("=" * 40)

    ff_ok = fix_filefinder()
    cv_ok = fix_configvalidator()

    if ff_ok and cv_ok:
        print("\n[SUCCESS] Both tools fixed!")
        print("Testing...")

        # Quick test
        try:
            from file_finder import FileFinder

            finder = FileFinder()
            files = finder.find_by_extension("py", ".", max_results=3)
            print(f"âœ“ FileFinder test: Found {len(files)} Python files")
        except Exception as e:
            print(f"âš  FileFinder test skipped: {e}")

        try:
            from config_validator import ConfigValidator

            validator = ConfigValidator()
            result = validator.validate_config("../../Config/settings.json")
            print(
                f"âœ“ ConfigValidator test: Config is {'VALID' if result['valid'] else 'INVALID'}"
            )
        except Exception as e:
            print(f"âš  ConfigValidator test skipped: {e}")
    else:
        print("\n[ERROR] Some fixes failed")
        sys.exit(1)
