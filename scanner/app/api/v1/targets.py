from fastapi import APIRouter, HTTPException
from app.models.target import Target
from pydantic import BaseModel
from beanie import PydanticObjectId

router = APIRouter()

class TargetCreate(BaseModel):
    value: str
    targetType: str

@router.post("/")
async def create_target(data: TargetCreate):
    target = Target(value=data.value, targetType=data.targetType)
    await target.insert()
    return {"id": str(target.id), "value": target.value, "targetType": target.targetType}

@router.get("/{target_id}")
async def get_target(target_id: str):
    try:
        target = await Target.get(PydanticObjectId(target_id))
    except Exception:
        raise HTTPException(status_code=404, detail="Target not found")
    if not target:
        raise HTTPException(status_code=404, detail="Target not found")
    return {"id": str(target.id), "value": target.value, "targetType": target.targetType}
