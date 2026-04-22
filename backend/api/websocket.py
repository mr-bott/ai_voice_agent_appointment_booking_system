"""
WebSocket handler for real-time audio and text communication.
This module manages the connection between the frontend and the VoiceOrchestrator.
"""
import json
import logging
import traceback
import uuid

from fastapi import APIRouter, Depends, WebSocket, WebSocketDisconnect
from sqlalchemy.ext.asyncio import AsyncSession

from ..agent.orchestrator import VoiceOrchestrator
from ..database.connection import get_db
from ..memory.session import SessionMemory

router = APIRouter()
logger = logging.getLogger(__name__)


@router.websocket("/ws/audio")
async def audio_websocket(websocket: WebSocket, db: AsyncSession = Depends(get_db)):
    await websocket.accept()

    session_id = str(uuid.uuid4())
    session_memory = SessionMemory(session_id)
    orchestrator = VoiceOrchestrator(websocket=websocket, session_memory=session_memory, db_session=db)

    try:
        await orchestrator.start()

        while True:
            message = await websocket.receive()

            if message.get("type") == "websocket.disconnect":
                break

            if message.get("bytes"):
                await orchestrator.process_audio(message["bytes"])
                continue

            if message.get("text"):
                try:
                    data = json.loads(message["text"])
                except json.JSONDecodeError:
                    await websocket.send_json({"type": "warning", "message": "Invalid control message received."})
                    continue

                msg_type = data.get("type")
                if msg_type == "interrupt":
                    orchestrator.barge_in_flag = True
                    await websocket.send_json({"type": "interrupt_tts"})
                elif msg_type == "ping":
                    await websocket.send_json({"type": "pong"})
                elif msg_type == "user_text":
                    await orchestrator.process_text(data.get("text", ""))
                else:
                    await websocket.send_json(
                        {
                            "type": "warning",
                            "message": f"Unknown message type: {msg_type}",
                        }
                    )

    except WebSocketDisconnect:
        logger.info("WebSocket disconnected for session %s", session_id)
    except Exception as exc:
        logger.error("Fatal WebSocket error for session %s: %s", session_id, exc)
        traceback.print_exc()
        await websocket.send_json({"type": "error", "message": str(exc)})
    finally:
        await orchestrator.stop()
