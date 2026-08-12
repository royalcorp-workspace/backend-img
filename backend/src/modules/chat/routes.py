from fastapi import APIRouter, Depends, HTTPException
from sqlalchemy.ext.asyncio import AsyncSession
from sqlalchemy import select
from uuid import UUID

from ...infrastructure.database.session import async_session
from ...services.pusher_client import notify_message_sent
from . import models, schemas

router = APIRouter(prefix="/chat", tags=["chat"])

@router.get("/conversations", response_model=list[schemas.ConversationResponse])
async def get_conversations(db: AsyncSession = Depends(async_session)):
    result = await db.execute(select(models.Conversation))
    return result.scalars().all()

@router.get("/{conversation_id}/messages", response_model=list[schemas.MessageResponse])
async def get_messages(conversation_id: UUID, db: AsyncSession = Depends(async_session)):
    result = await db.execute(
        select(models.Message)
        .where(models.Message.conversation_id == conversation_id)
        .order_by(models.Message.created_at.asc())
    )
    return result.scalars().all()

@router.post("/{conversation_id}/messages", response_model=schemas.MessageResponse)
async def send_message(
    conversation_id: UUID, 
    message_in: schemas.MessageCreate, 
    db: AsyncSession = Depends(async_session)
):
    result = await db.execute(select(models.Conversation).where(models.Conversation.id == conversation_id))
    conversation = result.scalars().first()
    
    if not conversation:
        raise HTTPException(status_code=404, detail="Conversation not found")

    new_message = models.Message(
        conversation_id=conversation_id,
        sender_id="customer_123", # TODO: Use real authentication
        sender_type="customer",
        text=message_in.text
    )
    
    db.add(new_message)
    await db.commit()
    await db.refresh(new_message)

    # Broadcast via Pusher (Task 5)
    notify_message_sent({
        "id": str(new_message.id),
        "conversation_id": str(new_message.conversation_id),
        "sender_id": new_message.sender_id,
        "sender_type": new_message.sender_type,
        "text": new_message.text,
        "created_at": new_message.created_at.isoformat(),
    })

    return new_message
