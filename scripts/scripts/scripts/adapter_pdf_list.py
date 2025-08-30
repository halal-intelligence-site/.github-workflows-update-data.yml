import io, re
from typing import List, Dict
import pdfplumber
from scripts.common import get_bytes, normalize_record

def parse_pdf_directory(url: str, acc_tag: str):
    pdf_bytes = get_bytes(url)
    rows = []
    with pdfplumber.open(io.BytesIO(pdf_bytes)) as pdf:
        text = "\n".join(page.extract_text() or "" for page in pdf.pages)

    # VERY simple heuristic; adjust regex to the real PDF structure.
    # e.g. lines like: Name – Country – Website
    pattern = re.compile(r"(?P<name>.+?)\s*-\s*(?P<country>[A-Za-z ()]+)\s*-\s*(?P<site>https?://\S+)", re.MULTILINE)
    for m in pattern.finditer(text):
        name = m.group("name").strip()
        country = m.group("country").strip()
        site = m.group("site").strip()
        rec = normalize_record({
            "id": f"{acc_tag}-{name}".lower().replace(" ", "-")[:64],
            "name": name,
            "country": country,
            "cc": None,
            "scopes": [],
            "accs": [acc_tag],
            "status": "Accredited",
            "site": site,
            "evidence": url
        })
        rows.append(rec)
    return rows
