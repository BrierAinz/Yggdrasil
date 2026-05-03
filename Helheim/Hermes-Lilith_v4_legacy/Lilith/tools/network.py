"""
Network Tools
============
Tools para operaciones de red.
"""
import subprocess


def get_tools():
    """Retorna lista de definiciones de tools de red."""
    return [
        {
            "type": "function",
            "function": {
                "name": "ping",
                "description": "Hacer ping a una direccion IP o dominio",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "host": {
                            "type": "string",
                            "description": "Direccion IP o dominio a pingear",
                        },
                        "count": {
                            "type": "integer",
                            "description": "Cantidad de pings (default: 4)",
                        },
                    },
                    "required": ["host"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "check_port",
                "description": "Verificar si un puerto está abierto en localhost",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "port": {
                            "type": "integer",
                            "description": "Numero de puerto a verificar",
                        },
                        "host": {
                            "type": "string",
                            "description": "Host (default: localhost)",
                        },
                    },
                    "required": ["port"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "get_network_info",
                "description": "Obtener informacion de redes y adaptadores de red",
                "parameters": {"type": "object", "properties": {}},
            },
        },
        {
            "type": "function",
            "function": {
                "name": "download_file",
                "description": "Descargar un archivo desde una URL",
                "parameters": {
                    "type": "object",
                    "properties": {
                        "url": {
                            "type": "string",
                            "description": "URL del archivo a descargar",
                        },
                        "destination": {
                            "type": "string",
                            "description": "Ruta destino (opcional)",
                        },
                    },
                    "required": ["url"],
                },
            },
        },
        {
            "type": "function",
            "function": {
                "name": "check_internet",
                "description": "Verificar conexion a internet",
                "parameters": {"type": "object", "properties": {}},
            },
        },
    ]


def execute_tool(name: str, args: dict = None) -> dict:
    """Ejecuta una tool de red."""
    args = args or {}

    if name == "ping":
        return execute_ping(args.get("host"), args.get("count", 4))
    elif name == "check_port":
        return execute_check_port(args.get("port"), args.get("host", "localhost"))
    elif name == "get_network_info":
        return execute_get_network_info()
    elif name == "download_file":
        return execute_download_file(args.get("url"), args.get("destination"))
    elif name == "check_internet":
        return execute_check_internet()
    else:
        return {"error": f"Tool desconocida: {name}"}


def execute_ping(host: str, count: int = 4) -> dict:
    """Hace ping a un host."""
    try:
        result = subprocess.run(
            ["ping", "-n", str(count), host], capture_output=True, text=True, timeout=30
        )

        output = result.stdout
        if "TTL=" in output or "ttl=" in output:
            return {
                "success": True,
                "host": host,
                "result": "Host reachable",
                "output": output[:500],
            }
        else:
            return {
                "success": False,
                "host": host,
                "result": "Host unreachable",
                "output": output[:500],
            }

    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_check_port(port: int, host: str = "localhost") -> dict:
    """Verifica si un puerto está abierto."""
    try:
        script = f"""
        $result = Test-NetConnection -ComputerName {host} -Port {port} -WarningAction SilentlyContinue
        if ($result.TcpTestSucceeded) {{ "open" }} else {{ "closed" }}
        """

        result = subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True,
            text=True,
            timeout=10,
        )

        status = result.stdout.strip()
        return {"success": True, "host": host, "port": port, "status": status}

    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_get_network_info() -> dict:
    """Obtiene info de redes."""
    try:
        script = """
        Get-NetIPAddress | Where-Object {$_.AddressFamily -eq "IPv4" -and $_.IPAddress -ne "127.0.0.1"} |
        Select-Object IPAddress, InterfaceAlias |
        ConvertTo-Json
        """

        result = subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True,
            text=True,
            timeout=10,
        )

        return {"success": True, "output": result.stdout[:2000]}

    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_download_file(url: str, destination: str = None) -> dict:
    """Descarga un archivo."""
    try:
        if not destination:
            destination = f"D:/Downloads/{url.split('/')[-1]}"

        script = f"""
        Invoke-WebRequest -Uri "{url}" -OutFile "{destination}"
        """

        result = subprocess.run(
            ["powershell", "-Command", script],
            capture_output=True,
            text=True,
            timeout=60,
        )

        if result.returncode == 0:
            return {"success": True, "destination": destination}
        else:
            return {"success": False, "error": result.stderr[:500]}

    except Exception as e:
        return {"success": False, "error": str(e)}


def execute_check_internet() -> dict:
    """Verifica conexion a internet."""
    try:
        result = subprocess.run(
            ["ping", "-n", "1", "8.8.8.8"], capture_output=True, text=True, timeout=10
        )

        connected = "TTL=" in result.stdout or "ttl=" in result.stdout
        return {"success": True, "connected": connected}

    except Exception as e:
        return {"success": False, "error": str(e)}
