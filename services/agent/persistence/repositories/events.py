from sqlalchemy.orm import Session
from ..models.event import ApplicationEvent
from .base import BaseRepository

class EventRepository(BaseRepository[ApplicationEvent]):
    def __init__(self, db: Session):
        super().__init__(db, ApplicationEvent)
