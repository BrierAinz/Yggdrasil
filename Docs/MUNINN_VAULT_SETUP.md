# Configuración de Vault "docs" en MuninnDB

## Problema
El token actual no está autorizado para el vault `docs`.

## Solución

### Opción 1: Crear vault desde UI de MuninnDB

1. Abrir MuninnDB UI (normalmente http://localhost:3000 o http://localhost:8475)
2. Crear nuevo vault llamado `docs`
3. Copiar el token generado
4. Actualizar `Core/Config/muninn.json`:

```json
{
  "vault_tokens": {
    "docs": "mk_xxxxxxxxxxxxxxxx"
  }
}
```

### Opción 2: Usar token maestro

Si tienes un token maestro (mk_master), puedes crear el vault via API:

```bash
curl -X POST http://127.0.0.1:8475/api/vaults \
  -H "Authorization: Bearer mk_tu_token_maestro" \
  -H "Content-Type: application/json" \
  -d '{"name": "docs"}'
```

### Opción 3: Vault "default"

Si no quieres crear un vault específico, modifica el indexador para usar el vault `default`:

En `Scripts/index_docs_to_muninn.py`:
```python
VAULT_NAME = "default"  # En lugar de "docs"
```

Y en `core/Backend/core/agents/archivero_agent.py`:
```python
self.muninn_docs = MuninnMemory(
    base_path=Path("D:/Proyectos/Yggdrasil/Asgard/Lilith"),
    vault_name="default"  # En lugar de "docs"
)
```

## Verificación

Una vez configurado:

```bash
curl -H "Authorization: Bearer mk_tu_token" \
  "http://127.0.0.1:8475/api/engrams?vault=docs&limit=5"
```

Debería retornar los engramas indexados.
