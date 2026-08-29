"""
Extrator de questões de múltipla escolha (A-E) de PDFs de apostilas BACEN/Cebraspe.

Padrões reconhecidos:
  - Enunciado seguido de opções rotuladas A), B), C), D), E) ou a) b) c) d) e)
  - Gabarito inline: "Gabarito: B" / "Resposta: C" / "Gabarito Comentado: D"
  - Comentário/Justificativa/Resolução após o gabarito → salvo como explanation
  - Questões numeradas: "1.", "Questão 1", "Q1.", etc.
  - Tópico extraído de cabeçalhos de seção (ex: "Aula 01 — Princípios Administrativos")
"""

import re
import logging
from pathlib import Path
from typing import Optional

logger = logging.getLogger(__name__)

# ─── Regex de padrões ─────────────────────────────────────────────────────────

# Início de opção: A) texto  ou  a) texto  ou  (A) texto
OPTION_RE = re.compile(r"^\s*[(\[]?\s*([AaBbCcDdEe])\s*[)\]\.]\s*(.+)", re.DOTALL)

# Início de questão numerada
QUESTION_START_RE = re.compile(
    r"^\s*(?:questão|questao|quest\.?|q\.?)\s*\d+[\.\):\s]|^\s*\d{1,3}[\.\)]\s*[A-ZÁÀÂÃÉÊÍÓÔÕÚ]",
    re.IGNORECASE,
)

# Gabarito inline
GABARITO_RE = re.compile(
    r"(?:gabarito|resposta|alternativa\s+correta)\s*(?:comentad[oa])?\s*[:\-–]\s*([AaBbCcDdEe])",
    re.IGNORECASE,
)

# Início de comentário/explicação
COMMENT_START_RE = re.compile(
    r"^\s*(?:comentário|comentario|justificativa|resolução|resolucao|explicação|explicacao"
    r"|gabarito\s+comentado|gabarito\s+e\s+comentário|comentários?)[:\-–\s]*",
    re.IGNORECASE,
)

# Cabeçalho de tópico: "Aula 01", "Capítulo 3:", "Tema: Princípios"
TOPIC_HEADER_RE = re.compile(
    r"^(?:aula|capítulo|capitulo|tema|assunto|módulo|modulo)\s*\d*\s*[:\-–]?\s*(.+)$",
    re.IGNORECASE,
)

# Seção de gabarito tabular: "1. B  2. A  3. C ..."
GABARITO_TABLE_RE = re.compile(r"(\d+)\s*[\.\-]\s*([AaBbCcDdEe])\b")


def extract_questions_from_pdf(pdf_path: str | Path, source_label: str = "") -> list[dict]:
    """
    Extrai questões de um PDF e retorna lista de dicts:
    {
        statement: str,
        options: [{"label": "A", "text": "...", "is_correct": bool}, ...],
        explanation: str,   ← comentário/justificativa extraído do PDF
        source: str,
        topic: str,         ← tópico/aula detectado pelo cabeçalho de seção
    }
    """
    try:
        import pdfplumber
    except ImportError:
        logger.error("pdfplumber não instalado. Execute: pip install pdfplumber")
        return []

    path = Path(pdf_path)
    if not path.exists():
        logger.warning(f"PDF não encontrado: {path}")
        return []

    raw_text = _extract_text(path)
    if not raw_text:
        logger.warning(f"PDF sem texto extraível: {path}")
        return []

    # Estratégia 1: extração estruturada por padrões de questão
    questions = _parse_structured(raw_text, source_label)

    if not questions:
        # Fallback: janela deslizante
        questions = _parse_sliding_window(raw_text, source_label)

    logger.info(f"  → {len(questions)} questões extraídas de {path.name}")
    return questions


