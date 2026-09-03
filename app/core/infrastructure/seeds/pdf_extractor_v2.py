"""
pdf_extractor_v2.py — Extrator de questões v2 para apostilas Estratégia Concursos.

Padrão dos PDFs (3 seções fixas):
  1. TEORIA + QUESTÕES COMENTADAS
     - questão + alternativas + Comentários: ... + Gabarito: Letra X. (inline)
  2. LISTA DAS QUESTÕES (sem comentários, para praticar)
     - cabeçalho de tópico + questões numeradas sem gabarito inline
  3. GABARITO (tabela no final)
     - "1. A  2. C  3. E ..." ou grade por tópico "GABARITO MULTIBANCAS / Tópico / LETRA A ..."
"""

import re
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)


# ─── Regex patterns ───────────────────────────────────────────────────────────

# Alternativas A) ... E)
OPTION_RE = re.compile(r"^\s*[([]?\s*([AaBbCcDdEe])\s*[)\].]\s*(.+)", re.DOTALL)

# Gabarito inline (questões comentadas): "Gabarito: Letra B." / "Gabarito: CERTO."
# Também: Gabarito: "d" / Gabarito: 'A'
GABA_INLINE_LETRA_RE = re.compile(
    r"gabarito\s*[:–\-]\s*(?:letra\s+)?[\"']?([a-eA-E])[\"']?[.\s,)”]",
    re.IGNORECASE,
)
GABA_INLINE_CE_RE = re.compile(
    r"gabarito\s*[:–\-]\s*[\"']?(certo|errado|verdadeiro|falso)[\"']?[.\s]?",
    re.IGNORECASE,
)

# Gabarito tabular no final: "1. A" "2. CERTO" "1. LETRA A"
GABA_TABLE_NUM_RE = re.compile(
    r"(\d{1,3})\s*[.\-)\s]\s*(?:letra\s+)?([a-eA-ECERTO|ERRADO]{1,6})\b",
    re.IGNORECASE,
)
GABA_TABLE_LETRAS_RE = re.compile(
    r"(\d{1,3})\s*[.)\-]\s+([A-E])\b"
)

# Início de bloco de comentário dentro de questão comentada
COMMENT_START_RE = re.compile(
    r"^\s*(?:comentário|comentario|justificativa|resolução|resolucao|explicação"
    r"|comentários?)\s*[:–\-]?\s*",
    re.IGNORECASE,
)

# Início de seção de gabarito (tabela final)
GABA_SECTION_RE = re.compile(
    r"^\s*(?:gabarito|gabaritos|gabarito\s+multibancas?|g\s*[-–]\s*m)\s*$",
    re.IGNORECASE,
)

# Questão numerada (lista de questões ou questão comentada)
QUESTION_NUM_RE = re.compile(
    r"^(?P<num>\d{1,3})\s*[.)]\s*(?=[A-ZÁÀÂÃÉÊÍÓÔÕÚ\(])",
    re.MULTILINE,
)

# Cabeçalho de tópico na seção de lista
# Linhas que parecem título de seção (sem ser número de questão, alternativa, rodapé)
TOPIC_HEADER_RE = re.compile(
    r"^(?![\d]+\s*[.)]\s)(?!(?:[a-e]\s*[).])\s)(?!gabarito)(?!comentár)(?!www\.|https?://)([A-ZÁÀÂÃÉÊÍÓÔÕÚ][^:]{5,80})$",
    re.IGNORECASE,
)

# Rodapés e cabeçalhos de página a remover
FOOTER_LINE_RE = re.compile(
    r"""(?x)
    ^\s*\d+\s*$                    # Número isolado
    | ^\s*www\.\S+                 # URL www
    | ^\s*https?://\S+             # URL http
    | ©.*direitos
    | todos\s+os\s+direitos
    | ^\s*\d+\s*/\s*\d+\s*$       # X / Y
    | material\s+de\s+apoio
    | estrategia\s+concursos
    | by\s+@\w+
    | t\.me/\w+
    """,
    re.IGNORECASE,
)

