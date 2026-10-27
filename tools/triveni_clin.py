#!/usr/bin/env python3
import argparse, json, zipfile
from pathlib import Path

import numpy as np
import pandas as pd
from scipy import stats
import statsmodels.formula.api as smf

NHANES = Path('module_references/triveni-clin/nhanes_2015_2016_merged.parquet')
SDY4 = Path('module_references/triveni-clin/SDY4')
SDY4_ZIP = SDY4 / 'SDY4-DR65_Tab.zip'
SDY4_TAB = SDY4 / 'extracted/SDY4-DR65_Tab/Tab'
CACHE = Path('.cache/triveni-clin')

PHENOTYPES = {
    'asthma': {'var': 'MCQ010', 'label': 'Ever told you have asthma', 'yes': 1, 'no': 2},
    'current asthma': {'var': 'MCQ035', 'label': 'Still have asthma', 'yes': 1, 'no': 2},
    'hay fever': {'var': 'AGQ030', 'label': 'Hay fever episode in past year', 'yes': 1, 'no': 2},
    'allergic rhinitis': {'var': 'AGQ030', 'label': 'Hay fever episode in past year (allergic rhinitis proxy)', 'yes': 1, 'no': 2},
}

NHANES_LABS = {
    'LBDEONO': 'Absolute eosinophils (1000 cells/uL)', 'LBXEOPCT': 'Eosinophils percent',
    'LBXWBCSI': 'White blood cell count', 'LBXHGB': 'Hemoglobin', 'LBXGH': 'HbA1c',
    'LBXTC': 'Total cholesterol', 'LBDHDD': 'HDL cholesterol', 'LBXCOT': 'Serum cotinine',
    'LBXSCR': 'Creatinine', 'LBXSATSI': 'ALT', 'LBXSASSI': 'AST',
}

SDY4_LAB_HINTS = {
    'eosin': ['Eosinophils', 'Eosinophils percentage'],
    'ige': ['Total IgE'],
    'cbc': ['Leukocytes', 'Lymphocytes', 'Neutrophils', 'Monocytes', 'Eosinophils'],
    't cell': ['CD3 positive cells', 'CD4 positive cells', 'CD8 positive cells'],
    'b cell': ['CD19 positive cells'],
    'nk': ['CD16 positive/CD56 positive'],
    'hsv': ['HSV 1/2 IgG(ELISA) Absolute Result', 'HSV 1/2 IgM(ELISA) Absolute Result'],
}


def smd(a, b):
    pooled = np.sqrt((np.nanvar(a, ddof=1) + np.nanvar(b, ddof=1)) / 2)
    return np.nan if pooled == 0 else (np.nanmean(a) - np.nanmean(b)) / pooled


def sd4_unzip():
    if not (SDY4_TAB / 'lab_test.txt').exists() and SDY4_ZIP.exists():
        with zipfile.ZipFile(SDY4_ZIP) as z:
            z.extractall(SDY4 / 'extracted')


def read_tab(name):
    sd4_unzip()
    return pd.read_csv(SDY4_TAB / f'{name}.txt', sep='\t', dtype=str)


def choose_sdy4_labs(q, available):
    q = q.lower()
    if any(x in q for x in ['all lab', 'all measures', 'altered lab', 'increased lab', 'increase lab', 'screen']):
        return sorted(available)
    labs = []
    for key, vals in SDY4_LAB_HINTS.items():
        if key in q:
            labs += vals
    if not labs:
        labs = ['Eosinophils', 'Eosinophils percentage', 'Leukocytes', 'Lymphocytes', 'Neutrophils', 'Monocytes', 'Total IgE']
    return [x for x in dict.fromkeys(labs) if x in available]


def bh_fdr(pvals):
    p = pd.Series(pvals, dtype='float64')
    out = pd.Series(np.nan, index=p.index)
    ok = p.dropna().sort_values()
    if ok.empty:
        return out
    m = len(ok)
    q = ok * m / np.arange(1, m + 1)
    q = q[::-1].cummin()[::-1].clip(upper=1)
    out.loc[q.index] = q
    return out


