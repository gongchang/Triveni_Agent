#!/usr/bin/env python3
import html, json, re, sqlite3, urllib.parse, zipfile
from http.server import BaseHTTPRequestHandler, ThreadingHTTPServer
from pathlib import Path

import duckdb
import pandas as pd
import plotly.express as px

SDY4 = Path('module_references/triveni-clin/SDY4')
ZIP = SDY4 / 'SDY4-DR65_Tab.zip'
TAB = SDY4 / 'extracted/SDY4-DR65_Tab/Tab'
CACHE = Path('.cache/triveni-conv')
DB = CACHE / 'sdy4.duckdb'

HINTS = {
    'eosin': 'Eosinophils', 'eosinophil': 'Eosinophils', 'ige': 'Total IgE',
    'leukocyte': 'Leukocytes', 'wbc': 'Leukocytes', 'lymph': 'Lymphocytes',
    'neutro': 'Neutrophils', 'mono': 'Monocytes', 'hsv': 'HSV 1/2 IgG(ELISA) Absolute Result',
    'cd4': 'CD4 positive cells', 'cd8': 'CD8 positive cells', 't cell': 'CD3 positive cells',
    'b cell': 'CD19 positive cells', 'nk': 'CD16 positive/CD56 positive',
}


def unzip():
    if not (TAB / 'lab_test.txt').exists() and ZIP.exists():
        with zipfile.ZipFile(ZIP) as z:
            z.extractall(SDY4 / 'extracted')


def tab(name):
    unzip()
    return pd.read_csv(TAB / f'{name}.txt', sep='\t', dtype=str)


def prepare():
    CACHE.mkdir(parents=True, exist_ok=True)
    if DB.exists():
        return
    arm = tab('arm_or_cohort')
    a2s = tab('arm_2_subject')
    subj = tab('subject')
    bios = tab('biosample')
    lab = tab('lab_test')
    meta = a2s.merge(arm[['ARM_ACCESSION', 'NAME']], on='ARM_ACCESSION', how='left')
    meta = meta.merge(subj[['SUBJECT_ACCESSION', 'GENDER', 'RACE', 'ETHNICITY']], on='SUBJECT_ACCESSION', how='left')
    meta['age'] = pd.to_numeric(meta['MAX_SUBJECT_AGE_IN_YEARS'], errors='coerce')
    meta['ad_case'] = (~meta['NAME'].eq('Healthy controls')).astype(int)
    lab = lab.merge(bios[['BIOSAMPLE_ACCESSION', 'SUBJECT_ACCESSION', 'PLANNED_VISIT_ACCESSION', 'TYPE']], on='BIOSAMPLE_ACCESSION', how='left')
    lab['value'] = pd.to_numeric(lab['RESULT_VALUE_PREFERRED'], errors='coerce')
    df = lab.dropna(subset=['SUBJECT_ACCESSION', 'NAME_REPORTED', 'value']).merge(meta, on='SUBJECT_ACCESSION', how='left')
    df = df.rename(columns={'NAME': 'arm', 'NAME_REPORTED': 'measure', 'value': 'lab_value'})[
        ['SUBJECT_ACCESSION', 'arm', 'ad_case', 'GENDER', 'RACE', 'ETHNICITY', 'age', 'measure', 'lab_value']
    ]
    con = duckdb.connect(DB)
    con.execute('CREATE TABLE subject_lab AS SELECT * FROM df')
    con.execute('CREATE VIEW subject_lab_mean AS SELECT SUBJECT_ACCESSION, arm, ad_case, GENDER, RACE, ETHNICITY, age, measure, avg(lab_value) AS lab_value FROM subject_lab GROUP BY ALL')
    con.close()


def pick_measures(q, con):
    measures = [r[0] for r in con.execute('SELECT DISTINCT measure FROM subject_lab_mean').fetchall()]
    low = q.lower()
    picked = []
    for k, v in HINTS.items():
        if k in low and v in measures and v not in picked:
            picked.append(v)
    for m in sorted(measures, key=len, reverse=True):
        if m.lower() in low and m not in picked:
            picked.append(m)
    return picked


def pick_measure(q, con):
    measures = [r[0] for r in con.execute('SELECT DISTINCT measure FROM subject_lab_mean').fetchall()]
    picked = pick_measures(q, con)
    return picked[0] if picked else ('Eosinophils' if 'Eosinophils' in measures else measures[0])


def wants_plot(q):
    return any(w in q.lower() for w in ['plot', 'chart', 'figure', 'visual', 'boxplot', 'bar chart', 'graph', 'show distribution'])


