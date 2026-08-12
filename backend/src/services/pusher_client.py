import os
import pusher

# Initialize Pusher client using environment variables
# Note: Ensure these variables are loaded (e.g., using python-dotenv or Docker env vars)
try:
    pusher_client = pusher.Pusher(
        app_id=os.environ.get("PUSHER_APP_ID", ""),
        key=os.environ.get("PUSHER_APP_KEY", ""),
        secret=os.environ.get("PUSHER_APP_SECRET", ""),
        cluster=os.environ.get("PUSHER_APP_CLUSTER", ""),
        ssl=True,
    )
except Exception as e:
    pusher_client = None
    print(f"Failed to initialize Pusher client: {e}")

def notify_message_sent(message: dict) -> None:
    """
    Broadcasts a chat message via Pusher to the relevant conversation channel.
    
    The 'message' dict must contain the following keys:
    id, conversation_id, sender_id, sender_type, text, created_at
    """
    if not pusher_client:
        print("Pusher client not initialized. Cannot send message.")
        return

    try:
        pusher_client.trigger(
            [f"chat.{message['conversation_id']}", "admin.chat"],
            "message.sent",
            {
                "id": message.get("id"),
                "conversation_id": message.get("conversation_id"),
                "sender_id": message.get("sender_id"),
                "sender_type": message.get("sender_type"),
                "text": message.get("text"),
                "created_at": message.get("created_at"),
            },
        )
    except Exception as e:
        print(f"Error triggering Pusher event: {e}")
