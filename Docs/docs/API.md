# API Reference

Documentacion de los servicios y APIs del ecosistema Yggdrasil.

---

## Servicios

| Servicio | Puerto | Protocolo | Descripcion |
|----------|--------|-----------|-------------|
| API Gateway | 8000 | REST/WS | Gateway principal con WebSocket |
| Model Orchestrator | 8001 | REST | Gestion de modelos LLM |
| Memory Service | 8002 | REST | Memoria vectorial |

---

## API Gateway (Puerto 8000)

Gateway principal del ecosistema. Maneja autenticacion, enrutamiento y WebSocket.

### Endpoints

#### `GET /health`

Health check del gateway.

```bash
curl http://localhost:8000/health
```

Response:
```json
{
    "status": "healthy",
    "service": "api-gateway",
    "version": "1.0.0"
}
```

#### `POST /chat`

Enviar mensaje al agente.

```bash
curl -X POST http://localhost:8000/chat \
  -H "Content-Type: application/json" \
  -d '{"message": "Hola Lilith", "context": "general"}'
```

#### `WS /ws`

WebSocket para comunicacion en tiempo real.

```javascript
const ws = new WebSocket('ws://localhost:8000/ws');
ws.onmessage = (event) => console.log(event.data);
ws.send(JSON.stringify({type: 'chat', message: 'Hola'}));
```

---

## Model Orchestrator (Puerto 8001)

Gestion de modelos LLM y orquestacion de proveedores.

### Endpoints

#### `GET /models`

Listar modelos disponibles.

```bash
curl http://localhost:8001/models
```

Response:
```json
{
    "models": [
        {"id": "mimo-v2.5-pro", "provider": "xiaomi", "status": "active"},
        {"id": "seed-2.0", "provider": "byteplus", "status": "active"}
    ]
}
```

#### `POST /generate`

Generar texto con un modelo especifico.

```bash
curl -X POST http://localhost:8001/generate \
  -H "Content-Type: application/json" \
  -d '{
    "model": "mimo-v2.5-pro",
    "prompt": "Explica que es Yggdrasil",
    "max_tokens": 500
  }'
```

#### `GET /providers`

Listar proveedores configurados y su estado.

```bash
curl http://localhost:8001/providers
```

---

## Memory Service (Puerto 8002)

Servicio de memoria vectorial con SQLite y busqueda semantica.

### Endpoints

#### `GET /memory`

Obtener entradas de memoria.

```bash
curl http://localhost:8002/memory?limit=10
```

#### `POST /memory`

Agregar entrada a la memoria.

```bash
curl -X POST http://localhost:8002/memory \
  -H "Content-Type: application/json" \
  -d '{
    "content": "El CLI de Yggdrasil usa Python y Rich",
    "metadata": {"type": "fact", "source": "docs"}
  }'
```

#### `POST /search`

Busqueda semantica en la memoria.

```bash
curl -X POST http://localhost:8002/search \
  -H "Content-Type: application/json" \
  -d '{
    "query": "como configurar el CLI",
    "limit": 5
  }'
```

Response:
```json
{
    "results": [
        {
            "content": "El CLI se configura con python ygg.py...",
            "score": 0.87,
            "metadata": {"type": "docs"}
        }
    ]
}
```

#### `DELETE /memory`

Borrar toda la memoria (requiere confirmacion).

```bash
curl -X DELETE http://localhost:8002/memory?confirm=true
```

---

## Cloudflare Workers

### Contact Form Worker

El formulario de contacto de brierstudios.com usa un Cloudflare Worker.

**Archivo:** `worker-contact.js`
**Wrangler config:** `wrangler.toml`

```toml
name = "worker-contact"
main = "worker-contact.js"
compatibility_date = "2024-01-01"
```

---

## Iniciar Servicios

```bash
# Todos los servicios
./start_services.sh

# Individual
python -m lilith_api.main        # API Gateway :8000
python -m lilith_orchestrator    # Orchestrator :8001
python -m lilith_memory.server   # Memory :8002
```

---

## Autenticacion

Los servicios usan tokens JWT para autenticacion interna.

### Headers

```http
Authorization: Bearer <token>
Content-Type: application/json
```

### Permisos

| Rol | Acceso |
|-----|--------|
| agent | Lectura/escritura completa |
| user | Lectura + chat |
| readonly | Solo lectura |

---

## Errores

Todos los endpoints retornan errores en formato estandar:

```json
{
    "error": {
        "code": 404,
        "message": "Model not found",
        "details": "The model 'xyz' is not available"
    }
}
```

| Codigo | Significado |
|--------|-------------|
| 200 | Exito |
| 400 | Bad request |
| 401 | No autenticado |
| 403 | Sin permisos |
| 404 | No encontrado |
| 500 | Error interno |