def answer(q):
    prepare()
    con = duckdb.connect(DB, read_only=True)
    low = q.lower()
    fig = None
    if ('lab' in low or 'measure' in low) and any(w in low for w in ['available', 'list', 'what are', 'show me']):
        sql = "SELECT DISTINCT measure FROM subject_lab_mean ORDER BY measure"
        df = con.execute(sql).df()
        text = f'{len(df)} lab measures are available in SDY4.'
    elif 'scatter' in low:
        picked = pick_measures(q, con)
        x, y = (picked + ['Eosinophils', 'Total IgE'])[:2]
        sx, sy = x.replace("'", "''"), y.replace("'", "''")
        sql = f"""
        SELECT SUBJECT_ACCESSION, arm,
               max(CASE WHEN measure = '{sx}' THEN lab_value END) AS x_value,
               max(CASE WHEN measure = '{sy}' THEN lab_value END) AS y_value
        FROM subject_lab_mean
        WHERE measure IN ('{sx}', '{sy}')
        GROUP BY SUBJECT_ACCESSION, arm
        HAVING x_value IS NOT NULL AND y_value IS NOT NULL
        """
        df = con.execute(sql).df()
        fig = px.scatter(df, x='x_value', y='y_value', color='arm', hover_data=['SUBJECT_ACCESSION'], title=f'{x} vs {y}', labels={'x_value': x, 'y_value': y})
        text = f'Scatter plot for {x} vs {y}.'
    elif 'count' in low or 'cohort' in low or 'subject' in low:
        sql = "SELECT arm, count(DISTINCT SUBJECT_ACCESSION) subjects FROM subject_lab_mean GROUP BY arm ORDER BY subjects DESC"
        df = con.execute(sql).df()
        if wants_plot(q):
            fig = px.bar(df, x='arm', y='subjects', title='SDY4 subjects by arm')
        text = 'Cohort counts by SDY4 arm.'
    elif 'top' in low or 'screen' in low or 'increase' in low or 'decrease' in low or 'altered' in low:
        direction = 'DESC' if 'decrease' not in low else 'ASC'
        sql = f"""
        WITH s AS (
          SELECT measure, ad_case, avg(lab_value) mean_value, count(*) n
          FROM subject_lab_mean GROUP BY measure, ad_case
        ), w AS (
          SELECT c.measure, c.mean_value ad_mean, h.mean_value healthy_mean, c.n ad_n, h.n healthy_n,
                 c.mean_value - h.mean_value difference
          FROM s c JOIN s h ON c.measure=h.measure AND c.ad_case=1 AND h.ad_case=0
        )
        SELECT * FROM w WHERE ad_n>1 AND healthy_n>1 ORDER BY difference {direction} LIMIT 15
        """
        df = con.execute(sql).df()
        if wants_plot(q):
            fig = px.bar(df, x='difference', y='measure', orientation='h', title='AD vs healthy mean difference')
        text = 'Top lab mean differences: AD arms minus healthy controls.'
    else:
        measure = pick_measure(q, con)
        safe = measure.replace("'", "''")
        sql = f"SELECT arm, ad_case, lab_value FROM subject_lab_mean WHERE measure = '{safe}'"
        df = con.execute(sql).df()
        if wants_plot(q):
            fig = px.box(df, x='arm', y='lab_value', color='arm', points='all', title=measure)
        text = f'Distribution rows for {measure} by SDY4 arm.'
    con.close()
    return {
        'text': text,
        'sql': re.sub(r'\s+', ' ', sql).strip(),
        'table': df.head(30),
        'plot': fig.to_html(full_html=False, include_plotlyjs='cdn') if fig else '',
    }


class Handler(BaseHTTPRequestHandler):
    def do_GET(self):
        q = urllib.parse.parse_qs(urllib.parse.urlparse(self.path).query).get('q', ['screen increased labs'])[0]
        try:
            res = answer(q)
            rows = ''.join('<tr>' + ''.join(f'<td>{html.escape(str(v))}</td>' for v in row) + '</tr>' for row in res['table'].itertuples(index=False))
            head = ''.join(f'<th>{html.escape(c)}</th>' for c in res['table'].columns)
            body = f"""<!doctype html><html><head><meta charset='utf-8'><style>
              body{{font-family:system-ui;margin:0;padding:14px;color:#172033}} .bar{{display:flex;gap:8px}} input{{flex:1;padding:8px}} button{{padding:8px 12px;border:2px solid #26315f;border-radius:999px;background:#5b7cfa;color:white}}
              pre{{white-space:pre-wrap;background:#f4f6ff;padding:8px;border-radius:8px}} table{{border-collapse:collapse;width:100%;font-size:12px}} th,td{{border:1px solid #d8ddf2;padding:3px 5px}} th{{background:#edf0ff}} .hint{{font-size:12px;color:#475569;margin:.4rem 0}}
            </style></head><body>
              <form class='bar'><input name='q' value='{html.escape(q)}' autofocus><button>Ask / plot</button></form>
              <div class='hint'>Plotly requests supported: bar chart, boxplot/distribution, scatter plot. Non-plot questions return SQL + table only.</div>
              <p><b>{html.escape(res['text'])}</b></p><pre>{html.escape(res['sql'])}</pre>
              {res['plot']}<table><thead><tr>{head}</tr></thead><tbody>{rows}</tbody></table>
            </body></html>"""
            self.send_response(200); self.send_header('content-type', 'text/html; charset=utf-8'); self.end_headers(); self.wfile.write(body.encode())
        except Exception as e:
            self.send_response(500); self.end_headers(); self.wfile.write(str(e).encode())


if __name__ == '__main__':
    import argparse
    ap = argparse.ArgumentParser(); ap.add_argument('--port', type=int, default=3840); args = ap.parse_args()
    prepare()
    ThreadingHTTPServer(('127.0.0.1', args.port), Handler).serve_forever()
