from motor.motor_asyncio import AsyncIOMotorClient
from beanie import init_beanie
from app.core.config import settings
from app.models.target import Target
from app.models.scan_result import ScanResult
from app.models.scan_log import ScanLog
from app.models.ai_conversation import AiConversation

# Beanie calls database.client.append_metadata() which doesn't exist in all
# motor versions. Add a no-op so startup doesn't crash.
if not hasattr(AsyncIOMotorClient, 'append_metadata'):
    AsyncIOMotorClient.append_metadata = lambda self, *args, **kwargs: None

async def init_db():
    client = AsyncIOMotorClient(settings.MONGODB_URL)
    db = client[settings.DATABASE_NAME]
    await init_beanie(
        database=db,
        document_models=[
            Target,
            ScanResult,
            ScanLog,
            AiConversation,
        ]
    )
