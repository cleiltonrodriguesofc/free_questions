"""
Script de seed: popula o banco com disciplinas e questões extraídas dos PDFs.
Execute: python -m app.core.infrastructure.seeds.seed
"""
import logging
import sys
from pathlib import Path

# Adiciona raiz do projeto ao PYTHONPATH
PROJECT_ROOT = Path(__file__).resolve().parents[5]
sys.path.insert(0, str(PROJECT_ROOT))

from app.core.infrastructure.database.session import init_db, SessionLocal
from app.core.infrastructure.database.models import SubjectModel, QuestionModel, OptionModel
from app.core.infrastructure.seeds.pdf_extractor import extract_questions_from_pdf

logging.basicConfig(level=logging.INFO, format="%(levelname)s %(message)s")
logger = logging.getLogger(__name__)

# ─── Mapeamento de disciplinas ────────────────────────────────────────────────
# Cada entrada: (slug, nome, fase, dia, lista de PDFs relativos à raiz dos materiais)

MATERIALS_ROOT = PROJECT_ROOT  # /media/cleilton/CLEILTON/ESTUDOS/BACEN_study

SUBJECTS = [
    {
        "slug": "direito-administrativo",
        "name": "Direito Administrativo",
        "phase": "Phase 1 - Foundation",
        "day": 1,
        "description": "Princípios, atos administrativos, licitações, contratos, servidores públicos.",
        "pdfs": [
            "Phase 1 - Foundation - 4_weeks/Day 1/BACEN - Administrative Law/Aula 01_Apostila.pdf",
            "Phase 1 - Foundation - 4_weeks/Day 1/BACEN - Administrative Law/Aula 02_Apostila.pdf",
            "Phase 1 - Foundation - 4_weeks/Day 1/BACEN - Administrative Law/Aula 03_Apostila.pdf",
            "Phase 1 - Foundation - 4_weeks/Day 1/BACEN - Administrative Law/Aula 04_Apostila.pdf",
            "Phase 1 - Foundation - 4_weeks/Day 1/BACEN - Administrative Law/Aula 05_Apostila.pdf",
            "Phase 1 - Foundation - 4_weeks/Day 1/BACEN - Administrative Law/Aula 06_Apostila.pdf",
            "Phase 1 - Foundation - 4_weeks/Day 1/BACEN - Administrative Law/Aula 07_Apostila.pdf",
            "Phase 1 - Foundation - 4_weeks/Day 1/BACEN - Administrative Law/Aula 08_Apostila.pdf",
            "Phase 1 - Foundation - 4_weeks/Day 1/BACEN - Administrative Law/Aula 09_Apostila.pdf",
            "Phase 1 - Foundation - 4_weeks/Day 1/BACEN - Administrative Law/Aula 10_Apostila.pdf",
        ],
    },
    {
        "slug": "lingua-portuguesa",
        "name": "Língua Portuguesa",
        "phase": "Phase 1 - Foundation",
        "day": 1,
        "description": "Interpretação de texto, sintaxe, coesão e coerência textual.",
        "pdfs": [
            "Phase 1 - Foundation - 4_weeks/Day 1/BACEN - Portuguese/Aula 01_Apostila.pdf",
            "Phase 1 - Foundation - 4_weeks/Day 1/BACEN - Portuguese/Aula 02_Apostila.pdf",
            "Phase 1 - Foundation - 4_weeks/Day 1/BACEN - Portuguese/Aula 03_Apostila.pdf",
            "Phase 1 - Foundation - 4_weeks/Day 1/BACEN - Portuguese/Aula 04_Apostila.pdf",
            "Phase 1 - Foundation - 4_weeks/Day 1/BACEN - Portuguese/Aula 05_Apostila.pdf",
        ],
    },
    {
        "slug": "direito-constitucional",
        "name": "Direito Constitucional",
        "phase": "Phase 1 - Foundation",
        "day": 2,
        "description": "Administração pública, direitos fundamentais, controle constitucional.",
        "pdfs": [
            "Phase 1 - Foundation - 4_weeks/Day 2/BACEN - Constitutional Law/Aula 01_Apostila.pdf",
        ],
    },
    {
        "slug": "matematica-logica",
        "name": "Matemática e Raciocínio Lógico",
        "phase": "Phase 1 - Foundation",
        "day": 2,
        "description": "Proposições lógicas, combinatória, probabilidade, análise numérica.",
        "pdfs": [
            "Phase 1 - Foundation - 4_weeks/Day 2/BACEN - Math and Logic/Aula 01_Apostila.pdf",
        ],
    },
    {
        "slug": "engenharia-software",
        "name": "Engenharia de Software",
        "phase": "Phase 2 - IT Pipeline",
        "day": 1,
        "description": "Metodologias ágeis, UML, testes de software, qualidade.",
        "pdfs": [
            "Phase 2 - IT Pipeline - 12_weeks/Day 1/BACEN - Software Engineering/Aula 01_Apostila.pdf",
            "Phase 2 - IT Pipeline - 12_weeks/Day 1/BACEN - Software Engineering/Aula 02_Apostila.pdf",
            "Phase 2 - IT Pipeline - 12_weeks/Day 1/BACEN - Software Engineering/Aula 03_Apostila.pdf",
            "Phase 2 - IT Pipeline - 12_weeks/Day 1/BACEN - Software Engineering/Aula 04_Apostila.pdf",
            "Phase 2 - IT Pipeline - 12_weeks/Day 1/BACEN - Software Engineering/Aula 05_Apostila.pdf",
        ],
    },
    {
        "slug": "desenvolvimento-sistemas",
        "name": "Desenvolvimento de Sistemas",
        "phase": "Phase 2 - IT Pipeline",
        "day": 1,
        "description": "Clean Code, arquitetura, padrões de projeto, APIs.",
        "pdfs": [
            "Phase 2 - IT Pipeline - 12_weeks/Day 1/BACEN - Systems Development/Aula 01_Apostila.pdf",
            "Phase 2 - IT Pipeline - 12_weeks/Day 1/BACEN - Systems Development/Aula 02_Apostila.pdf",
            "Phase 2 - IT Pipeline - 12_weeks/Day 1/BACEN - Systems Development/Aula 03_Apostila.pdf",
        ],
    },
    {
        "slug": "sistemas-operacionais",
        "name": "Sistemas Operacionais e Cloud",
        "phase": "Phase 2 - IT Pipeline",
        "day": 1,
        "description": "Virtualização, cloud computing, Docker, processos e memória.",
        "pdfs": [
            "Phase 2 - IT Pipeline - 12_weeks/Day 1/BACEN - Operating Systems/Aula 01_Apostila.pdf",
            "Phase 2 - IT Pipeline - 12_weeks/Day 1/BACEN - Operating Systems/Aula 02_Apostila.pdf",
        ],
    },
    {
        "slug": "banco-de-dados",
        "name": "Banco de Dados e Business Intelligence",
        "phase": "Phase 2 - IT Pipeline",
        "day": 2,
        "description": "Modelagem relacional, SQL, Data Warehousing, ETL.",
        "pdfs": [
            "Phase 2 - IT Pipeline - 12_weeks/Day 2/BACEN - Database and BI/Aula 01_Apostila.pdf",
            "Phase 2 - IT Pipeline - 12_weeks/Day 2/BACEN - Database and BI/Aula 02_Apostila.pdf",
            "Phase 2 - IT Pipeline - 12_weeks/Day 2/BACEN - Database and BI/Aula 03_Apostila.pdf",
        ],
    },
    {
        "slug": "gestao-ti",
        "name": "Gestão de TI (COBIT/ITIL)",
        "phase": "Phase 2 - IT Pipeline",
        "day": 2,
        "description": "Frameworks COBIT, ITIL, governança de TI.",
        "pdfs": [
            "Phase 2 - IT Pipeline - 12_weeks/Day 2/BACEN - IT Management/Aula 01_Apostila.pdf",
        ],
    },
    {
        "slug": "redes-computadores",
        "name": "Redes de Computadores",
        "phase": "Phase 2 - IT Pipeline",
        "day": 3,
        "description": "Protocolos de rede, arquiteturas, roteamento, topologias.",
        "pdfs": [
            "Phase 2 - IT Pipeline - 12_weeks/Day 3/BACEN - Computer Networks/Aula 01_Apostila.pdf",
            "Phase 2 - IT Pipeline - 12_weeks/Day 3/BACEN - Computer Networks/Aula 02_Apostila.pdf",
        ],
    },
    {
        "slug": "seguranca-informacao",
        "name": "Segurança da Informação",
        "phase": "Phase 2 - IT Pipeline",
        "day": 3,
        "description": "ISO 27001/27002, NIST, criptografia, gestão de riscos.",
        "pdfs": [
            "Phase 2 - IT Pipeline - 12_weeks/Day 3/BACEN - Information Security/Aula 01_Apostila.pdf",
            "Phase 2 - IT Pipeline - 12_weeks/Day 3/BACEN - Information Security/Aula 02_Apostila.pdf",
        ],
    },
    {
        "slug": "etica-servico-publico",
        "name": "Ética no Serviço Público",
        "phase": "Phase 3 - Domain Backlog",
        "day": 1,
        "description": "Ética, conduta funcional e responsabilidade do servidor público.",
        "pdfs": [
            "Phase 3 - Domain Backlog/Day 1/BACEN - Ethics/Aula 01_Apostila.pdf",
            "Phase 3 - Domain Backlog/Day 1/BACEN - Ethics/Aula 02_Apostila.pdf",
        ],
    },
]


