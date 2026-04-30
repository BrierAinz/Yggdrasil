# SEBAS Protocols

## ComunicaciÃ³n Named Pipe
- Formato: NDJSON (Newline Delimited JSON)
- Estructura: {"type": "command|response|error", "payload": {}, "timestamp": ""}
- I/O: Overlapped/AsÃ­ncrono

## Comandos Soportados
1. @generate_pytorch - Genera cÃ³digo PyTorch
2. @learn - Actualiza knowledge base
3. @execute - Ejecuta comando shell (requiere aprobaciÃ³n)
4. @file_read - Lee archivo
5. @file_write - Escribe archivo (requiere aprobaciÃ³n MEDIUM)

## Niveles de Riesgo
- LOW: Lectura, anÃ¡lisis, generaciÃ³n de cÃ³digo
- MEDIUM: Escritura de archivos, operaciones filesystem
- HIGH: EjecuciÃ³n de cÃ³digo, comandos shell, instalaciÃ³n de paquetes