def _extract_text(path: Path) -> str:
    import pdfplumber
    pages_text = []
    with pdfplumber.open(str(path)) as pdf:
        for page in pdf.pages:
            # Crop top 8% and bottom 8% to remove headers and footers
            bbox = (0, float(page.height) * 0.08, float(page.width), float(page.height) * 0.92)
            cropped_page = page.crop(bbox)
            text = cropped_page.extract_text(x_tolerance=2.0, y_tolerance=3.0)
            if text:
                pages_text.append(text)
    return "\n".join(pages_text)


def _parse_structured(text: str, source: str) -> list[dict]:
    """
    Estratégia principal: divide em blocos de questão e dentro de cada
    bloco extrai enunciado + opções + gabarito + comentário + tópico.
    """
    text = re.sub(r"\n{3,}", "\n\n", text)

    gabarito_map = _extract_gabarito_table(text)
    comment_map = _extract_comment_table(text)  # {num: comentário}
    current_topic = _detect_first_topic(text)

    blocks = _split_into_question_blocks(text)
    if len(blocks) < 2:
        return []

    questions = []
    for idx, (num, block) in enumerate(blocks, start=1):
        # detectar mudança de tópico dentro do bloco
        topic_match = TOPIC_HEADER_RE.search(block.split("\n")[0])
        if topic_match:
            current_topic = topic_match.group(1).strip()[:100]

        parsed = _parse_block(block, source, current_topic)
        if parsed:
            # resolver gabarito via tabela de gabarito
            if num and num in gabarito_map and not any(o["is_correct"] for o in parsed["options"]):
                correct_label = gabarito_map[num].upper()
                for o in parsed["options"]:
                    o["is_correct"] = o["label"] == correct_label

            # resolver comentário via tabela de comentários
            if num and num in comment_map and not parsed["explanation"]:
                parsed["explanation"] = comment_map[num]

            questions.append(parsed)

    return questions


def _detect_first_topic(text: str) -> str:
    """Tenta capturar o primeiro tópico do documento."""
    for line in text.split("\n")[:30]:
        m = TOPIC_HEADER_RE.match(line.strip())
        if m:
            return m.group(1).strip()[:100]
    return ""


