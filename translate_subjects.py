import os
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker
from dotenv import load_dotenv

load_dotenv()

# We need the models to perform updates
from app.core.infrastructure.database.models import SubjectModel

translations = {
    "Administrative Law": "Direito Administrativo",
    "Portuguese": "Português",
    "Constitutional Law": "Direito Constitucional",
    "Math and Logic": "Matemática e Raciocínio Lógico",
    "English": "Inglês",
    "Statistics": "Estatística",
    "Operating Systems": "Sistemas Operacionais",
    "Software Engineering": "Engenharia de Software",
    "Systems Development": "Desenvolvimento de Sistemas",
    "Database and BI": "Banco de Dados e BI",
    "IT Management": "Gestão de TI",
    "Computer Networks": "Redes de Computadores",
    "Ethics": "Ética",
    "Economics": "Economia",
    "SFN_SPB": "Sistema Financeiro Nacional"
}

def translate_db(db_url):
    print(f"Translating DB: {db_url}")
    engine = create_engine(db_url)
    Session = sessionmaker(bind=engine)
    session = Session()
    
    subjects = session.query(SubjectModel).all()
    for s in subjects:
        if s.name in translations:
            print(f"Translating {s.name} -> {translations[s.name]}")
            s.name = translations[s.name]
    
    session.commit()
    print("Translation complete.\n")

if __name__ == "__main__":
    local_url = os.getenv("DATABASE_URL")
    prod_url = os.getenv("PROD_DATABASE_URL")
    
    if local_url:
        translate_db(local_url)
        
    if prod_url:
        translate_db(prod_url)
