import sys
import subprocess

def install_and_import(package, import_name=None):
    if import_name is None:
        import_name = package
    try:
        __import__(import_name)
    except ImportError:
        subprocess.check_call([sys.executable, "-m", "pip", "install", package])

install_and_import('pymupdf', 'fitz')
import fitz

pdf_path = r"e:\工作\系统开发\sjb\static_dashboard\assets\strs_1031724(1).pdf"
out_path = r"e:\工作\系统开发\sjb\pdf_extracted_text.txt"

try:
    doc = fitz.open(pdf_path)
    text = ""
    for page in doc:
        text += page.get_text() + "\n"
        
    with open(out_path, "w", encoding="utf-8") as f:
        f.write(text)
    print(f"Success! Extracted {len(text)} characters.")
except Exception as e:
    print(f"Error: {e}")
