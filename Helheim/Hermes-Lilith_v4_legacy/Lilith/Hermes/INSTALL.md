# Instalación de Hermes Agent + Lilith MCP Bridge

## Requisitos Previos

1. **WSL2** instalado en Windows
2. **Docker Desktop** (opcional, para sandboxing)
3. **LM Studio** ejecutándose en Windows (puerto 1234)

---

## Paso 1: Instalar WSL2 (si no lo tienes)

```powershell
# En PowerShell (Admin)
wsl --install -d Ubuntu
```

Reinicia tu PC y configura Ubuntu.

---

## Paso 2: Instalar Hermes Agent

```bash
# En Ubuntu/WSL2
curl -fsSL https://hermes-agent.nousresearch.com/install.sh | bash

# Recargar shell
source ~/.bashrc

# Verificar instalación
hermes --version
```

---

## Paso 3: Configurar Hermes

```bash
# Iniciar configuración interactiva
hermes setup
```

Te preguntará:
- **Modelo a usar**: Selecciona API local o endpoint personalizado
- **Modo CLI**: Yes (no necesitamos Discord/Telegram por ahora)

---

## Paso 4: Configurar LM Studio como endpoint

Hermes puede usar tu LM Studio local. En `hermes setup`:

```
Provider: Custom Endpoint
Endpoint URL: http://localhost:1234/v1
Model: google/gemma-4-e4b
```

---

## Paso 5: Copiar el MCP Bridge de Lilith

```bash
# En WSL2, ir al home
cd ~

# Crear estructura para skills
mkdir -p ~/.hermes/skills
mkdir -p ~/.hermes/plugins

# El MCP bridge se configurará automáticamente
```

---

## Paso 6: Usar Hermes con las tools de Lilith

Una vez instalado Hermes, puedes:

1. **Iniciar Hermes**: `hermes` en WSL2
2. **Usar comandos**: `/help`, `/skills`, `/tools`
3. **Las tools de Lilith** estarán disponibles via MCP

---

## Solución de Problemas

### Hermes no conecta a LM Studio Windows

En WSL2, usa la IP de Windows:

```bash
# Obtener IP de Windows
grep nameserver /etc/resolv.conf

# Endpoint sería:
# http://<IP-WINDOWS>:1234/v1
```

### Verificar Docker (para sandboxing)

```bash
docker --version
# Si no está, instala Docker Desktop en Windows
```

---

## Comandos Útiles

```bash
hermes              # Iniciar
hermes --help       # Ver ayuda
hermes tools        # Listar tools disponibles
hermes skills       # Listar skills
hermes config       # Ver/configurar
```

---

## Siguiente Paso

Una vez instalado Hermes, copiamos el MCP Bridge de Lilith a la carpeta de skills de Hermes.
