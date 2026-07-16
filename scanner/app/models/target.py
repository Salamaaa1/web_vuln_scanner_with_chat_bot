from enum import Enum
from typing import Optional
from beanie import Document
from pydantic import Field
import datetime

class TargetType(str, Enum):
    DNS = "DNS"
    IP = "IP"
    CIDR = "CIDR"
    URL = "URL"

class Target(Document):
    value: str
    targetType: str
    created_at: datetime.datetime = Field(default_factory=lambda: datetime.datetime.now(datetime.timezone.utc))

    class Settings:
        name = "targets"