def sdy4_analysis(question):
    arm = read_tab('arm_or_cohort')
    a2s = read_tab('arm_2_subject')
    subj = read_tab('subject')
    bios = read_tab('biosample')
    lab = read_tab('lab_test')

    meta = a2s.merge(arm[['ARM_ACCESSION', 'NAME']], on='ARM_ACCESSION', how='left')
    meta = meta.merge(subj[['SUBJECT_ACCESSION', 'GENDER', 'RACE', 'ETHNICITY']], on='SUBJECT_ACCESSION', how='left')
    meta['age'] = pd.to_numeric(meta['MAX_SUBJECT_AGE_IN_YEARS'], errors='coerce')
    meta['ad_case'] = (~meta['NAME'].eq('Healthy controls')).astype(int)
    demographics = {
        'age_mean_by_group': meta.groupby('NAME')['age'].mean().round(2).to_dict(),
        'sex_by_group': meta.groupby('NAME')['GENDER'].value_counts(dropna=False).unstack(fill_value=0).to_dict(),
        'race_by_group': meta.groupby('NAME')['RACE'].value_counts(dropna=False).unstack(fill_value=0).to_dict(),
    }

    lab = lab.merge(bios[['BIOSAMPLE_ACCESSION', 'SUBJECT_ACCESSION', 'PLANNED_VISIT_ACCESSION', 'TYPE']], on='BIOSAMPLE_ACCESSION', how='left')
    lab['value'] = pd.to_numeric(lab['RESULT_VALUE_PREFERRED'], errors='coerce')
    lab = lab.dropna(subset=['SUBJECT_ACCESSION', 'NAME_REPORTED', 'value'])
    available = set(lab['NAME_REPORTED'])
    labs = choose_sdy4_labs(question, available)

    rows = []
    for lab_name in labs:
        x = lab[lab.NAME_REPORTED.eq(lab_name)].merge(meta, on='SUBJECT_ACCESSION', how='left')
        # average repeated biosamples per subject/lab for quick subject-level screen
        s = x.groupby(['SUBJECT_ACCESSION', 'ad_case'], as_index=False)['value'].mean()
        case = s.loc[s.ad_case == 1, 'value'].dropna()
        ctrl = s.loc[s.ad_case == 0, 'value'].dropna()
        p = stats.ttest_ind(case, ctrl, equal_var=False).pvalue if len(case) > 1 and len(ctrl) > 1 else np.nan
        rows.append({
            'measure': lab_name,
            'case_n': int(len(case)), 'control_n': int(len(ctrl)),
            'case_missing_n': int(meta.ad_case.sum() - len(case)),
            'control_missing_n': int((1 - meta.ad_case).sum() - len(ctrl)),
            'ad_mean': float(case.mean()) if len(case) else None,
            'healthy_mean': float(ctrl.mean()) if len(ctrl) else None,
            'difference': float(case.mean() - ctrl.mean()) if len(case) and len(ctrl) else None,
            'direction': 'increased_in_ad' if len(case) and len(ctrl) and case.mean() > ctrl.mean() else ('decreased_in_ad' if len(case) and len(ctrl) else 'not_comparable'),
            'smd': float(smd(case, ctrl)) if len(case) > 1 and len(ctrl) > 1 else None,
            'welch_p': float(p) if pd.notna(p) else None,
        })
    out = pd.DataFrame(rows)
    if not out.empty:
        out['fdr_bh'] = bh_fdr(out['welch_p'])
        out['abs_smd'] = out['smd'].abs()
        out = out.sort_values(['fdr_bh', 'abs_smd'], ascending=[True, False], na_position='last')
    csv = CACHE / 'last_sdy4_eda.csv'
    out.to_csv(csv, index=False)

    cohort = meta['NAME'].value_counts().to_dict()
    return {
        'dataset': 'ImmPort SDY4 atopic dermatitis / eczema herpeticum study',
        'analysis': 'sdy4_ad_vs_healthy_lab_comparison',
        'comparison': 'All AD arms vs Healthy controls',
        'cohort_counts': cohort,
        'subjects': int(meta.SUBJECT_ACCESSION.nunique()),
        'demographics_qc': demographics,
        'available_lab_measures_examples': sorted(list(available))[:80],
        'selected_measures': labs,
        'result_csv': str(csv),
        'results': out.to_dict(orient='records'),
        'best_practice_caveats': [
            'Exploratory observational comparison; not causal.',
            'Repeated biosamples for the same subject/lab are averaged for this quick screen.',
            'Welch tests are unadjusted; Benjamini-Hochberg FDR is included for screening, not confirmation.',
            'Review missingness columns before interpreting any measure.',
            'Follow-up analysis should model AD subgroups, visit, age, sex, race, and missingness explicitly.',
        ],
    }


