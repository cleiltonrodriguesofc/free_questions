import os
import sys
import logging
from pathlib import Path

PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.infrastructure.database.session import init_db, SessionLocal
from app.core.infrastructure.database.models import SubjectModel, QuestionModel
from app.core.infrastructure.seeds.pdf_extractor_v2 import extract_questions_from_pdf

from dotenv import load_dotenv
load_dotenv()

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MATERIALS_ROOT = PROJECT_ROOT.parent

def run_organizer(use_prod=False):
    if use_prod:
        from sqlalchemy import create_engine
        from sqlalchemy.orm import sessionmaker
        
        prod_url = os.getenv("PROD_DATABASE_URL")
        if not prod_url:
            logger.error("PROD_DATABASE_URL não configurada no .env")
            return
            
        prod_engine = create_engine(prod_url)
        SessionLocalClass = sessionmaker(autocommit=False, autoflush=False, bind=prod_engine)
        logger.info("=== Usando Banco de Dados ONLINE (Produção) ===")
        db = SessionLocalClass()
    else:
        from app.core.infrastructure.database.session import SessionLocal as LocalSession
        init_db()
        logger.info("=== Usando Banco de Dados LOCAL (SQLite) ===")
        db = LocalSession()

    logger.info("=== Iniciando Organização de Tópicos nas Questões ===")

    pdf_files = list(MATERIALS_ROOT.rglob("*Apostila.pdf"))
    logger.info(f"Encontrados {len(pdf_files)} arquivos 'Apostila.pdf'.")

    total_updated = 0
    total_not_found = 0

    for pdf_path in pdf_files:
        if "_grifada" in pdf_path.name.lower() or "_simplificada" in pdf_path.name.lower():
            continue

        subject_name = None
        for p in pdf_path.parents:
            if p.name.startswith("BACEN - "):
                subject_name = p.name.replace("BACEN - ", "").strip()
                break
                
        if not subject_name:
            continue

        SUBJECTS_PT = {
            'Administrative Law': 'Direito Administrativo',
            'Portuguese': 'Português',
            'Constitutional Law': 'Direito Constitucional',
            'Math and Logic': 'Matemática e Raciocínio Lógico',
            'English': 'Inglês',
            'Statistics': 'Estatística',
            'Operating Systems': 'Sistemas Operacionais',
            'Software Engineering': 'Engenharia de Software',
            'Systems Development': 'Desenvolvimento de Sistemas',
            'Database and BI': 'Banco de Dados e BI',
            'IT Management': 'Gestão de TI',
            'Computer Networks': 'Redes de Computadores',
            'Ethics': 'Ética',
            'Economics': 'Economia',
            'SFN_SPB': 'Sistema Financeiro Nacional'
        }
        subject_name = SUBJECTS_PT.get(subject_name, subject_name)
        
        subject_model = db.query(SubjectModel).filter_by(name=subject_name).first()
        if not subject_model:
            logger.warning(f"Disciplina '{subject_name}' não encontrada no banco. Pulando...")
            continue

        logger.info(f"Processando: {pdf_path.name} (Disciplina: {subject_name})")
        
        extracted = extract_questions_from_pdf(pdf_path, "Cebraspe")
        
        updated_in_this_file = 0
        not_found_in_this_file = 0

        for q_data in extracted:
            topic = q_data.get("topic")
            if not topic:
                continue

            # Para achar a questão no banco, vamos bater os 100 primeiros caracteres do enunciado
            stmt_prefix = q_data["statement"][:100]
            
            # Buscando no banco
            db_question = (
                db.query(QuestionModel)
                .filter(
                    QuestionModel.subject_id == subject_model.id,
                    QuestionModel.statement.like(f"{stmt_prefix}%")
                )
                .first()
            )
            
            if db_question:
                db_question.topic = topic
                updated_in_this_file += 1
            else:
                not_found_in_this_file += 1

        db.commit()
        total_updated += updated_in_this_file
        total_not_found += not_found_in_this_file
        
        logger.info(f"  → Atualizadas {updated_in_this_file} questões. Não encontradas: {not_found_in_this_file}.")

    db.close()
    logger.info("=== Organização de Tópicos Concluída ===")
    logger.info(f"Total de questões atualizadas com temas reais: {total_updated}")
    logger.info(f"Total de questões não encontradas (possíveis duplicatas ou texto alterado): {total_not_found}")

if __name__ == "__main__":
    use_prod = "--prod" in sys.argv
    run_organizer(use_prod)
