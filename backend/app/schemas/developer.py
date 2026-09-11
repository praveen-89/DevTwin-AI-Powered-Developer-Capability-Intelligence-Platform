from pydantic import BaseModel, ConfigDict
import uuid
from datetime import datetime


class DeveloperResponse(BaseModel):
    """
    Response schema for the Developer identity.
    Maps to the ORM model safely without exposing database internals
    or relying on client-supplied data.
    """
    id: uuid.UUID
    auth_user_id: uuid.UUID
    created_at: datetime
    updated_at: datetime

    model_config = ConfigDict(from_attributes=True)
