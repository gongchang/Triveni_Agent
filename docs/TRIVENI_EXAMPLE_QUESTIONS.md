# Triveni-agent example questions

## `/triveni` — auto-router

Use when you do not want to choose a module manually. It routes the question to `/triveni-ci`, `/triveni-hr`, `/triveni-bio`, or `/triveni-clin`.

Examples:

```text
/triveni what is the lens policy?
/triveni which tissues expressed the highest levels of KLK5 and KLK7?
/triveni screen all labs increased in eczema vs healthy controls
/triveni disease landscape for epithelial barrier dysfunction and kallikrein biology
```


## `/triveni-ci` — CI / target / competitor landscape

Use for quick public-source lookup around Triveni target spaces.

Examples:

```text
/triveni-ci list all the APIs I am using
/triveni-ci TRIV-509 AD KLK5 KLK7 competitor landscape
/triveni-ci clinical trials for KLK5 KLK7 kallikrein Netherton atopic dermatitis
/triveni-ci target biology landscape for KLK5 KLK7 SPINK5 LEKTI
/triveni-ci TRIV-920 pancreatitis PRSS1 trypsin clinical landscape
/triveni-ci disease landscape for epithelial barrier dysfunction and kallikrein biology
```

Current live sources:

- ClinicalTrials.gov API v2
- Europe PMC REST API
- bioRxiv public API

Planned future sources:

- WHO ICTRP
- PatentsView / USPTO
- OpenFDA

## `/triveni-hr` — HR benefits memo RAG

Uses the local benefits memo PDF.

Examples:

```text
/triveni-hr lens policy
/triveni-hr frame reimbursement policy
/triveni-hr who is eligible for benefits?
/triveni-hr when is open enrollment?
/triveni-hr are domestic partners covered?
/triveni-hr what is the difference between HMO and EPO?
```

## `/triveni-bio` — GTEx expression analysis

Uses GTEx median TPM by tissue.

Examples:

```text
/triveni-bio which tissues expressed the highest levels of KLK5 and KLK7?
/triveni-bio plot KLK5 and KLK7 expressions in skin
/triveni-bio scatter plot KLK5 and KLK7 expressions in all tissues
/triveni-bio scatter plot KLK5 and KLK7 expressions in skin, lung and brain tissues
/triveni-bio which genes are negatively correlated with TP63 in expressions?
/triveni-bio which genes are positively correlated with KLK5 and expressed higher than KLK5 in skin?
```

## `/triveni-clin` — SDY4 clinical exploratory data analysis

Uses ImmPort SDY4 atopic dermatitis / eczema herpeticum data.

Examples:

```text
/triveni-clin screen all labs increased in eczema vs healthy controls
/triveni-clin explore whether people with eczema have altered eosinophils and IgE than healthy controls
/triveni-clin compare CBC measures between atopic dermatitis and healthy controls
/triveni-clin compare T cell and B cell measures between AD and healthy controls
/triveni-clin explore HSV serology in AD subgroups
/triveni-clin screen all measures for AD vs healthy controls
```

Interpretation caveats:

- Exploratory only, not causal.
- Repeated biosamples are averaged in quick screens.
- Welch tests and FDR are screening tools, not confirmatory analysis.
- Follow-up should model AD subgroup, visit, age, sex, race, and missingness.
