#!/usr/bin/env python3
import json, re, subprocess, sys
from pathlib import Path

PDF = Path('module_references/triveni-hr/Triveni Bio 2025-26 Employee Benefits Memo.pdf')
TXT = Path('.cache/triveni-hr-benefits.txt')

def ensure():
    TXT.parent.mkdir(exist_ok=True)
    if not TXT.exists() or TXT.stat().st_mtime < PDF.stat().st_mtime:
        subprocess.check_call(['pdftotext', str(PDF), str(TXT)])

def main():
    json_out = '--json' in sys.argv[1:]
    q = ' '.join(a for a in sys.argv[1:] if a != '--json').lower()
    ensure()
    paras = [re.sub(r'\s+', ' ', p).strip() for p in TXT.read_text(errors='ignore').split('\n\n')]
    stop = {'what','who','when','where','does','policy','benefit','benefits','the','and','for','with','about','tell','show'}
    terms = [t for t in re.findall(r'[a-z0-9]+', q) if len(t) > 2 and t not in stop]
    generic = {'insurance', 'reimbursement', 'reimbursable', 'coverage', 'covered'}
    specific = [t for t in terms if t not in generic]
    def score(p):
        low = p.lower()
        if specific and not any(t in low for t in specific):
            return 0
        return sum(t in low for t in terms)
    scored = sorted(((score(p), i, p) for i, p in enumerate(paras) if len(p) > 40), reverse=True)
    hits = [{'page': None, 'text': p} for score, _, p in scored[:3] if score]
    result = {'source': str(PDF), 'question': q, 'evidence': hits}
    if json_out:
        print(json.dumps(result, indent=2))
    elif not hits:
        print(f"Nothing was found in the HR benefits memo for: {q}")
        print(f"Source: {PDF}")
    else:
        print(f"Found relevant text in {PDF}.\n")
        print('\n'.join(f"[{i + 1}] {e['text']}" for i, e in enumerate(hits[:2])))

if __name__ == '__main__': main()
