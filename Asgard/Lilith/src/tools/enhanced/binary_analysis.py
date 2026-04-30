"""
Binary Analysis Capability - NO RESTRICTIONS
PE analysis, string extraction, hex dump, pattern search
"""
import os
import re
import string
from pathlib import Path
from typing import Dict, List, Optional


class BinaryAnalysisCapability:
    """Binary file analysis - no restrictions"""

    def __init__(self):
        """Initialize binary analysis"""
        pass

    def read_binary(self, file_path: str, max_bytes: Optional[int] = None) -> Dict:
        """Read binary file"""
        try:
            with open(file_path, "rb") as f:
                data = f.read(max_bytes) if max_bytes else f.read()

            return {"success": True, "data": data, "size": len(data)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def hex_dump(self, file_path: str, max_bytes: int = 1024) -> str:
        """Generate hex dump of file"""
        try:
            result = self.read_binary(file_path, max_bytes)
            if not result["success"]:
                return f"âŒ {result['error']}"

            data = result["data"]
            output = f"ðŸ“Š Hex Dump: {Path(file_path).name}\n\n"
            output += (
                "Offset    Hex                                              ASCII\n"
            )
            output += "â”€" * 80 + "\n"

            for i in range(0, len(data), 16):
                chunk = data[i : i + 16]

                # Hex
                hex_part = " ".join(f"{b:02X}" for b in chunk)
                hex_part = hex_part.ljust(48)

                # ASCII
                ascii_part = "".join(chr(b) if 32 <= b < 127 else "." for b in chunk)

                output += f"{i:08X}  {hex_part}  {ascii_part}\n"

            return output
        except Exception as e:
            return f"âŒ Error: {str(e)}"

    def extract_strings(self, file_path: str, min_length: int = 4) -> Dict:
        """Extract printable strings from binary"""
        try:
            result = self.read_binary(file_path)
            if not result["success"]:
                return result

            data = result["data"]

            # ASCII strings
            ascii_pattern = rb"[\x20-\x7E]{" + str(min_length).encode() + rb",}"
            ascii_strings = [s.decode("ascii") for s in re.findall(ascii_pattern, data)]

            # Unicode strings
            unicode_pattern = (
                rb"(?:[\x20-\x7E]\x00){" + str(min_length).encode() + rb",}"
            )
            unicode_strings = [
                s.decode("utf-16-le") for s in re.findall(unicode_pattern, data)
            ]

            all_strings = list(set(ascii_strings + unicode_strings))
            all_strings.sort()

            return {"success": True, "strings": all_strings, "count": len(all_strings)}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def analyze_pe(self, file_path: str) -> Dict:
        """Analyze PE (Portable Executable) file"""
        try:
            import pefile

            pe = pefile.PE(file_path)

            info = {
                "success": True,
                "file": file_path,
                "type": "PE32+" if pe.OPTIONAL_HEADER.Magic == 0x20B else "PE32",
                "machine": pefile.MACHINE_TYPE[pe.FILE_HEADER.Machine],
                "timestamp": pe.FILE_HEADER.TimeDateStamp,
                "sections": [],
                "imports": [],
                "exports": [],
                "entry_point": hex(pe.OPTIONAL_HEADER.AddressOfEntryPoint),
                "image_base": hex(pe.OPTIONAL_HEADER.ImageBase),
            }

            # Sections
            for section in pe.sections:
                info["sections"].append(
                    {
                        "name": section.Name.decode("utf-8").rstrip("\x00"),
                        "virtual_address": hex(section.VirtualAddress),
                        "virtual_size": section.Misc_VirtualSize,
                        "raw_size": section.SizeOfRawData,
                        "entropy": section.get_entropy(),
                    }
                )

            # Imports
            if hasattr(pe, "DIRECTORY_ENTRY_IMPORT"):
                for entry in pe.DIRECTORY_ENTRY_IMPORT:
                    dll_name = entry.dll.decode("utf-8")
                    functions = [
                        imp.name.decode("utf-8")
                        if imp.name
                        else f"Ordinal_{imp.ordinal}"
                        for imp in entry.imports
                    ]
                    info["imports"].append(
                        {
                            "dll": dll_name,
                            "functions": functions[:10],  # Limit to first 10
                        }
                    )

            # Exports
            if hasattr(pe, "DIRECTORY_ENTRY_EXPORT"):
                for exp in pe.DIRECTORY_ENTRY_EXPORT.symbols:
                    if exp.name:
                        info["exports"].append(exp.name.decode("utf-8"))

            pe.close()
            return info

        except ImportError:
            return {"success": False, "error": "pefile not installed"}
        except Exception as e:
            return {"success": False, "error": str(e)}

    def search_bytes(self, file_path: str, pattern: bytes) -> Dict:
        """Search for byte pattern in file"""
        try:
            result = self.read_binary(file_path)
            if not result["success"]:
                return result

            data = result["data"]
            matches = []

            index = 0
            while True:
                index = data.find(pattern, index)
                if index == -1:
                    break
                matches.append(hex(index))
                index += 1

            return {
                "success": True,
                "pattern": pattern.hex(),
                "matches": matches,
                "count": len(matches),
            }
        except Exception as e:
            return {"success": False, "error": str(e)}


# Singleton
_binary = None


def get_binary_analysis() -> BinaryAnalysisCapability:
    """Get binary analysis singleton"""
    global _binary
    if _binary is None:
        _binary = BinaryAnalysisCapability()
    return _binary
