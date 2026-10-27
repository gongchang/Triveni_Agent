# Triveni agent plan

## Goal
Create a pi-based agent named **Triveni** with slash modules that demonstrate enterprise-scale agentic AI grounded in Triveni's scientific strategy: KLK5/7, PRSS1, antibody engineering, and translational I&I biology.

## Implemented slash modules

| Command | Function | Capability | Output pattern |
|---|---|---|---|
| `/triveni` | Help | Lists available modules | Command menu |
| `/triveni-ci <query>` | Competitive Intelligence | Live landscape lookup through ClinicalTrials.gov, Europe PMC, and bioRxiv APIs | Competitor / evidence matrix vs TRIV-509 or TRIV-920 with sources and caveats |
| `/triveni-hr <question>` | People Operations | Grounded RAG over `module_references/triveni-hr/Triveni Bio 2025-26 Employee Benefits Memo.pdf` | Exact memo quotes, page citations, short answer, missing-evidence note |
| `/triveni-bio <question>` | Biology / Translational Science | Natural-language GTEx expression Q&A and plotting | Median TPM summaries, top tissues, CSV and PNG artifacts, interpretation caveats |
| `/triveni-clin <question>` | Clinical / Observational EDA | ImmPort SDY4 atopic dermatitis / eczema herpeticum lab exploration | AD-vs-healthy lab summaries, SMDs, Welch tests, caveats |

## Current implementation
- `extensions/triveni.ts` registers the slash commands.
- Each command sends a structured prompt into pi with the correct role, scenario, execution checklist, grounding rules, and scientific-strategy anchor.
- `/triveni-ci` selects TRIV-509 vs TRIV-920 from the query, fetches ClinicalTrials.gov, Europe PMC, and recent bioRxiv evidence, then asks pi to synthesize a sourced landscape matrix.
- `/triveni-hr` extracts the benefits PDF with `pdftotext`, caches text in `.cache/triveni-hr-benefits.txt`, retrieves top keyword-matched chunks, and instructs pi to answer only from retrieved evidence.
- `/triveni-bio` calls `tools/triveni_bio.py`, parses natural-language gene/tissue requests, analyzes GTEx median TPM data, and writes `.cache/triveni-bio/last_result.csv` plus `.cache/triveni-bio/last_plot.png` when plotting is requested.
- `/triveni-clin` calls `tools/triveni_clin.py`, analyzes ImmPort SDY4 tab files under `module_references/triveni-clin/SDY4`, and writes `.cache/triveni-clin/last_sdy4_eda.csv`.
- The embedded Slidev pi TUI can load this extension so slash commands work in the deck.

## Next minimal additions
1. Add real source connectors only when data locations are known.
2. Replace HR keyword retrieval with embeddings/vector search if the corpus grows beyond a few PDFs.
3. Add a sample biomarker dataset/notebook if a live EDA demo is needed.