# Marcadores de C/E no enunciado
CE_INDICATOR_RE = re.compile(
    r"julgue\s+(?:o\s+)?(?:item|os\s+itens|a\s+afirmativa|o\s+seguinte)"
    r"|assinale\s+(?:certo|errado)"
    r"|(?:é\s+)?(?:certo|errado)\s+(?:afirmar|dizer|que)"
    r"|\(\s*(?:certo|errado)\s*\)",
    re.IGNORECASE,
)

# Cabeçalhos das bancas por tópico na seção de lista (ex: "FGV", "CESPE", "Outras Bancas")
BANCA_HEADER_RE = re.compile(
    r"^\s*(?:FGV|CESPE|CEBRASPE|FCC|VUNESP|CESGRANRIO|IADES|IBFC|QUADRIX|AOCP"
    r"|Outras\s+bancas?|Multibancas?|CESPE/CEBRASPE)\s*$",
    re.IGNORECASE,
)

# Cabeçalho de banca no enunciado: "(FGV / TJ-BA / 2015)", "(STN/Analista/2020)"
QUESTION_BANCA_HEADER_RE = re.compile(
    r"^\s*\(([A-Z]{2,}[^)]{3,60}(?:\d{4}|Analista|Auditor|Técnico)[^)]{0,40})\)",
    re.IGNORECASE,
)

# Tópico: linha totalmente em maiúsculo ou título de seção clara (sem rodapé)
SECTION_TOPIC_RE = re.compile(
    r"^[A-ZÁÀÂÃÉÊÍÓÔÕÚ][A-ZÁÀÂÃÉÊÍÓÔÕÚa-záàâãéêíóôõú\s\-–()]{8,70}$"
)


def clean_text(text: str) -> str:
    """Adiciona espaço após pontuação colada com letra."""
    if not text:
        return text
    text = re.sub(r"(?<=[a-zA-ZÀ-ú])([,.;:])(?=[a-zA-ZÀ-ú])", r"\1 ", text)
    return text.strip()


def extract_questions_from_pdf(pdf_path: str | Path, source_label: str = "") -> list[dict]:
    """
    Extrai questões de um PDF apostila Estratégia Concursos.
    Retorna lista de dicts:
      { statement, options:[{label, text, is_correct}], explanation, source, year, topic }
    """
    try:
        import pdfplumber
    except ImportError:
        logger.error("pdfplumber não instalado. pip install pdfplumber")
        return []

    path = Path(pdf_path)
    if not path.exists():
        logger.warning(f"PDF não encontrado: {path}")
        return []

    raw_pages = _extract_pages(path)
    if not raw_pages:
        logger.warning(f"PDF sem texto extraível: {path}")
        return []

    full_text = "\n".join(raw_pages)

    # Determinar o Tema Principal da Aula
    lesson_topic = extract_lesson_topic(path)
    
    # 1. Extrair tabela de gabarito do final do PDF
    gabarito_map = _extract_gabarito_table(full_text)

    # 2. Extrair questões comentadas (com gabarito inline)
    commented = _extract_commented_questions(full_text, source_label, lesson_topic)

    # 3. Extrair lista de questões (com tópicos e gabarito via tabela)
    listed = _extract_listed_questions(full_text, source_label, gabarito_map, lesson_topic)

    # Deduplicar: preferir comentadas (têm explicação)
    all_questions = _deduplicate(commented, listed)

    logger.info(f"  → {len(all_questions)} questões ({len(commented)} comentadas + {len(listed)} da lista) de {path.name} (Tema: {lesson_topic})")
    return all_questions


def _extract_pages(path: Path) -> list[str]:
    """Extrai texto de cada página, removendo rodapés."""
    import pdfplumber
    pages = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            # Crop 10% topo/base para remover cabeçalho/rodapé de página
            h = float(page.height)
            w = float(page.width)
            bbox = (0, h * 0.10, w, h * 0.90)
            cropped = page.crop(bbox)
            text = cropped.extract_text(x_tolerance=2.0, y_tolerance=3.0) or ""
            if text:
                pages.append(_strip_footer_lines(text))
    return pages


