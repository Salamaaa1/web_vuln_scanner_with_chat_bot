from typing import Optional
from beanie import Document
from pydantic import Field
import datetime


class ScanLog(Document):
    """A history entry for every target that gets searched/scanned.

    Stores the lightweight summary (metrics + timing) so the Logs tab can list
    past searches without loading the full raw tool output.
    """
    target_value: str
    target_type: str
    target_id: Optional[str] = None
    status: str = "completed"
    subdomains: int = 0
    endpoints: int = 0
    ports: int = 0
    findings: int = 0
    duration_ms: int = 0
    cached: bool = False
    created_at: datetime.datetime = Field(default_factory=datetime.datetime.utcnow)

    class Settings:
        name = "scan_logs"
