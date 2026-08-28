from typing import Optional
from sqlalchemy.orm import Session
from sqlalchemy import func
from app.core.infrastructure.database.models import QuestionModel, SubjectModel

class GetQuestionsUseCase:
    def __init__(self, db: Session):
        self.db = db

    def execute(
        self,
        page: int = 1,
        limit: int = 20,
        subject_id: Optional[int] = None,
        topic: Optional[str] = None,
        source: Optional[str] = None
    ):
        query = self.db.query(QuestionModel)

        if subject_id:
            query = query.filter(QuestionModel.subject_id == subject_id)
        
        if topic:
            query = query.filter(QuestionModel.topic.ilike(f"%{topic}%"))
            
        if source:
            query = query.filter(QuestionModel.source.ilike(f"%{source}%"))

        total_questions = query.count()
        
        # Pagination
        offset = (page - 1) * limit
        questions = query.order_by(QuestionModel.id.asc()).offset(offset).limit(limit).all()

        return {
            "items": questions,
            "total": total_questions,
            "page": page,
            "limit": limit,
            "total_pages": (total_questions + limit - 1) // limit
        }

    def get_filter_options(self):
        """Retorna as opções disponíveis para os filtros (disciplinas, fontes, tópicos únicos)"""
        subjects = self.db.query(SubjectModel).order_by(SubjectModel.name).all()
        
        # Pega as bancas únicas (ex: Cebraspe, FCC, etc)
        sources = [s[0] for s in self.db.query(QuestionModel.source).distinct().filter(QuestionModel.source != "").all()]
        
        # Pega tópicos únicos
        topics = [t[0] for t in self.db.query(QuestionModel.topic).distinct().filter(QuestionModel.topic != "").all()]
        
        return {
            "subjects": subjects,
            "sources": sources,
            "topics": topics
        }