def _strip_footer_lines(text: str) -> str:
    lines = []
    for line in text.split("\n"):
        if not FOOTER_LINE_RE.search(line.strip()):
            lines.append(line)
    return "\n".join(lines)


# ─── Gabarito tabular ────────────────────────────────────────────────────────

def _extract_gabarito_table(text: str) -> dict[int, str]:
    """Extrai {número: letra_correta} da seção de GABARITO no final do PDF."""
    result: dict[int, str] = {}

    # Encontrar seção GABARITO
    lines = text.split("\n")
    in_gab = False
    gab_lines: list[str] = []

    for line in lines:
        stripped = line.strip()
        if GABA_SECTION_RE.match(stripped):
            in_gab = True
            continue
        if in_gab:
            # Parar se entrar em nova seção substancial
            if len(stripped) > 60 and not re.search(r"\d+\s*[.)\-]", stripped):
                break
            gab_lines.append(stripped)

    gab_text = " ".join(gab_lines)

    # Padrão "1. A" ou "1 A" ou "1. LETRA A" ou "1. CERTO"
    for m in re.finditer(
        r"(\d{1,3})\s*[.)\-\s]\s*(?:letra\s+)?([A-E]|certo|errado|verdadeiro|falso)\b",
        gab_text,
        re.IGNORECASE,
    ):
        num = int(m.group(1))
        val = m.group(2).upper()
        if val in ("CERTO", "VERDADEIRO"):
            val = "C"
        elif val in ("ERRADO", "FALSO"):
            val = "E"
        if num not in result:  # primeiro encontrado prevalece
            result[num] = val

    # Fallback: varrer as últimas 4000 chars do texto inteiro
    if not result:
        for m in GABA_TABLE_LETRAS_RE.finditer(text[-4000:]):
            num = int(m.group(1))
            if num not in result:
                result[num] = m.group(2).upper()

    return result


# ─── Questões Comentadas ─────────────────────────────────────────────────────

def _extract_commented_questions(text: str, source: str, lesson_topic: str) -> list[dict]:
    """
    Extrai questões da seção de questões comentadas.
    Suporta dois padrões:
      1. Numerado: "1. Enunciado... a) ... Comentários: ... Gabarito: Letra X."
      2. Por banca: "(FGV/TJ-BA/2015) Enunciado... a) ... Comentários: ... Gabarito: Letra X."
    """
    questions: list[dict] = []
    current_topic = lesson_topic

    # Estratégia 1: divisão por questão numerada
    blocks = _split_into_blocks(text)

    # Estratégia 2: divisão por cabeçalho de banca (para PDFs sem numeração)
    # Usada se o padrão numerado gerar menos de 3 questões comentadas
    numbered_commented: list[dict] = []
    for num, block in blocks:
        has_comment = bool(COMMENT_START_RE.search(block))
        has_inline_gab = bool(GABA_INLINE_LETRA_RE.search(block) or GABA_INLINE_CE_RE.search(block))
        if not (has_comment or has_inline_gab):
            continue
        # Detectar tópico
        first_line = block.split("\n")[0].strip()
        if _is_topic_candidate(first_line):
            current_topic = first_line[:100]
        q = _parse_commented_block(block, source, current_topic)
        if q:
            numbered_commented.append(q)

    if len(numbered_commented) >= 3:
        return numbered_commented

    # Fallback: divisão por cabeçalho de banca entre parênteses
    banca_questions = _extract_by_banca_blocks(text, source, lesson_topic)
    return banca_questions if banca_questions else numbered_commented


def _is_topic_candidate(line: str) -> bool:
    """Verifica se a linha parece ser um cabeçalho de tópico."""
    s = line.strip()
    if len(s) < 8 or len(s) > 100:
        return False
    if re.match(r'^\d', s):  # começa com número → não é tópico
        return False
    if BANCA_HEADER_RE.match(s):
        return False
    if FOOTER_LINE_RE.search(s):
        return False
    if QUESTION_BANCA_HEADER_RE.match(s):  # (BANCA/ANO) → não é tópico
        return False
    if re.search(r'comentário|gabarito|justificativa', s, re.IGNORECASE):
        return False
    # Tem pelo menos uma letra maiúscula no início
    return bool(re.match(r'[A-ZÁÀÂÃÉÊÍÓÔÕÚ]', s))


