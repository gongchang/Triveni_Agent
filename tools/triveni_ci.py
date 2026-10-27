#!/usr/bin/env python3
import argparse, hashlib, json, os, re, time, urllib.parse, urllib.request
from datetime import date
from functools import lru_cache

TARGET_DRUG_MAP = {
    # Curated CI bridge: trials often list asset names but omit molecular targets.
    'KLK5': ['TRIV-509', 'TRIV-573', 'SXR1096'],
    'KLK7': ['TRIV-509', 'TRIV-573'],
    'KALLIKREIN': ['TRIV-509', 'TRIV-573', 'SXR1096'],
    'SPINK5': ['TRIV-509', 'TRIV-573', 'SXR1096'],
    'LEKTI': ['TRIV-509', 'TRIV-573', 'SXR1096'],
    'PRSS1': ['TRIV-920'],
    'PRSS2': ['TRIV-920'],
    'TRYPSIN': ['TRIV-920'],
}

ASSET_TARGET_MAP = {
    'TRIV-509': 'KLK5/KLK7',
    'TRIV-573': 'KLK5/KLK7',
    'SXR1096': 'KLK5',
    'TRIV-920': 'PRSS1/PRSS2 active trypsin',
}

PROFILES = {
    'TRIV-509': {
        'space': 'atopic dermatitis / epithelial barrier',
        'terms': ['KLK5', 'KLK7', 'kallikrein', 'Netherton', 'SPINK5', 'LEKTI', 'atopic dermatitis'],
    },
    'TRIV-920': {
        'space': 'pancreatitis / trypsin biology',
        'terms': ['PRSS1', 'PRSS2', 'trypsin', 'trypsinogen', 'pancreatitis'],
    },
}

CACHE_DIR = '.cache/triveni-ci-api'
CACHE_TTL = 86400

def get_json(url):
    os.makedirs(CACHE_DIR, exist_ok=True)
    path = os.path.join(CACHE_DIR, hashlib.sha1(url.encode()).hexdigest() + '.json')
    if os.path.exists(path) and time.time() - os.path.getmtime(path) < CACHE_TTL:
        with open(path) as f:
            return json.load(f)
    req = urllib.request.Request(url, headers={'User-Agent': 'triveni-agent/0.1'})
    with urllib.request.urlopen(req, timeout=12) as r:
        data = json.load(r)
    with open(path, 'w') as f:
        json.dump(data, f)
    return data

@lru_cache(maxsize=256)
def chembl_targets_for_drug(name):
    if not name or name.lower() in {'placebo', 'vehicle', 'clean air exposure'}:
        return []
    try:
        search = get_json('https://www.ebi.ac.uk/chembl/api/data/molecule/search.json?q=' + urllib.parse.quote(name))
        mol = next((m for m in search.get('molecules', []) if m.get('molecule_chembl_id')), None)
        if not mol:
            return []
        mid = mol['molecule_chembl_id']
        mech = get_json(f'https://www.ebi.ac.uk/chembl/api/data/mechanism.json?molecule_chembl_id={mid}')
        targets = []
        for item in mech.get('mechanisms', [])[:5]:
            tid = item.get('target_chembl_id')
            target_name = item.get('target_name')
            if tid and not target_name:
                try:
                    target_name = get_json(f'https://www.ebi.ac.uk/chembl/api/data/target/{tid}.json').get('pref_name')
                except Exception:
                    pass
            if target_name:
                targets.append({'drug': mol.get('pref_name') or name, 'molecule_chembl_id': mid, 'target': target_name, 'target_chembl_id': tid, 'mechanism': item.get('mechanism_of_action')})
        return targets
    except Exception:
        return []

def safe(fn, *args):
    try:
        return fn(*args)
    except Exception as e:
        return {'error': str(e)}

def pick_profile(q):
    ql = q.lower()
    if any(x in ql for x in ['920', 'prss', 'trypsin', 'pancreatitis']):
        return 'TRIV-920', PROFILES['TRIV-920']
    if any(x in ql for x in ['509', 'klk', 'kallikrein', 'netherton', 'spink5', 'lekti', 'atopic', 'barrier']):
        return 'TRIV-509', PROFILES['TRIV-509']
    return 'custom', {'space': 'custom CI query', 'terms': []}

