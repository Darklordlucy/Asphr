import logging
from typing import List
from fastapi import WebSocket

logger = logging.getLogger("app.websocket_manager")

class ConnectionManager:
    def __init__(self):
        self.active_connections: List[WebSocket] = []

    async def connect(self, websocket: WebSocket):
        """Accept a connection and track it."""
        await websocket.accept()
        self.active_connections.append(websocket)
        logger.info(f"New WebSocket client connected. Active: {len(self.active_connections)}")

    def disconnect(self, websocket: WebSocket):
        """Untrack a disconnected connection."""
        if websocket in self.active_connections:
            self.active_connections.remove(websocket)
            logger.info(f"WebSocket client disconnected. Active: {len(self.active_connections)}")

    async def send_personal_message(self, message: dict, websocket: WebSocket):
        """Send a JSON message to a specific connection."""
        try:
            await websocket.send_json(message)
        except Exception as e:
            logger.warning(f"Error sending message to client: {e}")
            self.disconnect(websocket)

    async def broadcast(self, message: dict):
        """Broadcast a JSON message to all connected clients."""
        if not self.active_connections:
            return
            
        logger.info(f"Broadcasting message to {len(self.active_connections)} clients: {message.get('type') or message.get('event')}")
        
        # Make a copy of connections to modify list safely during broadcast if any fail
        for connection in list(self.active_connections):
            try:
                await connection.send_json(message)
            except Exception as e:
                logger.warning(f"Failed to send broadcast, disconnecting client: {e}")
                self.disconnect(connection)

# Singleton manager
websocket_manager = ConnectionManager()