def _extract_by_banca_blocks(text: str, source: str, lesson_topic: str) -> list[dict]:
    """
    Extrai questões usando cabeçalhos de banca como delimitador.
    Padrão: "(BANCA/ÓRGÃO/ANO) Enunciado..."
    """
    questions: list[dict] = []
    current_topic = lesson_topic

    # Dividir texto em blocos por cabeçalho (BANCA/...)
    # Padrões: (FGV/TJ-BA/2015), (STN/Analista...), (2016/FCC/ARSETE/Economista)
    split_re = re.compile(
        r'(?=^\s*\(?(?:\d{4}[/\-])?(?:[A-Z]{2,}[^)]{2,80}(?:\d{4}|Analista|Auditor|Técnico|Economista|Administrador|Servidor|Especialista)[^)]{0,40})\)?)',
        re.MULTILINE | re.IGNORECASE,
    )
    parts = split_re.split(text)

    for part in parts:
        part = part.strip()
        if not part or len(part) < 50:
            continue

        # Precisa ter alternativas e comentário/gabarito inline
        has_options = bool(OPTION_RE.search(part))
        has_comment = bool(COMMENT_START_RE.search(part))
        has_inline_gab = bool(GABA_INLINE_LETRA_RE.search(part) or GABA_INLINE_CE_RE.search(part))

        if not has_options or not (has_comment or has_inline_gab):
            # Pode ser cabeçalho de tópico sem questão
            first_line = part.split("\n")[0].strip()
            if _is_topic_candidate(first_line) and not QUESTION_BANCA_HEADER_RE.match(first_line):
                current_topic = first_line[:100]
            continue

        q = _parse_commented_block(part, source, current_topic)
        if q:
            questions.append(q)

    return questions


def _detect_first_topic(text: str) -> str:
    for line in text.split("\n")[:80]:
        s = line.strip()
        if _is_topic_candidate(s) and not QUESTION_BANCA_HEADER_RE.match(s):
            # Verificar se parece um título real (tem palavra com >=4 letras)
            if re.search(r'[A-Za-záàâãéêíóôõú]{4,}', s):
                return s[:100]
    return ""


def _split_into_blocks(text: str) -> list[tuple[Optional[int], str]]:
    """Divide texto em blocos por questão numerada '1.' '2.' etc."""
    pattern = re.compile(
        r"(?:^|\n)\s*(\d{1,3})\s*[.)]\s*(?=[A-ZÁÀÂÃÉÊÍÓÔÕÚ\(])",
        re.MULTILINE,
    )
    matches = list(pattern.finditer(text))
    if not matches:
        return []

    blocks = []
    for i, m in enumerate(matches):
        start = m.start()
        end = matches[i + 1].start() if i + 1 < len(matches) else len(text)
        num = int(m.group(1))
        block = text[start:end].strip()
        blocks.append((num, block))
    return blocks


