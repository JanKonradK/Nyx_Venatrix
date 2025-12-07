from sqlalchemy.orm import Session
from ..models.application import Application
from .base import BaseRepository

class ApplicationRepository(BaseRepository[Application]):
    def __init__(self, db: Session):
        super().__init__(db, Application)

    def get_by_job_post(self, job_post_id: str):
        return self.db.query(Application).filter(Application.job_post_id == job_post_id).first()

    def get_queued(self, limit: int = 10):
        return self.db.query(Application).filter(Application.application_status == 'queued').limit(limit).all()
