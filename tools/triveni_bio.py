#!/usr/bin/env python3
import argparse, json, re
from pathlib import Path

import pandas as pd

DATA = Path('module_references/triveni-bio/GTEx_Analysis_2017-06-05_v8_RNASeQCv1.1.9_gene_median_tpm.gct')
CACHE = Path('.cache/triveni-bio')

DEFAULT_GENES = ['KLK5', 'KLK7', 'PRSS1', 'PRSS2', 'F2RL1', 'TSLP']  # F2RL1 = PAR2
ALIASES = {'PAR2': 'F2RL1'}


def load():
    df = pd.read_csv(DATA, sep='\t', skiprows=2)
    df = df.rename(columns={'Name': 'gene_id', 'Description': 'gene'})
    return df


def parse(question, tissues, gene_set):
    words = re.findall(r'[A-Za-z][A-Za-z0-9-]*', question.upper())
    genes = []
    for w in words:
        g = ALIASES.get(w, w)
        if g in gene_set:
            genes.append(g)
    genes = list(dict.fromkeys(genes)) or DEFAULT_GENES[:4]

    q = question.lower()
    parts = [p for p in re.split(r'[,; ?]+', q) if len(p) > 3]
    picked = [t for t in tissues if any(part in t.lower() for part in parts)]
    groups = {
        'skin': 'skin',
        'blood': 'blood',
        'pancreas': 'pancreas',
        'pancreatic': 'pancreas',
        'lung': 'lung',
        'brain': 'brain',
    }
    requested = [needle for key, needle in groups.items() if key in q]
    if requested:
        picked = [t for t in tissues if any(needle in t.lower() for needle in requested)]
    return genes, picked or tissues


