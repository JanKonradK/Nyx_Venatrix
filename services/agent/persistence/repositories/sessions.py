from sqlalchemy.orm import Session
from ..models.session import ApplicationSession
from .base import BaseRepository

class SessionRepository(BaseRepository[ApplicationSession]):
    def __init__(self, db: Session):
        super().__init__(db, ApplicationSession)

    def get_latest_active(self):
        return self.db.query(ApplicationSession).filter(ApplicationSession.status == 'running').order_by(ApplicationSession.start_datetime.desc()).first()

    def get_active_sessions(self):
        return self.db.query(ApplicationSession).filter(ApplicationSession.status.in_(['running', 'paused'])).all()
