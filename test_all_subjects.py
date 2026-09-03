import glob
import re
import pdfplumber

def extract_lesson_topic(pdf_path):
    try:
        with pdfplumber.open(str(pdf_path)) as pdf:
            for page in pdf.pages[:6]:
                text = page.extract_text()
                if not text: continue
                text = text.replace(".", "")
                lines = text.split("\n")
                for line in lines:
                    line = line.strip()
                    nospaces = line.replace(" ", "")
                    m = re.match(r"^(?:2|02|3|03|1|01)[)\-\.](.+?)(?:\d+$|$)", nospaces)
                    if m:
                        topic = m.group(1).strip()
                        topic = re.sub(r"([a-zà-ú])([A-ZÁ-Ú])", r"\1 \2", topic)
                        if not re.search(r"abertura|apresentação|considerações|aviso", topic, re.IGNORECASE):
                            return topic
    except Exception as e:
        pass
    return "Geral"

pdfs = glob.glob("/media/cleilton/CLEILTON/ESTUDOS/BACEN_study/**/*Apostila.pdf", recursive=True)
subjects_tested = set()
for p in pdfs:
    subject = "Unknown"
    for part in p.split("/"):
        if part.startswith("BACEN - "):
            subject = part.replace("BACEN - ", "")
            break
            
    if subject not in subjects_tested:
        subjects_tested.add(subject)
        topic = extract_lesson_topic(p)
        print(f"[{subject}] {p.split('/')[-1]} -> Tópico Extraído: {topic}")