def _parse_commented_block(block: str, source: str, topic: str) -> Optional[dict]:
    """Extrai questão de um bloco comentado (com gabarito inline)."""
    lines = block.split("\n")
    statement_lines: list[str] = []
    options: list[dict] = []
    current_opt_label: Optional[str] = None
    current_opt_lines: list[str] = []
    gabarito_label: Optional[str] = None
    explanation_lines: list[str] = []
    in_explanation = False

    for line in lines:
        stripped = line.strip()
        if not stripped:
            continue

        # Início de comentário
        if COMMENT_START_RE.match(stripped) and not in_explanation:
            in_explanation = True
            after = COMMENT_START_RE.sub("", stripped).strip()
            if after:
                explanation_lines.append(after)
            if current_opt_label:
                options.append({
                    "label": current_opt_label.upper(),
                    "text": clean_text(" ".join(current_opt_lines)),
                    "is_correct": False,
                })
                current_opt_label = None
                current_opt_lines = []
            continue

        if in_explanation:
            # Procurar gabarito na linha da explicação
            gm = GABA_INLINE_LETRA_RE.search(stripped)
            if gm and not gabarito_label:
                gabarito_label = gm.group(1).upper()
            gm_ce = GABA_INLINE_CE_RE.search(stripped)
            if gm_ce and not gabarito_label:
                val = gm_ce.group(1).upper()
                gabarito_label = "C" if val in ("CERTO", "VERDADEIRO") else "E"
            explanation_lines.append(stripped)
            continue

        # Gabarito inline fora da seção de comentário (ex: linha "Gabarito: Letra D.")
        if not in_explanation:
            gm = GABA_INLINE_LETRA_RE.search(stripped)
            if gm and "gabarito" in stripped.lower():
                gabarito_label = gm.group(1).upper()
                # Texto após o gabarito → início de explicação
                after = stripped[gm.end():].strip()
                if after and len(after) > 10:
                    in_explanation = True
                    explanation_lines.append(after)
                if current_opt_label:
                    options.append({
                        "label": current_opt_label.upper(),
                        "text": clean_text(" ".join(current_opt_lines)),
                        "is_correct": False,
                    })
                    current_opt_label = None
                    current_opt_lines = []
                continue
            gm_ce = GABA_INLINE_CE_RE.search(stripped)
            if gm_ce and "gabarito" in stripped.lower():
                val = gm_ce.group(1).upper()
                gabarito_label = "C" if val in ("CERTO", "VERDADEIRO") else "E"
                if current_opt_label:
                    options.append({
                        "label": current_opt_label.upper(),
                        "text": clean_text(" ".join(current_opt_lines)),
                        "is_correct": False,
                    })
                    current_opt_label = None
                    current_opt_lines = []
                continue

        # Início de alternativa
        opt_m = OPTION_RE.match(line)
        if opt_m:
            if current_opt_label:
                options.append({
                    "label": current_opt_label.upper(),
                    "text": clean_text(" ".join(current_opt_lines)),
                    "is_correct": False,
                })
            current_opt_label = opt_m.group(1).upper()
            current_opt_lines = [opt_m.group(2).strip()]
            continue

        if current_opt_label:
            current_opt_lines.append(stripped)
        else:
            statement_lines.append(stripped)

    # Finalizar última opção
    if current_opt_label:
        options.append({
            "label": current_opt_label.upper(),
            "text": clean_text(" ".join(current_opt_lines)),
            "is_correct": False,
        })

    statement = "\n".join(statement_lines).strip()
    statement = re.sub(r"^\d+[.)]\s*", "", statement).strip()
    statement = clean_text(statement)

    if not statement or len(statement) < 15:
        return None

    # Questão C/E?
    if not options:
        if CE_INDICATOR_RE.search(statement) or (gabarito_label and gabarito_label in ("C", "E")):
            certo_correct = gabarito_label == "C"
            errado_correct = gabarito_label == "E"
            options = [
                {"label": "C", "text": "Certo", "is_correct": certo_correct},
                {"label": "E", "text": "Errado", "is_correct": errado_correct},
            ]
        else:
            return None

    if len(options) < 2:
        return None

    # Aplicar gabarito
    if gabarito_label:
        for o in options:
            o["is_correct"] = o["label"] == gabarito_label

    explanation = clean_text("\n".join(explanation_lines).strip()[:2000])
    src, year = _extract_source_year(statement, source)

    return {
        "statement": statement,
        "options": options[:5],
        "explanation": explanation,
        "source": src,
        "year": year,
        "topic": topic,
    }


# ─── Lista de Questões (seção sem comentários) ────────────────────────────────

