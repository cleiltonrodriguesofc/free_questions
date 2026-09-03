import pdfplumber
import re
from pathlib import Path

def extract_lesson_topic(pdf_path):
    with pdfplumber.open(pdf_path) as pdf:
        for page in pdf.pages[:4]:
            text = page.extract_text()
            if not text:
                continue
            
            # Clean up tracking dots
            text = text.replace('.', '')
            
            lines = text.split('\n')
            for line in lines:
                line = line.strip()
                # Remove spaces so we can parse cleanly
                nospaces = line.replace(' ', '')
                m = re.match(r'^(?:2|02|3|03|1|01)[)\-\.](.+?)(?:\d+$|$)', nospaces)
                if m:
                    topic = m.group(1).strip()
                    # Add spaces between CamelCase
                    topic = re.sub(r'([a-zà-ú])([A-ZÁ-Ú])', r'\1 \2', topic)
                    if not re.search(r'abertura|apresentação|considerações', topic, re.IGNORECASE):
                        return topic
    return "Geral"

p = "/media/cleilton/CLEILTON/ESTUDOS/BACEN_study/Phase 1 - Foundation - 4_weeks/Day 1/BACEN - Administrative Law/Aula 01_Apostila.pdf"
print("Topic:", extract_lesson_topic(p))
