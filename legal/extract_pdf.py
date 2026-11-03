"""
NyayaGuide PDF Extraction Pipeline
Extracts text, metadata, and constitutional articles from official Indian Government PDFs
(e.g., Legislative Department diglot Constitution of India and Gazette notifications).
Flags low-quality or OCR-needed text for human review.
"""
import re
from pathlib import Path
from typing import Dict, Any, List, Optional
import pypdf
from legal.normalize import clean_text

def extract_pdf_document(pdf_path: Path) -> Dict[str, Any]:
    """
    Extracts text and metadata from an official PDF.
    Returns structured dict with page count, metadata, extracted text, and review flags.
    """
    pdf_path = Path(pdf_path)
    if not pdf_path.exists():
        raise FileNotFoundError(f"PDF document not found: {pdf_path}")
    
    reader = pypdf.PdfReader(str(pdf_path))
    total_pages = len(reader.pages)
    
    doc_info = reader.metadata or {}
    title = getattr(doc_info, "title", None) or pdf_path.stem
    author = getattr(doc_info, "author", None) or "Ministry of Law and Justice, Govt of India"
    
    pages_text = []
    suspiciously_short_pages = 0
    
    for idx, page in enumerate(reader.pages):
        try:
            page_text = page.extract_text() or ""
            cleaned = clean_text(page_text)
            if len(cleaned) < 50:
                suspiciously_short_pages += 1
            pages_text.append({"page_number": idx + 1, "text": cleaned})
        except Exception as e:
            pages_text.append({"page_number": idx + 1, "text": "", "error": str(e)})
            suspiciously_short_pages += 1
            
    is_ocr_needed = (suspiciously_short_pages / max(1, total_pages)) > 0.4
    
    return {
        "file_name": pdf_path.name,
        "file_path": str(pdf_path),
        "total_pages": total_pages,
        "doc_title": title,
        "author": author,
        "pages": pages_text,
        "is_ocr_needed": is_ocr_needed,
        "needs_review": is_ocr_needed or (total_pages == 0)
    }

def extract_articles_from_constitution_pdf(pdf_path: Path, max_pages: int = 120) -> List[Dict[str, Any]]:
    """
    Extracts Fundamental Rights and core articles from the official Constitution diglot PDF.
    Preserves article numbers, headings, and authentic statutory texts.
    """
    extracted_doc = extract_pdf_document(pdf_path)
    articles = []
    
    # Regex to capture Article patterns in the official diglot / English version
    # Examples: "14. Equality before law.—The State shall not deny..."
    # or "Article 21. Protection of life and personal liberty.—"
    article_pattern = re.compile(
        r"(?:(?:Article|Art\.)\s+)?([0-9]+[A-Z]?)\.\s+([A-Za-z\s,—\(\)]+?)[.—–-]\s*(.+?)(?=(?:(?:Article|Art\.)\s+[0-9]+[A-Z]?\.|\Z))",
        re.DOTALL
    )
    
    full_text = "\n".join([p["text"] for p in extracted_doc["pages"][:max_pages]])
    
    matches = article_pattern.findall(full_text)
    for num, heading, body in matches:
        heading_clean = heading.strip().strip(".—–-")
        body_clean = clean_text(body)[:1500]  # Reasonable provision snippet
        if len(body_clean) > 30 and len(heading_clean) > 3:
            articles.append({
                "provision_number": num,
                "heading": heading_clean,
                "text": body_clean,
                "source": pdf_path.name
            })
            
    return articles

if __name__ == "__main__":
    test_pdf = Path("data/preamble.pdf")
    if test_pdf.exists():
        res = extract_pdf_document(test_pdf)
        print(f"Extracted {test_pdf.name}: {res['total_pages']} pages, OCR needed: {res['is_ocr_needed']}")
