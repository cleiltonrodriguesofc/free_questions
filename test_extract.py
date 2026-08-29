import pdfplumber
import sys

path = "/media/cleilton/CLEILTON/ESTUDOS/BACEN_study/Phase 1 - Foundation - 4_weeks/Day 1/BACEN - Administrative Law/Aula 01_01.pdf"

try:
    with pdfplumber.open(path) as pdf:
        page = pdf.pages[10] # just an arbitrary page
        text_2 = page.extract_text(x_tolerance=2.0, y_tolerance=3.0)
        text_1 = page.extract_text(x_tolerance=1.0, y_tolerance=3.0)
        
        print("--- x_tolerance=2.0 ---")
        print(text_2[:500])
        print("\n--- x_tolerance=1.0 ---")
        print(text_1[:500])
except Exception as e:
    print(e)