def query_terms(q, cfg):
    ql = q.lower()
    phrases = [
        'atopic dermatitis', 'epithelial barrier', 'barrier dysfunction', 'netherton syndrome',
        'eczema herpeticum', 'herpes simplex', 'chronic pancreatitis', 'acute pancreatitis',
        'eosinophilic esophagitis', 'pancreatic cancer', 'pancreatic adenocarcinoma'
    ]
    terms = [p for p in phrases if p in ql]
    phrase_words = {w for p in terms for w in p.split()}
    # Use the user's explicit search terms first. Do not expand KLK5 into the full
    # TRIV-509 default bundle, otherwise different queries collapse to same results.
    terms += re.findall(r'\b[A-Z][A-Z0-9-]{2,}\b', q)
    keep = {'kallikrein', 'netherton', 'trypsin', 'trypsinogen', 'pancreatitis', 'eczema', 'dermatitis', 'dupilumab'}
    stop = {'triv', 'triv-509', 'triv-920', 'competitor', 'competitors', 'landscape', 'disease', 'target', 'biology', 'clinical', 'trials', 'trial', 'indication', 'list', 'all', 'using', 'apis', 'source', 'sources', 'for', 'and', 'the', 'with', 'lookup', 'search', 'in', 'literature', 'paper', 'papers', 'preprint', 'preprints', 'biorxiv'}
    terms += [w for w in re.findall(r'[A-Za-z][A-Za-z0-9-]+', ql) if w in keep and w not in phrase_words]
    custom_words = [w for w in re.findall(r'[A-Za-z][A-Za-z0-9-]+', ql) if len(w) > 3 and w not in stop and w not in phrase_words and w not in {'disease', 'biology'}]
    terms += [w for w in custom_words if w not in {t.lower() for t in terms}]
    if not terms:
        terms = cfg['terms']
    dedup = []
    seen = set()
    for t in terms:
        k = t.lower()
        if k not in seen and k not in stop:
            dedup.append(t)
            seen.add(k)
    return dedup[:10]

def linked_drug_terms(terms):
    linked = []
    for t in terms:
        linked += TARGET_DRUG_MAP.get(t.upper(), [])
    seen = set()
    return [x for x in linked if not (x in seen or seen.add(x))]

def likely_drug_terms(q):
    ql = q.lower()
    stop = {'clinical', 'trials', 'trial', 'for', 'with', 'landscape', 'competitor', 'target', 'disease', 'indication', 'atopic', 'dermatitis', 'eczema', 'pancreatitis'}
    words = re.findall(r'[A-Za-z][A-Za-z0-9-]+', q)
    return [w for w in words if len(w) > 4 and w.lower() not in stop and not re.match(r'^(KLK|PRSS|TP\d+|IL\d+)', w, re.I)][:6]

def split_entities(terms):
    diseases = [t for t in terms if ' ' in t or t.lower() in {'dermatitis', 'eczema', 'pancreatitis', 'netherton'}]
    targets = [t for t in terms if t.upper() in TARGET_DRUG_MAP or re.match(r'^[A-Z]{2,}\d*[A-Z0-9-]*$', str(t))]
    return targets, diseases

def trials(terms):
    linked = linked_drug_terms(terms)
    target_terms, disease_terms = split_entities(terms)
    target_or_asset = target_terms + [x for x in linked if x not in target_terms]
    primary = 'https://clinicaltrials.gov/api/v2/studies?query.term=' + urllib.parse.quote(' OR '.join(terms + [x for x in linked if x not in terms])) + '&pageSize=12'
    if disease_terms and target_or_asset:
        primary = 'https://clinicaltrials.gov/api/v2/studies?query.cond=' + urllib.parse.quote(disease_terms[0]) + '&query.term=' + urllib.parse.quote(' OR '.join(target_or_asset)) + '&pageSize=12'
    studies = get_json(primary).get('studies', [])
    if not studies and disease_terms and target_or_asset:
        fallback = 'https://clinicaltrials.gov/api/v2/studies?query.term=' + urllib.parse.quote(' OR '.join(terms + [x for x in linked if x not in terms])) + '&pageSize=12'
        studies = get_json(fallback).get('studies', [])
    rows = []
    seen_nct = set()
    for s in studies:
        p = s.get('protocolSection', {})
        nct = p.get('identificationModule', {}).get('nctId')
        if nct in seen_nct:
            continue
        seen_nct.add(nct)
        interventions = [i.get('name', '') for i in p.get('armsInterventionsModule', {}).get('interventions', [])]
        blob = ' '.join([
            p.get('identificationModule', {}).get('briefTitle') or '',
            p.get('sponsorCollaboratorsModule', {}).get('leadSponsor', {}).get('name') or '',
            ' '.join(p.get('conditionsModule', {}).get('conditions', [])),
            ' '.join(interventions),
        ]).lower()
        linked_hits = [x for x in linked if x.lower() in blob]
        linked_targets = '; '.join(sorted({ASSET_TARGET_MAP.get(x, '') for x in linked_hits if ASSET_TARGET_MAP.get(x)}))
        chembl = []
        chembl_names = {str(t).lower() for t in terms + linked}
        for drug in interventions[:4]:
            base = re.split(r'\s|\(', drug.strip())[0]
            if base.lower() in chembl_names:
                chembl += chembl_targets_for_drug(base)
        chembl_targets = '; '.join(sorted({x['target'] for x in chembl}))
        target_blob = f'{blob} {linked_targets} {chembl_targets}'.lower()
        disease_match = not disease_terms or any(str(t).lower() in blob for t in disease_terms)
        target_match = not target_terms or any(str(t).lower() in target_blob for t in target_terms)
        if not (disease_match and target_match):
            continue
        score = sum(str(t).lower() in blob for t in terms) + 5 * len(linked_hits) + sum(str(t).lower() in chembl_targets.lower() for t in terms)
        rows.append({
            'nct': nct,
            'title': p.get('identificationModule', {}).get('briefTitle'),
            'sponsor': p.get('sponsorCollaboratorsModule', {}).get('leadSponsor', {}).get('name'),
            'conditions': '; '.join(p.get('conditionsModule', {}).get('conditions', [])[:3]),
            'interventions': '; '.join(interventions[:3]),
            'drug_names': '; '.join(interventions[:3]),
            'phase': '; '.join(p.get('designModule', {}).get('phases', []) or []),
            'status': p.get('statusModule', {}).get('overallStatus'),
            'primary_completion': p.get('statusModule', {}).get('primaryCompletionDateStruct', {}).get('date'),
            'target_linked_assets': '; '.join(linked_hits),
            'drug_targets': '; '.join(x for x in [linked_targets, chembl_targets, '; '.join(t for t in target_terms if str(t).lower() in blob)] if x),
            'chembl_targets': chembl_targets,
            'relevance_score': score,
        })
    return sorted(rows, key=lambda r: r.get('relevance_score', 0), reverse=True)[:12]

