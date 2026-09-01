"""
Script dinâmico para varrer todos os PDFs '*Apostila.pdf' do diretório de estudos
e inseri-los no banco de dados.

Execute: python -m app.core.infrastructure.seeds.seed_all
"""
import logging
import sys
from pathlib import Path

# Adiciona raiz do projeto ao PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.infrastructure.database.session import init_db, SessionLocal
from app.core.infrastructure.database.models import SubjectModel, QuestionModel, OptionModel
from app.core.infrastructure.seeds.pdf_extractor import extract_questions_from_pdf

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

MATERIALS_ROOT = PROJECT_ROOT.parent

def run_seed_all():
    init_db()
    db = SessionLocal()

    logger.info("=== Iniciando Seed Dinâmico de todas as Apostilas ===")
    total_questions = 0

    # Busca todos os PDFs que contêm "Apostila" no nome em qualquer subpasta
    pdf_files = list(MATERIALS_ROOT.rglob("*Apostila.pdf"))
    logger.info(f"Encontrados {len(pdf_files)} arquivos 'Apostila.pdf'.")

    # Mapeamento para evitar recriar subject toda hora
    subject_cache = {}

    for pdf_path in pdf_files:
        # Pula se for _grifada ou _simplificada (já que a regex *Apostila.pdf vai pegar)
        if "_grifada" in pdf_path.name.lower() or "_simplificada" in pdf_path.name.lower():
            continue

        # A estrutura costuma ser Phase X / Day Y / BACEN - NOME DA DISCIPLINA / Aula Z.pdf
        # Vamos procurar a pasta correta da disciplina subindo na árvore
        subject_name = None
        for p in pdf_path.parents:
            if p.name.startswith("BACEN - "):
                subject_name = p.name.replace("BACEN - ", "").strip()
                break
                
        # Fallback de segurança se não achar a pasta "BACEN - "
        if not subject_name:
            logger.warning(f"Ignorando PDF fora da estrutura esperada (sem 'BACEN - '): {pdf_path}")
            continue
        
        # Pega a fase da pasta avô ou bisavô
        phase_name = "Geral"
        for p in pdf_path.parents:
            if "Phase" in p.name:
                phase_name = p.name
                break

        # Traduzir para Português
        SUBJECTS_PT = {
            'Administrative Law': 'Direito Administrativo',
            'Portuguese': 'Português',
            'Constitutional Law': 'Direito Constitucional',
            'Math and Logic': 'Raciocínio Lógico e Matemática',
            'English': 'Inglês',
            'Statistics': 'Estatística',
            'Operating Systems': 'Sistemas Operacionais',
            'Software Engineering': 'Engenharia de Software',
            'Systems Development': 'Desenvolvimento de Sistemas',
            'Database and BI': 'Bancos de Dados e BI',
            'IT Management': 'Governança de TI',
            'Computer Networks': 'Redes de Computadores',
            'Ethics': 'Ética',
            'Economics': 'Economia',
            'SFN_SPB': 'Sistema Financeiro Nacional'
        }
        subject_name = SUBJECTS_PT.get(subject_name, subject_name)

        # Tenta obter do cache ou do banco
        if subject_name not in subject_cache:
            existing = db.query(SubjectModel).filter_by(name=subject_name).first()
            if not existing:
                import re
                slug = re.sub(r'[^a-z0-9]+', '-', subject_name.lower()).strip('-')
                subject_model = SubjectModel(
                    name=subject_name,
                    slug=slug,
                    phase=phase_name,
                    day=1, # Default
                    description=f"Disciplina {subject_name} ({phase_name})"
                )
                db.add(subject_model)
                db.commit()
                db.refresh(subject_model)
                subject_cache[subject_name] = subject_model
                logger.info(f"[NOVA DISCIPLINA] {subject_name}")
            else:
                subject_cache[subject_name] = existing

        subject_model = subject_cache[subject_name]

        logger.info(f"Extraindo de: {pdf_path.name} (Disciplina: {subject_name})")
        
        # Banca padrão
        source_label = "Cebraspe" 

        extracted = extract_questions_from_pdf(pdf_path, source_label)
        subj_questions = 0

        for q_data in extracted:
            # Evita duplicadas pelo início do enunciado
            stmt_prefix = q_data["statement"][:100]
            dup = (
                db.query(QuestionModel)
                .filter(
                    QuestionModel.subject_id == subject_model.id,
                    QuestionModel.statement.like(f"{stmt_prefix}%"),
                )
                .first()
            )
            if dup:
                continue

            opts = q_data.pop("options", [])
            q_model = QuestionModel(
                subject_id=subject_model.id,
                statement=q_data["statement"],
                explanation=q_data.get("explanation", ""),
                source=q_data.get("source", "Cebraspe"),
                topic=q_data.get("topic", ""),
                difficulty="médio", # Default
                year=2024 # Default estimativa material
            )
            db.add(q_model)
            db.flush()

            for opt in opts:
                db.add(OptionModel(
                    question_id=q_model.id,
                    label=opt["label"],
                    text=opt["text"],
                    is_correct=opt["is_correct"],
                ))

            db.commit()
            subj_questions += 1

        logger.info(f"  → Inseridas {subj_questions} questões exclusivas.")
        total_questions += subj_questions

    db.close()
    logger.info(f"=== Seed Dinâmico concluído: {total_questions} NOVAS questões processadas no total ===")

if __name__ == "__main__":
    run_seed_all()
