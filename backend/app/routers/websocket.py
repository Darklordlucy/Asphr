import logging
import json
import datetime
from fastapi import APIRouter, WebSocket, WebSocketDisconnect
from sqlalchemy import select

from app.config import AsyncSessionLocal
from app.services.websocket_manager import websocket_manager
from app.models.db_models import SegmentHazard, RoadSegment

logger = logging.getLogger("app.routers.websocket")
router = APIRouter(tags=["WebSockets"])

@router.websocket("/ws")
async def websocket_endpoint(websocket: WebSocket):
    await websocket_manager.connect(websocket)
    try:
        while True:
            # Wait for messages from the client
            data = await websocket.receive_text()
            try:
                message = json.loads(data)
            except json.JSONDecodeError:
                await websocket_manager.send_personal_message(
                    {"type": "error", "message": "Invalid JSON format"}, websocket
                )
                continue

            msg_type = message.get("type")
            if not msg_type:
                await websocket_manager.send_personal_message(
                    {"type": "error", "message": "Missing 'type' field"}, websocket
                )
                continue

            if msg_type == "ping":
                await websocket_manager.send_personal_message({"type": "pong"}, websocket)

            elif msg_type == "report_hazard":
                # Process a live hazard report from a client
                segment_id = message.get("segment_id")
                hazard_type = message.get("hazard_type", "general")
                hazard_score = message.get("hazard_score", 0.5)
                expires_in_sec = message.get("expires_in_sec", 7200) # Default 2 hours

                if not segment_id:
                    await websocket_manager.send_personal_message(
                        {"type": "error", "message": "Missing 'segment_id'"}, websocket
                    )
                    continue

                try:
                    hazard_score = float(hazard_score)
                    if not (0.0 <= hazard_score <= 1.0):
                        raise ValueError("Hazard score must be between 0.0 and 1.0")
                except ValueError as e:
                    await websocket_manager.send_personal_message(
                        {"type": "error", "message": str(e)}, websocket
                    )
                    continue

                # Store hazard in database
                async with AsyncSessionLocal() as db:
                    # Optional: Verify segment exists
                    segment_check = await db.execute(
                        select(RoadSegment).where(RoadSegment.id == segment_id)
                    )
                    segment = segment_check.scalar_one_or_none()
                    if not segment:
                        await websocket_manager.send_personal_message(
                            {"type": "error", "message": f"Segment ID {segment_id} not found"}, websocket
                        )
                        continue

                    now = datetime.datetime.utcnow()
                    expires_at = now + datetime.timedelta(seconds=expires_in_sec)

                    db_hazard = SegmentHazard(
                        segment_id=segment_id,
                        hazard_score=hazard_score,
                        hazard_type=hazard_type,
                        confidence=1.0,
                        source="live_report",
                        recorded_at=now,
                        expires_at=expires_at
                    )
                    db.add(db_hazard)
                    await db.commit()
                    await db.refresh(db_hazard)

                    logger.info(f"Persisted live hazard report: segment {segment_id}, type {hazard_type}, score {hazard_score}")

                    # Broadcast the alert to all connected clients
                    alert_payload = {
                        "type": "hazard_alert",
                        "data": {
                            "id": db_hazard.id,
                            "segment_id": segment_id,
                            "hazard_type": hazard_type,
                            "hazard_score": hazard_score,
                            "recorded_at": now.isoformat(),
                            "expires_at": expires_at.isoformat()
                        }
                    }
                    await websocket_manager.broadcast(alert_payload)

            else:
                await websocket_manager.send_personal_message(
                    {"type": "error", "message": f"Unknown message type: {msg_type}"}, websocket
                )

    except WebSocketDisconnect:
        websocket_manager.disconnect(websocket)
    except Exception as e:
        logger.error(f"WebSocket error: {e}")
        websocket_manager.disconnect(websocket)