def _extract_listed_questions(text: str, source: str, gabarito_map: dict[int, str], lesson_topic: str) -> list[dict]:
    """
    Extrai questões da seção de lista (sem comentários).
    Usa cabeçalhos de tópico para associar topic a cada grupo de questões.
    O gabarito vem da tabela extraída separadamente.
    """
    # Encontrar onde a lista de questões começa (após a seção comentada)
    # Heurística: a lista começa quando há questões numeradas SEM bloco "Comentários:" próximo
    list_start = _find_list_section_start(text)
    if list_start < 0:
        return []

    list_text = text[list_start:]

    # Extrair tópicos e questões
    questions: list[dict] = []
    current_topic = lesson_topic
    lines = list_text.split("\n")
    i = 0
    n_lines = len(lines)
    current_question_num: Optional[int] = None
    current_stmt_lines: list[str] = []
    current_opts: list[dict] = []
    current_opt_label: Optional[str] = None
    current_opt_lines: list[str] = []

    def _flush_question():
        nonlocal current_question_num, current_stmt_lines, current_opts, current_opt_label, current_opt_lines
        if current_opt_label:
            current_opts.append({
                "label": current_opt_label,
                "text": clean_text(" ".join(current_opt_lines)),
                "is_correct": False,
            })
            current_opt_label = None
            current_opt_lines = []

        if current_question_num is not None and current_stmt_lines:
            stmt = "\n".join(current_stmt_lines).strip()
            stmt = re.sub(r"^\d+[.)]\s*", "", stmt).strip()
            stmt = clean_text(stmt)

            if len(stmt) >= 15:
                opts = list(current_opts)
                if not opts and CE_INDICATOR_RE.search(stmt):
                    opts = [
                        {"label": "C", "text": "Certo", "is_correct": False},
                        {"label": "E", "text": "Errado", "is_correct": False},
                    ]

                if opts and len(opts) >= 2:
                    # Aplicar gabarito
                    correct = gabarito_map.get(current_question_num)
                    if correct:
                        for o in opts:
                            o["is_correct"] = o["label"] == correct

                    src, year = _extract_source_year(stmt, source)
                    questions.append({
                        "statement": stmt,
                        "options": opts[:5],
                        "explanation": "",
                        "source": src,
                        "year": year,
                        "topic": current_topic,
                    })

        current_question_num = None
        current_stmt_lines = []
        current_opts = []

    while i < n_lines:
        line = lines[i]
        stripped = line.strip()

        if not stripped:
            i += 1
            continue

        # Detectar início de seção de gabarito → parar
        if GABA_SECTION_RE.match(stripped):
            _flush_question()
            break

        # Detectar número de questão
        num_m = re.match(r"^(\d{1,3})\s*[.)]\s*(?=[A-ZÁÀÂÃÉÊÍÓÔÕÚ\(])", stripped)
        if num_m:
            _flush_question()
            current_question_num = int(num_m.group(1))
            rest = stripped[num_m.end():].strip()
            current_stmt_lines = [rest] if rest else []
            i += 1
            continue

        # Dentro de uma questão
        if current_question_num is not None:
            # Detectar alternativa
            opt_m = OPTION_RE.match(line)
            if opt_m:
                if current_opt_label:
                    current_opts.append({
                        "label": current_opt_label,
                        "text": clean_text(" ".join(current_opt_lines)),
                        "is_correct": False,
                    })
                current_opt_label = opt_m.group(1).upper()
                current_opt_lines = [opt_m.group(2).strip()]
            elif current_opt_label:
                current_opt_lines.append(stripped)
            else:
                current_stmt_lines.append(stripped)
        else:
            pass

        i += 1

    _flush_question()
    return questions


def _find_list_section_start(text: str) -> int:
    """
    Encontra o offset onde a seção de 'lista de questões' começa.
    Heurística: encontrar 'Lista das Questões' ou segunda ocorrência de questão numerada
    sem bloco 'Comentários' próximo — típico da lista sem gabarito.
    """
    # Tentar marcador explícito
    marker_re = re.compile(
        r"lista\s+das?\s+questões?\s+comentadas?|questões?\s+(?:de\s+)?concurso",
        re.IGNORECASE,
    )
    m = marker_re.search(text)
    if m:
        # Retroceder para o início da linha
        start = text.rfind("\n", 0, m.start())
        return start if start >= 0 else m.start()

    # Fallback: encontrar zona com questões numeradas sem bloco comentário nos próximos 800 chars
    matches = list(QUESTION_NUM_RE.finditer(text))
    for i, match in enumerate(matches):
        # Verificar se há "Comentários:" nos próximos 800 chars
        chunk = text[match.start(): match.start() + 800]
        if not COMMENT_START_RE.search(chunk):
            # E se existir mais que 3 questões seguidas sem comentário
            no_comment_run = 0
            for j in range(i, min(i + 6, len(matches))):
                chunk_j = text[matches[j].start(): matches[j].start() + 600]
                if not COMMENT_START_RE.search(chunk_j):
                    no_comment_run += 1
                else:
                    break
            if no_comment_run >= 3:
                return match.start()

    return -1


