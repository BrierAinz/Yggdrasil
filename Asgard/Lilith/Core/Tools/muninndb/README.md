# MuninnDB — servidor local (Pre-4.0)

Binario Windows descargado desde [releases](https://github.com/scrypster/muninndb/releases). Lilith usa la API REST en `http://localhost:8475` cuando `Config/muninn.json` tiene `muninn_enabled: true`.

## Arrancar el servidor

Desde esta carpeta (o con `muninn.exe` en el PATH):

```powershell
.\muninn.exe start
```

El servidor queda en segundo plano. Puertos: **8475** (REST), 8476 (Web UI), 8750 (MCP).

## Primera vez: token (opcional)

Las operaciones de vault pueden requerir Bearer token. Para generar uno:

```powershell
.\muninn.exe init
```

Sigue las preguntas; luego copia el token en `Core/Config/muninn.json` en `muninn_token`.

## Habilitar en Lilith

En `Core/Config/muninn.json` pon `"muninn_enabled": true`. Si no usas token, deja `muninn_token` vacío (algunas instalaciones permiten acceso sin token al vault por defecto).

## Verificar

```powershell
# Health (puede ser 404 según versión; la API sí responde)
Invoke-WebRequest -Uri "http://127.0.0.1:8475/api/activate" -Method POST -Body '{"vault":"default","context":["test"]}' -ContentType "application/json"
```

Si obtienes 401, añade token en la config o ejecuta `muninn init`.
