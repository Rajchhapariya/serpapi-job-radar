import io
import re
from typing import Dict, Any, List
from pypdf import PdfReader
from app.database import extract_skills_from_text

# Maximum allowed PDF size: 5 Megabytes
MAX_PDF_SIZE_BYTES = 5 * 1024 * 1024

# Common resume section header patterns
RESUME_SECTION_PATTERNS = [
    re.compile(r'(?i)\b(experience|work\s+experience|professional\s+experience|employment\s+history)\b'),
    re.compile(r'(?i)\b(education|academic\s+background|academics|qualifications|academic\s+profile)\b'),
    re.compile(r'(?i)\b(skills|technical\s+skills|core\s+competencies|technologies|proficiencies)\b'),
    re.compile(r'(?i)\b(projects|academic\s+projects|key\s+projects|personal\s+projects)\b'),
    re.compile(r'(?i)\b(certifications|certificates|licenses|courses|coursework)\b'),
    re.compile(r'(?i)\b(summary|professional\s+summary|profile|career\s+objective|objective)\b'),
    re.compile(r'(?i)\b(achievements|honors|awards|publications)\b'),
]

# Career, contact, and educational keyword indicators
CONTACT_OR_CAREER_PATTERNS = [
    re.compile(r'[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+\.[a-zA-Z0-9-.]+'),  # Email address
    re.compile(r'(?:\+?\d{1,3}[-.\s]?)?\(?\d{3}\)?[-.\s]?\d{3}[-.\s]?\d{4}'),  # Phone pattern
    re.compile(r'(?i)\b(b\.?tech|b\.?e\.?|m\.?tech|mca|bca|b\.?sc|m\.?sc|bachelor|master|phd|diploma)\b'),
    re.compile(r'(?i)\b(developer|engineer|analyst|architect|consultant|programmer|intern|internship|specialist)\b'),
    re.compile(r'(?i)\b(university|institute|college|school|cgpa|gpa|percentage)\b'),
]


def validate_and_extract_resume_pdf(pdf_bytes: bytes) -> Dict[str, Any]:
    """
    Strictly validates and extracts plain text from a resume PDF document.
    Enforces format, length, and semantic checks to guarantee only valid
    resumes are processed (rejecting invoices, bills, books, or blank scans).
    """
    if not pdf_bytes:
        raise ValueError("Uploaded file is empty.")

    if len(pdf_bytes) > MAX_PDF_SIZE_BYTES:
        raise ValueError("File size exceeds 5MB limit.")

    # 1. Magic bytes verification (ISO 32000-1 permits %PDF- within first 1024 bytes)
    if b"%PDF-" not in pdf_bytes[:1024]:
        raise ValueError("Uploaded file is not a valid PDF document (missing %PDF- magic header).")

    # 2. PDF parsing via pypdf
    try:
        reader = PdfReader(io.BytesIO(pdf_bytes))
    except Exception as e:
        raise ValueError(f"Corrupted or unreadable PDF document: {str(e)}")

    if len(reader.pages) == 0:
        raise ValueError("PDF document contains zero pages.")

    if len(reader.pages) > 10:
        raise ValueError("PDF exceeds standard resume length (maximum 10 pages).")

    # 3. Extract text from pages
    extracted_text_chunks: List[str] = []
    for idx, page in enumerate(reader.pages):
        try:
            page_text = page.extract_text() or ""
            if page_text.strip():
                extracted_text_chunks.append(page_text.strip())
        except Exception:
            continue

    full_text = "\n\n".join(extracted_text_chunks).strip()

    if len(full_text) < 80:
        raise ValueError("Uploaded PDF contains no extractable text. Scanned image-only PDFs are not supported.")

    # 4. Strict Resume Semantic Verification
    # Check A: Standard resume section headers (requires at least 2 distinct sections)
    matched_sections = 0
    for pattern in RESUME_SECTION_PATTERNS:
        if pattern.search(full_text):
            matched_sections += 1

    if matched_sections < 2:
        raise ValueError(
            "Document does not match resume structure. Standard resume sections "
            "(e.g., Experience, Education, Skills, or Projects) were not detected."
        )

    # Check B: Career, contact, or educational identifiers (requires at least 1 match)
    has_contact_or_career = any(pat.search(full_text) for pat in CONTACT_OR_CAREER_PATTERNS)
    if not has_contact_or_career:
        raise ValueError(
            "Document lacks professional or contact identifiers (such as degree, job title, email, or institution)."
        )

    # Check C: Technical skill recognition (must contain at least 2 recognizable skills)
    recognized_skills = extract_skills_from_text(full_text)
    if len(recognized_skills) < 2:
        raise ValueError(
            "Document does not contain sufficient technical skills relevant to software or data roles "
            "(at least 2 recognized skills required)."
        )

    return {
        "text": full_text,
        "skills": recognized_skills,
        "page_count": len(reader.pages),
        "char_count": len(full_text)
    }
