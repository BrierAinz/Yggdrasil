"""
Skill: monitor_sistema
Revisa CPU, RAM, disco y reporta el estado del sistema.
"""
import os
import platform
import subprocess
import time


def _get_windows_info() -> dict:
    """Obtiene info del sistema en Windows."""
    info = {}
    try:
        # CPU
        cpu_cmd = subprocess.run(
            ["wmic", "cpu", "get", "loadpercentage", "/value"],
            capture_output=True,
            text=True,
            timeout=5,
        )
        for line in cpu_cmd.stdout.strip().split("\n"):
            if "LoadPercentage" in line:
                info["cpu_percent"] = line.split("=")[1].strip() + "%"

        # RAM
        ram_cmd = subprocess.run(
            [
                "wmic",
                "OS",
                "get",
                "FreePhysicalMemory,TotalVisibleMemorySize",
                "/value",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        total_kb = free_kb = 0
        for line in ram_cmd.stdout.strip().split("\n"):
            if "TotalVisibleMemorySize" in line:
                total_kb = int(line.split("=")[1].strip())
            elif "FreePhysicalMemory" in line:
                free_kb = int(line.split("=")[1].strip())
        if total_kb:
            used_kb = total_kb - free_kb
            info["ram_total"] = f"{total_kb // 1024} MB"
            info["ram_used"] = f"{used_kb // 1024} MB"
            info["ram_free"] = f"{free_kb // 1024} MB"
            info["ram_percent"] = f"{(used_kb / total_kb) * 100:.1f}%"

        # Disk
        disk_cmd = subprocess.run(
            [
                "wmic",
                "logicaldisk",
                "where",
                "DeviceID='C:'",
                "get",
                "FreeSpace,Size",
                "/value",
            ],
            capture_output=True,
            text=True,
            timeout=5,
        )
        total_bytes = free_bytes = 0
        for line in disk_cmd.stdout.strip().split("\n"):
            if "Size=" in line:
                total_bytes = int(line.split("=")[1].strip())
            elif "FreeSpace=" in line:
                free_bytes = int(line.split("=")[1].strip())
        if total_bytes:
            info["disk_total"] = f"{total_bytes // (1024**3)} GB"
            info["disk_free"] = f"{free_bytes // (1024**3)} GB"
            info[
                "disk_used_percent"
            ] = f"{((total_bytes - free_bytes) / total_bytes) * 100:.1f}%"

    except Exception as e:
        info["error"] = str(e)
    return info


def ejecutar() -> str:
    """Genera reporte del estado del sistema."""
    reporte = []
    reporte.append(f"# Monitor del Sistema")
    reporte.append(f"*Reporte generado el {time.strftime('%Y-%m-%d %H:%M')}*\n")

    reporte.append(f"## Sistema")
    reporte.append(f"- **OS:** {platform.system()} {platform.release()}")
    reporte.append(f"- **Maquina:** {platform.machine()}")
    reporte.append(f"- **Procesador:** {platform.processor()}")
    reporte.append(f"- **Python:** {platform.python_version()}")

    if platform.system() == "Windows":
        info = _get_windows_info()

        reporte.append(f"\n## CPU")
        reporte.append(f"- **Uso:** {info.get('cpu_percent', 'N/A')}")

        reporte.append(f"\n## RAM")
        reporte.append(f"- **Total:** {info.get('ram_total', 'N/A')}")
        reporte.append(
            f"- **Usada:** {info.get('ram_used', 'N/A')} ({info.get('ram_percent', 'N/A')})"
        )
        reporte.append(f"- **Libre:** {info.get('ram_free', 'N/A')}")

        reporte.append(f"\n## Disco C:")
        reporte.append(f"- **Total:** {info.get('disk_total', 'N/A')}")
        reporte.append(f"- **Libre:** {info.get('disk_free', 'N/A')}")
        reporte.append(f"- **Uso:** {info.get('disk_used_percent', 'N/A')}")

        # Alertas
        reporte.append(f"\n## Alertas")
        alerts = []
        try:
            cpu_val = float(info.get("cpu_percent", "0").replace("%", ""))
            if cpu_val > 80:
                alerts.append(f"[!] CPU al {cpu_val}% - Carga alta")
            ram_val = float(info.get("ram_percent", "0").replace("%", ""))
            if ram_val > 85:
                alerts.append(f"[!] RAM al {ram_val}% - Memoria baja")
            disk_val = float(info.get("disk_used_percent", "0").replace("%", ""))
            if disk_val > 90:
                alerts.append(f"[!] Disco al {disk_val}% - Espacio bajo")
        except:
            pass
        if alerts:
            reporte.extend(alerts)
        else:
            reporte.append("Todo normal. Sin alertas.")

    return "\n".join(reporte)


if __name__ == "__main__":
    print(ejecutar())