def ascii_scatter(points, x, y, width=48, height=16):
    xmax = max(points[x].max(), 1)
    ymax = max(points[y].max(), 1)
    grid = [[' ' for _ in range(width)] for _ in range(height)]
    for _, r in points.iterrows():
        col = min(width - 1, round((r[x] / xmax) * (width - 1)))
        row = height - 1 - min(height - 1, round((r[y] / ymax) * (height - 1)))
        grid[row][col] = '•'
    lines = [f"{y} TPM"]
    lines += ['│' + ''.join(row) for row in grid]
    lines.append('└' + '─' * width)
    lines.append(f"  {x} TPM  (each dot = tissue)")
    return '\n'.join(lines)


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('question')
    args = ap.parse_args()

    CACHE.mkdir(parents=True, exist_ok=True)
    df = load()
    tissues = [c for c in df.columns if c not in ('gene_id', 'gene')]
    genes, picked = parse(args.question, tissues, set(df.gene.astype(str)))

    csv_path = CACHE / 'last_result.csv'
    png_path = CACHE / 'last_plot.png'
    q = args.question.lower()

    if 'correlat' in q or 'corrlat' in q:
        targets = genes or ['KLK5', 'KLK7']
        corr_cols = tissues if ('higher than' in q or len(picked) < 3) else picked
        mat = df[['gene_id', 'gene'] + corr_cols].drop_duplicates('gene')
        target_rows = mat[mat.gene.isin(targets)].set_index('gene')
        if len(target_rows) < len(targets):
            print(json.dumps({'error': f'Missing target genes: {targets}'}))
            return
        import numpy as np
        x = mat[corr_cols].to_numpy(dtype=float)
        x = x - x.mean(axis=1, keepdims=True)
        x_norm = np.linalg.norm(x, axis=1)
        rows = []
        for target in targets:
            y = target_rows.loc[target, corr_cols].to_numpy(dtype=float)
            y = y - y.mean()
            denom = x_norm * np.linalg.norm(y)
            rows.append(np.divide(x @ y, denom, out=np.full(len(mat), np.nan), where=denom != 0))
        corr = pd.DataFrame({target: rows[i] for i, target in enumerate(targets)})
        corr.insert(0, 'gene', mat['gene'].values)
        corr = corr[~corr.gene.isin(targets)].dropna()
        if 'negative' in q or 'negatively' in q:
            result = corr[(corr[targets] < 0).all(axis=1)].copy()
            result['mean_corr'] = result[targets].mean(axis=1)
            result = result.sort_values('mean_corr')
        elif 'positive' in q or 'positively' in q:
            result = corr[(corr[targets] > 0).all(axis=1)].copy()
            result['mean_corr'] = result[targets].mean(axis=1)
            result = result.sort_values('mean_corr', ascending=False)
        else:
            result = corr.copy()
            result['mean_corr'] = result[targets].mean(axis=1)
            result = result.reindex(result['mean_corr'].abs().sort_values(ascending=False).index)
        if 'higher than' in q:
            expr = df[['gene'] + picked].drop_duplicates('gene').set_index('gene')
            target_expr = expr.loc[targets[0], picked].mean()
            result['mean_tpm_in_selected_tissues'] = result['gene'].map(expr[picked].mean(axis=1))
            result[f'{targets[0]}_mean_tpm_in_selected_tissues'] = target_expr
            result = result[result['mean_tpm_in_selected_tissues'] > target_expr]
        result = result.head(20)
        out = result
        out.to_csv(csv_path, index=False)
        print(json.dumps({
            'dataset': str(DATA),
            'analysis': 'gene_expression_correlation_across_tissues',
            'targets': targets,
            'tissues_searched': len(corr_cols),
            'expression_filter_tissues': picked if 'higher than' in q else None,
            'result_csv': str(csv_path),
            'plot_png': None,
            'tui_plot': None,
            'top_correlations': out.to_dict(orient='records'),
            'caveat': 'Correlations use GTEx tissue-level median TPM across tissues, not sample-level patient data.',
        }, indent=2))
        return

    sub = df[df.gene.isin(genes)][['gene_id', 'gene'] + picked].copy()
    if sub.empty:
        print(json.dumps({'error': f'No requested genes found: {genes}'}))
        return

    long = sub.melt(id_vars=['gene_id', 'gene'], var_name='tissue', value_name='median_tpm')
    top = long.sort_values('median_tpm', ascending=False).groupby('gene').head(5)
    long.to_csv(csv_path, index=False)

    ascii_plot = None
    if any(w in q for w in ['plot', 'chart', 'bar', 'visual', 'figure', 'graph']):
        import matplotlib.pyplot as plt
        if 'scatter' in q and len(genes) >= 2:
            x, y = genes[:2]
            wide = long.pivot(index='tissue', columns='gene', values='median_tpm').reset_index()
            plot_df = wide.dropna(subset=[x, y]).copy()
            plot_df['coexpression_score'] = plot_df[x] * plot_df[y]
            plot_df.sort_values('coexpression_score', ascending=False).to_csv(csv_path, index=False)

            fig, ax = plt.subplots(figsize=(7, 5))
            ax.scatter(plot_df[x], plot_df[y])
            for _, r in plot_df.nlargest(5, 'coexpression_score').iterrows():
                ax.annotate(r['tissue'].replace(' - ', '\n'), (r[x], r[y]), fontsize=7)
            ax.set_xlabel(f'{x} GTEx median TPM')
            ax.set_ylabel(f'{y} GTEx median TPM')
            ax.set_title(f'{x} vs {y} across GTEx tissues')
            fig.tight_layout()
            fig.savefig(png_path, dpi=160)
            plt.close(fig)

            leaders = [f"Top co-expressing tissues ({x} x {y}):"]
            for _, r in plot_df.nlargest(6, 'coexpression_score').iterrows():
                leaders.append(f"{r['tissue'][:42]:<42} {x}={r[x]:>7.2f}  {y}={r[y]:>7.2f}")
            ascii_plot = ascii_scatter(plot_df, x, y) + "\n\n" + "\n".join(leaders)
        else:
            plot_df = long.sort_values('median_tpm', ascending=False).groupby('gene').head(8)
            fig, ax = plt.subplots(figsize=(10, max(4, 0.32 * len(plot_df))))
            labels = plot_df['gene'] + ' — ' + plot_df['tissue']
            ax.barh(labels, plot_df['median_tpm'])
            ax.invert_yaxis()
            ax.set_xlabel('GTEx median TPM')
            ax.set_title('Top GTEx tissue expression by gene')
            fig.tight_layout()
            fig.savefig(png_path, dpi=160)
            plt.close(fig)

            max_v = max(plot_df['median_tpm'].max(), 1)
            lines = []
            for _, r in plot_df.iterrows():
                bar = '█' * max(1, round(36 * r['median_tpm'] / max_v))
                lines.append(f"{r['gene']:<7} {r['tissue'][:36]:<36} {r['median_tpm']:>8.2f} {bar}")
            ascii_plot = "\n".join(lines)
    else:
        png_path = None

    print(json.dumps({
        'dataset': str(DATA),
        'genes': genes,
        'tissues_searched': len(picked),
        'result_csv': str(csv_path),
        'plot_png': str(png_path) if png_path else None,
        'tui_plot': ascii_plot,
        'top_expression': top.to_dict(orient='records'),
    }, indent=2))


if __name__ == '__main__':
    main()
