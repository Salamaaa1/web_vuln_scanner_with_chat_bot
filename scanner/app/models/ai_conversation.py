from typing import List, Optional, Dict, Any
from beanie import Document
from pydantic import BaseModel, Field
import datetime


class AiMessage(BaseModel):
    role: str          # "user" | "assistant"
    content: str
    ts: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)


class AiConversation(Document):
    """Persisted AI bilan + follow-up Q&A for ONE vulnerability of ONE scan.

    Keyed by (target_id, vuln_title) so the LLM is only ever billed once per
    vulnerability per scan; reopening the tab replays the stored conversation.
    """
    target_id: str
    vuln_title: str
    severity: Optional[str] = None
    bilan: Dict[str, Any] = {}          # {analysis, remediation, severity}
    messages: List[AiMessage] = []      # follow-up Q&A history
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)
    updated_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    class Settings:
        name = "ai_conversations"