def nhanes_analysis(question):
    q = question.lower()
    spec = None
    for key, val in PHENOTYPES.items():
        if key in q:
            spec = val
            break
    if spec is None:
        spec = PHENOTYPES['asthma']
    df = pd.read_parquet(NHANES)
    pheno = spec['var']
    d = df[df[pheno].isin([spec['yes'], spec['no']])].copy()
    d['case'] = (d[pheno] == spec['yes']).astype(int)
    labs = ['LBDEONO', 'LBXEOPCT', 'LBXWBCSI'] if 'eosin' in q else list(NHANES_LABS)
    rows = []
    for lab in [c for c in labs if c in d]:
        x = pd.to_numeric(d.loc[d.case == 1, lab], errors='coerce').dropna()
        y = pd.to_numeric(d.loc[d.case == 0, lab], errors='coerce').dropna()
        p = stats.ttest_ind(x, y, equal_var=False).pvalue if len(x) > 1 and len(y) > 1 else np.nan
        adj_beta = adj_p = np.nan
        model_df = d[['case', lab, 'RIDAGEYR', 'RIAGENDR', 'RIDRETH3']].dropna().copy()
        if len(model_df) > 30 and model_df.case.nunique() == 2:
            fit = smf.ols(f'Q("{lab}") ~ case + RIDAGEYR + C(RIAGENDR) + C(RIDRETH3)', data=model_df).fit()
            adj_beta, adj_p = fit.params.get('case', np.nan), fit.pvalues.get('case', np.nan)
        rows.append({'lab': lab, 'label': NHANES_LABS.get(lab, lab), 'case_n': int(len(x)), 'control_n': int(len(y)), 'case_mean': float(x.mean()), 'control_mean': float(y.mean()), 'difference': float(x.mean() - y.mean()), 'smd': float(smd(x, y)), 'welch_p': float(p) if pd.notna(p) else None, 'age_sex_race_adjusted_beta': float(adj_beta) if pd.notna(adj_beta) else None, 'age_sex_race_adjusted_p': float(adj_p) if pd.notna(adj_p) else None})
    out = pd.DataFrame(rows).sort_values('welch_p', na_position='last')
    csv = CACHE / 'last_nhanes_eda.csv'
    out.to_csv(csv, index=False)
    return {'dataset': str(NHANES), 'analysis': 'nhanes_observational_lab_comparison', 'phenotype': spec, 'cohort_n': int(len(d)), 'case_n': int(d.case.sum()), 'control_n': int((1-d.case).sum()), 'result_csv': str(csv), 'results': out.to_dict(orient='records'), 'best_practice_caveats': ['Exploratory observational comparison; not causal.', 'NHANES survey weights/design are not applied in this quick screen.', 'Adjusted beta uses simple OLS adjusted for age, sex, and race/ethnicity.']}


def main():
    ap = argparse.ArgumentParser()
    ap.add_argument('question')
    args = ap.parse_args()
    CACHE.mkdir(parents=True, exist_ok=True)
    print(json.dumps(sdy4_analysis(args.question), indent=2))


if __name__ == '__main__':
    main()
