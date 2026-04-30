"""
Dashboard WebSocket API Endpoint

Endpoint WebSocket para métricas live del dashboard.
Conecta el DashboardWebSocketManager con los clientes frontend.

v4.2.4: Dashboard Live Metrics
"""
import logging

from fastapi import APIRouter, WebSocket, WebSocketDisconnect

logger = logging.getLogger(__name__)

router = APIRouter(prefix="/ws", tags=["websocket"])


@router.websocket("/dashboard")
async def dashboard_websocket(websocket: WebSocket):
    """
    WebSocket endpoint para métricas live del dashboard.

    Envía métricas del sistema cada 2 segundos:
    - CPU y memoria
    - Uso de disco
    - Health checks
    - Sesiones activas
    - Actividad de agentes

    Example:
        const ws = new WebSocket('ws://localhost:8000/ws/dashboard')
        ws.onmessage = (event) => {
            const data = JSON.parse(event.data)
            // data.type = 'dashboard_metrics' | 'dashboard_history'
            // data.data = { cpu_percent, memory_percent, ... }
        }
    """
    try:
        # Aceptar conexión
        await websocket.accept()
        logger.info(f"Dashboard WebSocket connected: {websocket.client}")

        # Obtener manager
        from src.core.dashboard_websocket import get_dashboard_manager

        manager = get_dashboard_manager()

        # Suscribir cliente
        manager.subscribe(
            websocket,
            client_info={
                "host": websocket.client.host if websocket.client else None,
                "port": websocket.client.port if websocket.client else None,
            },
        )

        # Mantener conexión abierta y escuchar mensajes del cliente
        while True:
            try:
                # Esperar mensajes del cliente (ping/pong, comandos)
                data = await websocket.receive_json()

                # Manejar comandos del cliente
                if data.get("type") == "ping":
                    await websocket.send_json(
                        {"type": "pong", "timestamp": data.get("timestamp")}
                    )

                elif data.get("type") == "get_stats":
                    stats = manager.get_stats()
                    await websocket.send_json({"type": "manager_stats", "data": stats})

                elif data.get("type") == "toggle_live":
                    # El cliente puede solicitar pausar/reanudar updates
                    pass

            except WebSocketDisconnect:
                break
            except Exception as e:
                logger.debug(f"Dashboard WebSocket message error: {e}")
                break

    except WebSocketDisconnect:
        logger.info("Dashboard WebSocket disconnected")
    except Exception as e:
        logger.error(f"Dashboard WebSocket error: {e}")
    finally:
        # Desuscribir cliente
        try:
            from src.core.dashboard_websocket import get_dashboard_manager

            manager = get_dashboard_manager()
            manager.unsubscribe(websocket)
        except:
            pass

        try:
            await websocket.close()
        except:
            pass

        logger.info("Dashboard WebSocket connection closed")
