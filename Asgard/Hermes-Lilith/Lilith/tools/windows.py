"""
Windows Tools
============
Tools para administrar Windows.
"""
import subprocess


def get_tools():
    """Retorna lista de definiciones de tools de Windows."""
    return [
        {
            "type": "function",
            "function": {
                "name": "list_processes",
                "description": "Listar procesos en ejecucion",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Filtrar por nombre (opcional)",
                        }
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "kill_process",
                "description": "Matar un proceso por nombre",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {
                            "type": "string",
                            "description": "Nombre del proceso a matar",
                        }
                    },
                    "required": ["name"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_system_info",
                "description": "Obtener informacion del sistema",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_disk_space",
                "description": "Obtener espacio en disco",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "drive": {"type": "string", "description": "Unidad (ej: C, D)"}
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "list_services",
                "description": "Listar servicios de Windows",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "running_only": {
                            "type": "boolean",
                            "description": "Solo servicios corriendo",
                        }
                    },
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "start_service",
                "description": "Iniciar un servicio de Windows",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Nombre del servicio"}
                    },
                    "required": ["name"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "stop_service",
                "description": "Detener un servicio de Windows",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "name": {"type": "string", "description": "Nombre del servicio"}
                    },
                    "required": ["name"],
                },
            },
        },
    ]


def execute_tool(name: str, args: dict = None) -> dict:
    """Ejecuta una tool de Windows."""
    args = args or {}

    if name == "list_processes":
        return execute_list_processes(args.get("name"))
    elif name == "kill_process":
        return execute_kill_process(args.get("name"))
    elif name == "get_system_info":
        return execute_system_info()
    elif name == "get_disk_space":
        return execute_disk_space(args.get("drive", "C"))
    elif name == "list_services":
        return execute_list_services(args.get("running_only", False))
    elif name == "start_service":
        return execute_service(args.get("name"), "start")
    elif name == "stop_service":
        return execute_service(args.get("name"), "stop")
    else:
        return {"error": f"Tool desconocida: {name}"}


def execute_list_processes(name: str = None) -> dict:
    """Lista procesos."""
    try:
        if name:
            script = f"""
            Get-Process -Name "*{name}*" |
            Select-Object Name, Id, CPU, WorkingSet64 |
            ConvertTo-Json
            """
        else:
            script = """
            Get-Process |
            Select-Object Name, Id, CPU, WorkingSet64 |
            Sort-Object WorkingSet64 -Descending |
            Select-Object -First 20 |
            ConvertTo-Json
            """

        result = subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True,
            text=True,
            timeout=15,
        )

        return {"success": True, "output": result.stdout[:3000]}

    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_kill_process(name: str) -> dict:
    """Mata un proceso."""
    try:
        script = f'Stop-Process -Name "{name}" -Force -ErrorAction SilentlyContinue; "Killed"'

        result = subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True,
            text=True,
            timeout=10,
        )

        return {"success": True, "process": name, "output": result.stdout.strip()}

    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_system_info() -> dict:
    """Obtiene info del sistema."""
    try:
        script = """
        @{
            ComputerName = $env:COMPUTERNAME
            UserName = $env:USERNAME
            OS = (Get-CimInstance Win32_OperatingSystem).Caption
            Version = (Get-CimInstance Win32_OperatingSystem).Version
            TotalRAM = [math]::Round((Get-CimInstance Win32_ComputerSystem).TotalPhysicalMemory / 1GB, 2)
            FreeRAM = [math]::Round((Get-CimInstance Win32_OperatingSystem).FreePhysicalMemory / 1MB, 2)
            CPU = (Get-CimInstance Win32_Processor).Name
        } | ConvertTo-Json
        """

        result = subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True,
            text=True,
            timeout=15,
        )

        return {"success": True, "output": result.stdout}

    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_disk_space(drive: str) -> dict:
    """Obtiene espacio en disco."""
    try:
        script = (
            """
        Get-PSDrive -Name """
            + drive
            + """ |
        Select-Object Name, @{N="UsedGB";E={[math]::Round($_.Used/1GB,2)}}, @{N="FreeGB";E={[math]::Round($_.Free/1GB,2)}}, @{N="TotalGB";E={[math]::Round(($_.Used+$_.Free)/1GB,2)}} |
        ConvertTo-Json
        """
        )

        result = subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True,
            text=True,
            timeout=10,
        )

        return {"success": True, "drive": drive, "output": result.stdout}

    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_list_services(running_only: bool = False) -> dict:
    """Lista servicios."""
    try:
        if running_only:
            script = """
            Get-Service | Where-Object {$_.Status -eq "Running"} |
            Select-Object Name, DisplayName, Status |
            Sort-Object DisplayName |
            ConvertTo-Json
            """
        else:
            script = """
            Get-Service |
            Select-Object Name, DisplayName, Status |
            Sort-Object Status, DisplayName |
            ConvertTo-Json
            """

        result = subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True,
            text=True,
            timeout=15,
        )

        return {"success": True, "output": result.stdout[:4000]}

    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_service(name: str, action: str) -> dict:
    """Inicia o detiene un servicio."""
    try:
        script = f"""
        {action.capitalize()}-Service -Name "{name}" -Force
        Get-Service -Name "{name}" | Select-Object Name, Status | ConvertTo-Json
        """

        result = subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True,
            text=True,
            timeout=15,
        )

        return {
            "success": result.returncode == 0,
            "service": name,
            "action": action,
            "output": result.stdout,
        }

    except Exception as e:
        return {"success": False, "error": str(e)}
