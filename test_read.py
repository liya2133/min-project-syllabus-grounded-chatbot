import pdfplumber
import os

folder = "data/dsml"

for filename in os.listdir(folder):
    if filename.endswith(".pdf"):
        filepath = os.path.join(folder, filename)
        print(f"\n=== Reading: {filename} ===")
        with pdfplumber.open(filepath) as pdf:
            print(f"Number of pages: {len(pdf.pages)}")
            first_page_text = pdf.pages[0].extract_text()
            print("Preview of page 1:")
            print(first_page_text[:300] if first_page_text else "(no text found — might be a scanned PDF)")