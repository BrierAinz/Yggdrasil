# 🚀 LILITH Launchers

Scripts para iniciar el ecosistema Lilith.

---

## Scripts Disponibles

| Script | Descripción | Cuándo usar |
|--------|-------------|-------------|
| `LILITH.bat` | **Principal** - Menú completo | Uso normal |
| `LILITH_SIMPLE.bat` | Versión simplificada | Si LILITH.bat falla |
| `LILITH_DEBUG.bat` | Modo debug detallado | Para diagnosticar problemas |

---

## Uso

### Doble click (Modo normal)
```
D:\Proyectos\Yggdrasil\Asgard\Lilith\LILITH.bat
```

### Desde terminal (Para ver errores)
```batch
cd D:\Proyectos\Yggdrasil\Asgard\Lilith
LILITH.bat
```

---

## Solución de Problemas

### "Se abre y se cierra inmediatamente"

**Causa:** El script encuentra un error y cierra la ventana.

**Soluciones:**

1. **Probar LILITH_DEBUG.bat** - Muestra información detallada del error
2. **Probar LILITH_SIMPLE.bat** - Versión más estable sin caracteres especiales
3. **Ejecutar desde CMD** - Abre CMD primero, luego corre el script:
   ```batch
   cd D:\Proyectos\Yggdrasil\Asgard\Lilith
   LILITH.bat
   ```

### "Python no encontrado"

Asegúrate de que Python esté en el PATH:
```batch
python --version
```

Si no funciona, agrega Python al PATH o usa la ruta completa.

### "El menú no responde"

- No uses Ctrl+C en el menú
- Escribe solo el número (1-6) o Q y presiona Enter
- Si presionas Enter sin escribir nada, recargará el menú

---

## Opciones del Menú

```
[1] INICIAR TODO       - Backend + Discord + Telegram + Dashboard
[2] Backend + Dashboard- API y panel web
[3] Solo Backend       - API REST únicamente
[4] Solo Dashboard     - Panel web (requiere Backend externo)
[5] Solo Discord       - Bot de Discord
[6] Solo Telegram      - Bot de Telegram
[Q] Salir              - Cerrar el launcher
```

---

## Qué hace cada opción

### Opción 1: TODO
Abre 4 ventanas de consola:
1. **Backend API** (FastAPI en :8000)
2. **Discord Bot** (si existe Discord\bot.py)
3. **Telegram Bot** (si existe Telegram\bot.py)
4. **Dashboard Web** (React en :3000)

### Opción 2: Backend + Dashboard
Para uso sin bots de chat.

### Opción 3: Solo Backend
Para desarrollo o cuando el Dashboard corre en otra máquina.

### Opción 4-6: Individuales
Para depurar servicios específicos.

---

## URLs después de iniciar

| Servicio | URL |
|----------|-----|
| API Backend | http://localhost:8000 |
| Dashboard | http://localhost:3000 |
| API Docs | http://localhost:8000/docs |
| Health Check | http://localhost:8000/health |

---

## Cerrar servicios

Cada servicio corre en su propia ventana de consola.

Para detener:
1. Ve a la ventana del servicio
2. Presiona `Ctrl+C`
3. Cierra la ventana

**No cierres la ventana del launcher principal** hasta que hayas terminado, o perderás el menú.

---

## Notas

- Los bots de Discord/Telegram se omiten silenciosamente si no existen
- El Dashboard se omite silenciosamente si Node.js no está instalado
- Todas las ventanas se abren en modo "cmd /k" para mantenerlas abiertas