def _split_into_question_blocks(text: str) -> list[tuple[Optional[int], str]]:
    """Retorna lista de (número, bloco_de_texto) para cada questão."""
    pattern = re.compile(
        r"(?:^|\n)\s*(\d{1,3})\s*[\.\)]\s*(?=[A-ZÁÀÂÃÉÊÍÓÔÕÚ\(])",
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


def _parse_block(block: str, source: str, topic: str = "") -> Optional[dict]:
    """
    Extrai enunciado, opções, gabarito e comentário de um bloco de questão.
    O comentário é tudo que vem após o gabarito/resposta dentro do bloco.
    """
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

        # ── Verificar início de comentário/explicação ──
        if COMMENT_START_RE.match(stripped):
            in_explanation = True
            # capturar texto na mesma linha após o marcador
            after = COMMENT_START_RE.sub("", stripped).strip()
            if after:
                explanation_lines.append(after)
            # finalizar opção em andamento
            if current_opt_label:
                options.append({
                    "label": current_opt_label.upper(),
                    "text": " ".join(current_opt_lines).strip(),
                    "is_correct": False,
                })
                current_opt_label = None
                current_opt_lines = []
            continue

        if in_explanation:
            if stripped:
                explanation_lines.append(stripped)
            continue

        # ── Verificar gabarito inline ──
        gab_match = GABARITO_RE.search(stripped)
        if gab_match and not in_explanation:
            gabarito_label = gab_match.group(1).upper()
            # se houver texto adicional após o gabarito na mesma linha → começo da explicação
            remainder = stripped[gab_match.end():].strip()
            if remainder and len(remainder) > 10:
                in_explanation = True
                explanation_lines.append(remainder)
            if current_opt_label:
                options.append({
                    "label": current_opt_label.upper(),
                    "text": " ".join(current_opt_lines).strip(),
                    "is_correct": False,
                })
                current_opt_label = None
                current_opt_lines = []
            continue

        # ── Verificar início de opção ──
        opt_match = OPTION_RE.match(line)
        if opt_match:
            if current_opt_label:
                options.append({
                    "label": current_opt_label.upper(),
                    "text": " ".join(current_opt_lines).strip(),
                    "is_correct": False,
                })
            current_opt_label = opt_match.group(1).upper()
            current_opt_lines = [opt_match.group(2).strip()]
        elif current_opt_label:
            if stripped:
                current_opt_lines.append(stripped)
        else:
            if stripped:
                statement_lines.append(stripped)

    # ── Salvar última opção ──
    if current_opt_label:
        options.append({
            "label": current_opt_label.upper(),
            "text": " ".join(current_opt_lines).strip(),
            "is_correct": False,
        })

    # ── Validação ──
    statement = "\n".join(statement_lines).strip()
    statement = re.sub(r"^\d+[\.\)]\s*", "", statement).strip()
    
    # Limpeza adicional (remover links)
    statement = re.sub(r"http[s]?://\S+", "", statement)
    statement = re.sub(r"www\.\S+", "", statement)

    if not statement or len(options) < 4:
        return None

    # ── Marcar gabarito ──
    if gabarito_label:
        for o in options:
            o["is_correct"] = o["label"] == gabarito_label

    explanation = "\n".join(explanation_lines).strip()
    explanation = re.sub(r"http[s]?://\S+", "", explanation)
    explanation = re.sub(r"www\.\S+", "", explanation)
    # limitar tamanho da explicação
    if len(explanation) > 2000:
        explanation = explanation[:2000] + "…"

    # Aplicar limpeza adicional (palavras coladas e pontuação)
    statement = clean_extracted_text(statement)
    explanation = clean_extracted_text(explanation)
    for o in options:
        o["text"] = clean_extracted_text(o["text"])

    source_found = _extract_source_from_statement(statement, source)

    return {
        "statement": statement,
        "options": options[:5],
        "explanation": explanation,
        "source": source_found,
        "topic": topic,
    }


def _extract_gabarito_table(text: str) -> dict[int, str]:
    """Extrai tabela de gabarito: {número: letra}"""
    gab_section_re = re.compile(
        r"(?:gabarito|gabaritos?|respostas?)[:\s]*\n?((?:\s*\d+\s*[\.\-]\s*[AaBbCcDdEe]\s*\n?)+)",
        re.IGNORECASE,
    )
    result: dict[int, str] = {}
    for m in gab_section_re.finditer(text):
        section = m.group(1)
        for num_match in GABARITO_TABLE_RE.finditer(section):
            result[int(num_match.group(1))] = num_match.group(2).upper()

    if not result:
        for num_match in GABARITO_TABLE_RE.finditer(text[-3000:]):
            result[int(num_match.group(1))] = num_match.group(2).upper()

    return result


def _extract_comment_table(text: str) -> dict[int, str]:
    """
    Extrai comentários numerados em seção separada.
    Padrão: "1. Gabarito: B\nComentário: O princípio..."
    Retorna {número: texto_do_comentário}
    """
    result: dict[int, str] = {}

    # Procurar blocos "Gabarito e comentário" ou "Comentários" como seção
    section_re = re.compile(
        r"(?:gabarito(?:s)?\s*e\s*comentário(?:s)?|comentário(?:s)?)\s*\n(.*?)(?=\n\n\n|\Z)",
        re.IGNORECASE | re.DOTALL,
    )
    for section_match in section_re.finditer(text):
        section_text = section_match.group(1)
        # dentro da seção, detectar blocos numerados
        block_re = re.compile(r"(\d+)\s*[\.\)]\s*(.*?)(?=\n\s*\d+\s*[\.\)]|\Z)", re.DOTALL)
        for bm in block_re.finditer(section_text):
            num = int(bm.group(1))
            comment_text = bm.group(2).strip()
            # remover "Gabarito: X" do início
            comment_text = GABARITO_RE.sub("", comment_text).strip()
            comment_text = COMMENT_START_RE.sub("", comment_text).strip()
            if comment_text and len(comment_text) > 10:
                result[num] = comment_text[:2000]

    return result


def _parse_sliding_window(text: str, source: str) -> list[dict]:
    """Fallback: detecta blocos pelo padrão de 5 opções consecutivas A-E."""
    questions = []
    lines = text.split("\n")
    current_topic = _detect_first_topic(text)
    i = 0

    while i < len(lines):
        opt_a = OPTION_RE.match(lines[i])
        if opt_a and opt_a.group(1).upper() == "A":
            opts = []
            j = i
            expected = "A"
            while j < len(lines) and len(opts) < 5:
                m = OPTION_RE.match(lines[j])
                if m and m.group(1).upper() == expected:
                    opts.append({"label": m.group(1).upper(), "text": m.group(2).strip(), "is_correct": False})
                    expected = chr(ord(expected) + 1)
                elif opts:
                    s = lines[j].strip()
                    if s and not OPTION_RE.match(lines[j]):
                        opts[-1]["text"] += " " + s
                j += 1

            if len(opts) >= 4:
                # enunciado = linhas antes
                stmt_lines = []
                k = max(0, i - 8)
                while k < i:
                    s = lines[k].strip()
                    if s and not QUESTION_START_RE.match(lines[k]):
                        stmt_lines.append(s)
                    k += 1
                statement = "\n".join(stmt_lines[-7:]).strip()

                if statement and len(statement) > 20:
                    gab = None
                    explanation_lines = []
                    in_exp = False
                    for l in lines[j:j + 15]:
                        if COMMENT_START_RE.match(l.strip()):
                            in_exp = True
                            after = COMMENT_START_RE.sub("", l.strip()).strip()
                            if after:
                                explanation_lines.append(after)
                            continue
                        if in_exp and l.strip():
                            explanation_lines.append(l.strip())
                            continue
                        gm = GABARITO_RE.search(l)
                        if gm and not gab:
                            gab = gm.group(1).upper()
                            remainder = l[gm.end():].strip()
                            if remainder and len(remainder) > 10:
                                in_exp = True
                                explanation_lines.append(remainder)

                    if gab:
                        for o in opts:
                            o["is_correct"] = o["label"] == gab

                    # Limpeza extra
                    statement = clean_extracted_text(statement)
                    explanation_text = clean_extracted_text("\n".join(explanation_lines).strip()[:2000])
                    for o in opts:
                        o["text"] = clean_extracted_text(o["text"])

                    source_found = _extract_source_from_statement(statement, source)

                    questions.append({
                        "statement": statement,
                        "options": opts,
                        "explanation": explanation_text,
                        "source": source_found,
                        "topic": current_topic,
                    })
                i = j
                continue
        i += 1

    return questions


def _extract_source_from_statement(statement: str, default_source: str) -> str:
    # Procura explicitamente por siglas de bancas conhecidas no início do enunciado
    m = re.search(r"^\s*\(.*?\b(CESPE|CEBRASPE|FGV|FCC|VUNESP|QUADRIX|CESGRANRIO|IDIB|IBFC|IADES)\b.*?\)", statement, re.IGNORECASE)
    if m:
        banca = m.group(1).upper()
        if banca == "CESPE":
            return "CEBRASPE"
        return banca
        
    return default_source

def clean_extracted_text(text: str) -> str:
    """
    Limpa o texto extraído do PDF:
    1. Adiciona espaço após pontuação colada com letras (ex: 'palavra,outra' -> 'palavra, outra').
    """
    if not text:
        return text

    # Espaço após pontuação (exceto se for número)
    text = re.sub(r'(?<=[a-zA-Z])([,.;:])(?=[a-zA-Z])', r'\1 ', text)
    
    return text

