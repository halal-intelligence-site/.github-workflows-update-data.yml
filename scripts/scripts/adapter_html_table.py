from bs4 import BeautifulSoup
from typing import List, Dict
from scripts.common import get_html, normalize_record

def parse_html_table(url: str, country_cc_map=None, acc_tag=""):
    html = get_html(url)
    soup = BeautifulSoup(html, "lxml")

    # Try common table patterns; adjust selectors per site as needed.
    table = soup.select_one("table") or soup.find("table")
    if not table:
        return []

    headers = [th.get_text(strip=True) for th in table.select("thead th")] or \
              [th.get_text(strip=True) for th in table.select("tr th")]

    rows = []
    for tr in table.select("tbody tr") or table.select("tr"):
        cells = [td.get_text(" ", strip=True) for td in tr.select("td")]
        if not cells or len(cells) < 2:
            continue
        row = dict(zip(headers[:len(cells)], cells))

        name = row.get("Name") or row.get("Certification Body") or row.get("CB") or cells[0]
        country = row.get("Country") or row.get("Location") or ""
        site = row.get("Website") or ""
        status = row.get("Status") or "Accredited"
        scopes = []
        for k in ("Scope", "Scopes", "Category", "Scheme"):
            if row.get(k):
                scopes = [s.strip() for s in row[k].replace(";", ",").split(",") if s.strip()]
                break

        cc = None
        if country_cc_map and country:
            cc = country_cc_map.get(country.strip().lower())

        rec = normalize_record({
            "id": f"{acc_tag}-{name}".lower().replace(" ", "-")[:64],
            "name": name,
            "country": country,
            "cc": cc,
            "scopes": scopes,
            "accs": [acc_tag] if acc_tag else [],
            "status": status,
            "site": site,
            "evidence": url
        })
        rows.append(rec)
    return rows
