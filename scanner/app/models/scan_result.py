from typing import List, Optional, Dict, Any
from beanie import Document
from pydantic import BaseModel, Field
import datetime

class Vulnerability(BaseModel):
    title: str
    description: Optional[str] = None
    severity: Optional[str] = None
    raw_data: Optional[Dict[str, Any]] = None

class ScanResult(Document):
    toolName: str
    rawJson: Dict[str, Any] = {}
    status: str = "pending"
    vulnerabilities: List[Vulnerability] = []
    target_id: Optional[str] = None
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))

    class Settings:
        name = "scan_results"