def run_seed():
    init_db()
    db = SessionLocal()

    logger.info("=== Iniciando seed do banco de dados ===")
    total_questions = 0

    for subj_data in SUBJECTS:
        # Criar ou recuperar disciplina
        existing = db.query(SubjectModel).filter_by(slug=subj_data["slug"]).first()
        if existing:
            subject_model = existing
            logger.info(f"Disciplina já existe: {subj_data['name']}")
        else:
            subject_model = SubjectModel(
                name=subj_data["name"],
                slug=subj_data["slug"],
                phase=subj_data["phase"],
                day=subj_data["day"],
                description=subj_data["description"],
            )
            db.add(subject_model)
            db.commit()
            db.refresh(subject_model)
            logger.info(f"Criada disciplina: {subj_data['name']}")

        # Extrair questões dos PDFs
        subj_questions = 0
        for pdf_rel in subj_data["pdfs"]:
            pdf_path = MATERIALS_ROOT / pdf_rel
            if not pdf_path.exists():
                logger.warning(f"  PDF não encontrado: {pdf_path}")
                continue

            source_label = f"BACEN - {subj_data['name']}"
            extracted = extract_questions_from_pdf(pdf_path, source_label)

            for q_data in extracted:
                # evitar duplicatas simples por similaridade de enunciado (primeiros 100 chars)
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
                    source=q_data.get("source", ""),
                    year=q_data.get("year"),
                    topic=q_data.get("topic", ""),
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

        logger.info(f"  → {subj_questions} questões inseridas para {subj_data['name']}")
        total_questions += subj_questions

    db.close()
    logger.info(f"=== Seed concluído: {total_questions} questões no total ===")


if __name__ == "__main__":
    run_seed()
