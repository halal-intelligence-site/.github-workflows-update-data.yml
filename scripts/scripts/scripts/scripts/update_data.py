import json
from datetime import datetime
from rapidfuzz import process, fuzz
from scripts.common import write_json, normalize_record, changed_since_last

# Adapters
from scripts.adapter_html_table import parse_html_table
from scripts.adapter_pdf_list import parse_pdf_directory

DATA_PATH = "data/index.json"

# Minimal country mapping; extend as needed
COUNTRY_CC = {
    "united arab emirates": "AE", "uae": "AE",
    "malaysia": "MY", "saudi arabia": "SA", "singapore": "SG",
    "thailand": "TH", "indonesia": "ID", "kazakhstan": "KZ",
    "netherlands": "NL", "morocco": "MA", "turkiye": "TR", "turkey": "TR",
    "united states": "US", "usa": "US", "united kingdom": "GB", "uk": "GB",
}

def dedup(records):
    """De-dup by fuzzy name match within same country."""
    out = []
    seen = []
    for r in records:
        keyspace = [x["name"] for x in out if (x.get("country")==r.get("country")) or not r.get("country")]
        if keyspace:
            match, score, idx = process.extractOne(r["name"], keyspace, scorer=fuzz.token_set_ratio)
            if score >= 93:
                # merge accreditations & scopes
                out[idx]["accs"] = sorted(list(set(out[idx]["accs"] + r.get("accs", []))))
                out[idx]["scopes"] = sorted(list(set(out[idx]["scopes"] + r.get("scopes", []))))
                out[idx]["site"] = out[idx]["site"] or r.get("site","")
                continue
        out.append(r)
    return out

def source_gac():
    url = "https://gac.org.sa/accredited-bodies/"
    # If the site didn't change, skip heavy work (cheap HEAD poll)
    # if not changed_since_last(url): return []
    rows = parse_html_table(url, country_cc_map=COUNTRY_CC, acc_tag="GAC")
    return rows

def source_eiac():
    url = "https://eiac.gov.ae/directory"
    rows = parse_html_table(url, country_cc_map=COUNTRY_CC, acc_tag="EIAC")
    return rows

def source_muis():
    url = "https://www.muis.gov.sg/halal/fhcb/"
    rows = parse_html_table(url, country_cc_map=COUNTRY_CC, acc_tag="MUIS")
    return rows

def source_hak():
    url = "https://english.hak.gov.tr/accredited-hcabs"
    rows = parse_html_table(url, country_cc_map=COUNTRY_CC, acc_tag="HAK")
    return rows

def source_sfda_pdf():
    url = "https://sfda.gov.sa/sites/default/files/2020-08/sfda-halal.pdf"
    rows = parse_pdf_directory(url, acc_tag="SFDA")
    return rows

# Example for a frequently updated government directory that serves JSON/CSV:
def source_bpjph():
    url = "https://bpjph.halal.go.id/datalhln/"  # page; you may need to inspect for JSON request
    # If you identify a JSON endpoint later, fetch and transform here.
    # For now, return empty to keep pipeline green.
    return []

def build():
    all_rows = []
    for fn in (source_gac, source_eiac, source_muis, source_hak, source_sfda_pdf, source_bpjph):
        try:
            rows = fn()
            all_rows.extend(rows)
        except Exception as e:
            print("WARN: source failed:", fn.__name__, e)

    # Normalize, de-dup, and final touches
    all_rows = [normalize_record(r) for r in all_rows if r.get("name")]
    all_rows = dedup(all_rows)

    # Last pass: fill CC by country map if missing
    for r in all_rows:
        if not r.get("cc") and r.get("country"):
            r["cc"] = COUNTRY_CC.get(r["country"].strip().lower())

    # Sort for stable diffs
    all_rows.sort(key=lambda x: (x.get("country") or "", x["name"]))

    write_json(DATA_PATH, all_rows)
    print(f"Wrote {len(all_rows)} rows to {DATA_PATH}")

if __name__ == "__main__":
    build()