def literature_query(terms):
    targets, diseases = split_entities(terms)
    if targets and diseases:
        return ' AND '.join([targets[0], diseases[0]])
    return ' OR '.join(terms)

def epmc(terms):
    query = urllib.parse.quote('(' + literature_query(terms) + ')')
    url = f'https://www.ebi.ac.uk/europepmc/webservices/rest/search?query={query}&format=json&pageSize=12'
    data = get_json(url)
    return [{
        'title': r.get('title'), 'year': r.get('pubYear'), 'source': r.get('source'),
        'journal': r.get('journalTitle'), 'doi': r.get('doi'),
    } for r in data.get('resultList', {}).get('result', [])]

def biorxiv(terms):
    # bioRxiv's public details API is a date feed, not search. Europe PMC indexes
    # bioRxiv/medRxiv preprints and is fast enough for query-specific lookup.
    query = '(' + literature_query(terms) + ') AND SRC:PPR'
    url = 'https://www.ebi.ac.uk/europepmc/webservices/rest/search?' + urllib.parse.urlencode({
        'query': query, 'format': 'json', 'pageSize': '12', 'sort': 'FIRST_PDATE_D desc'
    })
    data = get_json(url)
    return [{
        'title': r.get('title'), 'date': r.get('firstPublicationDate') or r.get('pubYear'),
        'doi': r.get('doi'), 'category': r.get('source')
    } for r in data.get('resultList', {}).get('result', [])]

def classify(q):
    ql = q.lower()
    if 'api' in ql or 'source' in ql: return 'apis'
    if 'trial' in ql or 'clinical' in ql: return 'trials'
    if 'paper' in ql or 'literature' in ql or 'preprint' in ql or 'biorxiv' in ql: return 'landscape'
    if 'competitor' in ql or 'landscape' in ql or 'indication' in ql or 'disease' in ql: return 'landscape'
    if 'target' in ql or 'biology' in ql: return 'target'
    return 'trials'  # fast default for the common target + indication lookup

def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('question')
    args = ap.parse_args()
    profile, cfg = pick_profile(args.question)
    mode = classify(args.question)
    terms = query_terms(args.question, cfg)
    targets, diseases = split_entities(terms)
    if mode == 'trials' and targets and not diseases and not re.search(r'\b(clinical|trial|trials)\b', args.question, re.I):
        mode = 'landscape'
    drug_links = []
    for d in likely_drug_terms(args.question):
        drug_links += chembl_targets_for_drug(d)
    out = {'profile': profile, 'space': cfg['space'], 'query_terms': terms, 'target_entities': targets, 'disease_entities': diseases, 'mode': mode, 'original_query': args.question, 'drug_target_links': drug_links}
    if mode == 'apis':
        out['apis'] = [
            {'source': 'ClinicalTrials.gov', 'endpoint': 'https://clinicaltrials.gov/api/v2/studies', 'use': 'clinical trial registry lookup'},
            {'source': 'Europe PMC', 'endpoint': 'https://www.ebi.ac.uk/europepmc/webservices/rest/search', 'use': 'papers, PubMed/PMC, preprint-indexed biomedical literature'},
            {'source': 'Europe PMC preprint index', 'endpoint': 'https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=SRC:PPR', 'use': 'query-specific bioRxiv/medRxiv preprint lookup'},
        ]
    else:
        if not terms:
            out['error'] = 'No searchable target, disease, competitor, or indication terms were found in the query.'
            print(json.dumps(out, indent=2))
            return
        want_lit = mode in ['target', 'landscape'] or bool(targets and diseases)
        out['trials'] = safe(trials, terms) if mode in ['trials', 'landscape'] else []
        out['papers'] = safe(epmc, terms) if want_lit else []
        out['preprints'] = safe(biorxiv, terms) if want_lit else []
    print(json.dumps(out, indent=2))

if __name__ == '__main__':
    main()