# ─── Deduplicação ─────────────────────────────────────────────────────────────

def _deduplicate(commented: list[dict], listed: list[dict]) -> list[dict]:
    """Combina as duas listas removendo duplicatas. Comentadas têm prioridade."""
    seen: set[str] = set()
    result: list[dict] = []

    for q in commented:
        key = q["statement"][:80].lower().strip()
        if key not in seen:
            seen.add(key)
            result.append(q)

    for q in listed:
        key = q["statement"][:80].lower().strip()
        if key not in seen:
            seen.add(key)
            result.append(q)

    return result


# ─── Source / Year ────────────────────────────────────────────────────────────

QUESTION_HEADER_RE = re.compile(
    r"\(([A-Z]{2,20}(?:[/\-–,]\s*[A-Z0-9]{2,30})+(?:[/\-–,]\s*\d{4})?)\)",
    re.IGNORECASE,
)

BANCAS = {
    "CESPE": "CEBRASPE", "CEBRASPE": "CEBRASPE", "FGV": "FGV",
    "FCC": "FCC", "VUNESP": "VUNESP", "QUADRIX": "QUADRIX",
    "CESGRANRIO": "CESGRANRIO", "IDIB": "IDIB", "IBFC": "IBFC",
    "IADES": "IADES", "ESAF": "ESAF", "AOCP": "AOCP", "CODESG": "CODESG",
    "CBM": "CBM",
}


def _extract_source_year(statement: str, default_source: str) -> tuple[str, Optional[int]]:
    source = default_source
    year: Optional[int] = None

    m = QUESTION_HEADER_RE.search(statement[:250])
    if m:
        parts = re.split(r"[/\-–,]", m.group(1))
        for part in parts:
            part = part.strip().upper()
            if part in BANCAS:
                source = BANCAS[part]
            elif re.match(r"^\d{4}$", part):
                year = int(part)

    if source == default_source:
        fb = re.search(
            r"\b(CESPE|CEBRASPE|FGV|FCC|VUNESP|QUADRIX|CESGRANRIO|IADES|IBFC|ESAF|AOCP)\b",
            statement[:250], re.IGNORECASE,
        )
        if fb:
            source = BANCAS.get(fb.group(1).upper(), fb.group(1).upper())
            
    return source, year

def extract_lesson_topic(pdf_path: Path) -> str:
    """Extrai o tema da aula baseado no índice do PDF."""
    try:
        import pdfplumber
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages[:6]:
                text = page.extract_text()
                if not text:
                    continue
                
                # Clean up tracking dots
                text = text.replace('.', '')
                lines = text.split('\n')
                for line in lines:
                    line = line.strip()
                    nospaces = line.replace(' ', '')
                    m = re.match(r'^(?:[1-9]|0[1-9])[)\-\.]?([A-ZÁÀÂÃÉÊÍÓÔÕÚa-záàâãéêíóôõú].+?)(?:\d+$|$)', nospaces)
                    if m:
                        topic = m.group(1).strip()
                        topic = re.sub(r'([a-zà-ú])([A-ZÁ-Ú])', r'\1 \2', topic)
                        ignore_words = r'abertura|apresentação|considerações|introdução|aviso|janeiro|fevereiro|março|abril|maio|junho|julho|agosto|setembro|outubro|novembro|dezembro'
                        if not re.search(ignore_words, topic, re.IGNORECASE):
                            return topic
    except Exception as e:
        logger.error(f"Erro ao extrair tópico de {pdf_path}: {e}")
    return "Geral"
