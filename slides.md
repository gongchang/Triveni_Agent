---
theme: default
title: Data science assisted scientific and clinical decision-making
info: Resume-led deck with prior PowerPoint as secondary source
class: text-left
---

# Bridging Biology, Computation, and AI

## From bioinformatics to agentic AI coding

Zhaojie Zhang, 10/7/2026

---

# Outline

- Educational background and work experience
  - Career Arc: Wet-lab biology, computational genomics, and translational/clinical data science


- Agentic AI coding
  - Beyond vibe coding
  - Live interactive prototype demonstration: cross-functional agents in action
  - Pragmatic realities: trade-offs and prerequisites

---

# Career arc: biology + computation + clinical translation

<div class="card">

## Foundation
- University of Colorado at Boulder
- PhD in Biology: genomics, microRNA's roles in epidermis and hair follicle development
- MS in Computer Science: Machine Learning, databases, Natural Language Processing, cloud, etc.
- Wet-lab + dry-lab fluency

</div>

---

<img src="/work-experiences-slide-1-cropped.png" style="position:absolute; left:0; bottom:-70px; width:100%; opacity:1; z-index:2;" />

<div style="position:relative; z-index:1;">

# St. Jude: clinical genomics at diagnostic scale, 2013–2016

- Data scientist for Genomes for Kids, spanning pediatric hematologic malignancies, solid tumors, and brain tumors
- Built pipelines for SNVs, indels, CNVs, and SVs from WGS/WES/RNA-seq
- Partnered with sequencing labs, pathologists, genetic counselors, and tumor boards

</div>

---

# H3 Biomedicine / Novartis / Moderna, 2016-2025

<div class="grid-3 small">
<div class="card">

## H3 Biomedicine
**Senior Investigator / Investigator II, Data Science and Biomarkers**

- Biomarker and data science lead for ER+/HER2- breast cancer

</div>
<div class="card">

## Novartis
**Associate Director, Data Science, Global Drug Development**

- Biomarker biostatistics for Phase I–III trials

</div>
<div class="card">

## Moderna
**Director, Oncology Clinical & Translational Bioinformatics**

- Translational strategy for individualized neoantigen therapy

</div>
</div>

<div class="card" style="margin-top: 1rem;">

## Through-line
- Omics and biomarker data
- Statistics, causal inference and AI/ML
- Translational Research and Clinical Development

</div>

---

# Experience in different R&D stages

<img src="/work-experiences-slide-2-cropped.png" class="w-full" />

---

# BeOne Medicines: AI-enabled workflows, 2025–Present

<div class="card">

## Director, Data Insights
- Train broader teams on data, databases, ML, and agentic AI
- Drive AI initiatives for analytics, visualization, and workflow automation

</div>

<div class="card">

## Selected projects
- AI-enabled data visualization
   - Medical Data Review Dashboard redesign using AI coding
   - AI/BI dashboard in DataBricks
- Self-service reporting tools
   - Background rate generation of adverse events using Symphony Claims data for pharmacovigilance
- Workflow automation for recurring data tasks
   - Specification-driven Data Management tasks automation
</div>

---

# Why agentic AI coding now?

<div class="grid-2">
<div class="card">

## Noise
- Generic chatbots without grounding
- Demos that cannot touch real workflows
- Models that hallucinate, miscalculate, or go stale

</div>
<div class="card">

## Signal
- RAG over trusted documents
- API/function/tool execution
- Reproducible coding workflows
- Human-reviewed automation for R&D decisions

</div>
</div>

---

# Triveni concept

## Not a chatbot — an extensible operating system for decisions

Triveni pairs scientific strategy with executable agent capabilities:

1. **Ground** answers in curated sources
2. **Act** through APIs, code, databases, and analysis tools
3. **Structure** outputs into reusable artifacts
4. **Surface** uncertainties and caveats


---

# Scientific anchor for the demo

<div class="card">

## Triveni strategy context
- Genetics-informed targets in epithelial barrier disease: **KLK5/7**, **PRSS1**, and related protease biology
- Research & Development: lesion biopsies, biomarkers, patient cohorts, and clinical readouts
- Operations: based on company-specific documents

</div>

---

# Use case 1: People operations

<div class="grid-2">
<div class="card">

## AI dimension
Grounded RAG and policy retrieval

## Scenario
Answer questions over the local employee benefits memo without hallucinating.

</div>
<div class="card">

## What Triveni-agent executes
- Extracts and caches the benefits memo PDF with `pdftotext`
- Retrieves query-specific passages with keyword matching
- Returns “nothing found” when no specific passage matches
- Keeps supported answers short and quotes memo text

</div>
</div>

<TriveniAgent title="/triveni-hr" prompt="/triveni-hr frame reimbursement policy" />

---

# Use case 2: Competitive intelligence

<div class="grid-2">
<div class="card">

## AI dimension
Autonomous surveillance and competitive synthesis

## Scenario
Track competitor clinical reads and patent filings in atopic dermatitis / epithelial barrier disease.

</div>
<div class="card">

## What Triveni-agent executes
- Calls ClinicalTrials.gov, Europe PMC, bioRxiv, and ChEMBL APIs
- Uses flexible query terms and records exact terms used
- Links targets to known assets and drug names to ChEMBL targets
- Returns fixed-width trial/literature/preprint tables with caveats

</div>
</div>

<TriveniAgent title="/triveni-ci" prompt="/triveni-ci KLK5 in atopic dermatitis" />

---

# Use case 3: Biology and translational science

<div class="grid-2">
<div class="card">

## AI dimension
Multi-modal data harmonization and EDA

## Scenario
Explore GTEx tissue expression for related biomarkers.

</div>
<div class="card">

## What Triveni-agent executes
- Parses natural-language GTEx gene/tissue requests
- Runs Python / pandas on GTEx median TPM data
- Generates bar/scatter plots, TUI text plots, CSVs, and PNGs
- Supports top-expression, co-expression, and correlation queries

</div>
</div>

<TriveniAgent title="/triveni-bio" prompt="/triveni-bio box plot of KLK5 and KLK7 expressions in skin and brain tissues" />

---

# Use case 4: Exploratory analysis of clinical data

<div class="grid-2">
<div class="card">

## AI dimension
Clinical data exploration with guardrails

## Scenario
Explore ImmPort SDY4 atopic dermatitis / eczema herpeticum labs against healthy controls.

</div>
<div class="card">

## What Triveni-agent executes
- Loads ImmPort SDY4 AD / eczema herpeticum lab tables
- Compares all AD arms vs healthy controls for requested measures
- Reports means, differences, SMDs, Welch p-values, and BH-FDR
- Filters to increased or decreased markers when requested

</div>
</div>

<TriveniAgent title="/triveni-clin" prompt="/triveni-clin all labs increased in eczema vs healthy controls" />

---

# Use case 5: Interactive clinical EDA dashboard

<div class="grid-2">
<div class="card">

## AI dimension
Natural-language launch into deterministic analytics UI

## Scenario
Move from a `/triveni-clin` text summary into an interactive SDY4 lab dashboard for live review.

</div>
<div class="card">

## What Triveni-agent executes
- Launches a local R Shiny app from `/triveni-eda`
- Embeds the dashboard directly inside Slidev
- Lets reviewers choose lab measures, plot type, and AD arm grouping
- Keeps raw clinical tables local while showing plots and screening tables

</div>
</div>

<TriveniEda />

---

# Use case 6: Conversational clinical analytics

<div class="grid-2">
<div class="card">

## AI dimension
Natural-language analytics backed by deterministic SQL

## Scenario
Ask SDY4 lab questions, inspect DuckDB SQL, and review Plotly charts in the deck.

</div>
<div class="card">

## What Triveni-agent executes
- Launches `/triveni-conv` as a local Python web app
- Builds a DuckDB table over SDY4 subject-level labs
- Converts common clinical questions into SQL templates
- Renders cohort counts, lab screens, and measure plots with Plotly

</div>
</div>

<TriveniConv />

---

# Live interaction slide

Triveni agent: conversational intent to validated execution. Showcase triveni agent tool uses, browser use with triveni-assist, and communication with Telegram.

<TriveniAgent title="Live Triveni-agent command" ABC prompt="/triveni" />

---

# Triveni extension architecture

<div class="arch-small">

```mermaid
flowchart TB
  Q["User / Slidev / Telegram"] --> R["/triveni router"]
  R --> HR["HR RAG: PDF text"]
  R --> CI["CI APIs: trials + literature"]
  R --> BIO["Bio: GTEx Python"]
  R --> CLIN["Clin: SDY4 Python"]
  R --> EDA["EDA: R Shiny iframe"]
  R --> CONV["Conv: DuckDB + Plotly iframe"]
  R --> GMAIL["Gmail: Ego browser"]
  HR --> A["Grounded answer"]
  CI --> A
  BIO --> A
  CLIN --> A
  GMAIL --> A
  EDA --> W["Deterministic web app"]
  CONV --> V["Interactive artifact"]
```

</div>

---

# Closing

## The goal is not replacing expertise.

It is to make expertise **faster, more traceable, and more reusable** across the enterprise.

<div class="triveni">Triveni = grounded reasoning + executable tools + scientific judgment by humans</div>

---

# Decision Matrix: Apps vs. Hybrid vs. Agents

<div class="matrix-scroll">

| Dimension | Deterministic Web Apps | Hybrid: Tools + LLM Interface | Autonomous Multi-Step Agents |
|---|---|---|---|
| Primary mechanism | Static, pre-compiled business logic; same code path every run. | Natural-language interface maps intent into pre-defined tool calls. | Dynamic reasoning loops, self-correction, runtime tool chaining, task planning. |
| Output predictability | 100% deterministic. Identical inputs yield identical outputs. | High. Model drafts query/tool args; backend execution is deterministic. | Stochastic. Format and reasoning path can vary between runs. |
| Data sensitivity & privacy | Zero egress risk inside VPC, DuckDB, or lakehouse boundaries. | Controllable. LLM sees metadata/schema; raw records stay local. | Higher governance surface: context may carry sequences, assay, or clinical data. |
| Regulatory & audit traceability | Strong Part 11 fit: fixed code paths, deterministic logs, static tests. | Audit-friendly: intent and generated payloads are logged before execution. | Complex trail: loops, hidden branching, and dynamic context complicate compliance. |
| Workflow flexibility | Rigid: dropdowns, sliders, defined routes. | Semi-flexible: open questions constrained to mapped APIs. | Maximum: open-ended, ambiguous, multi-hop tasks without pre-coded paths. |
| Compute & ops cost | Negligible fixed server/database costs. | Low: usually 1–2 LLM calls plus tool execution. | High and variable: tokens, retries, tool calls, replanning. |

</div>

---

# Readiness Matrix: AI Coding & Agentic Workflows

<div class="matrix-scroll">

| Layer | Prerequisite metric | Not ready | AI-ready threshold | Triveni action |
|---|---|---|---|---|
| 1. Data structure & schemas | Semantic uniformity and typed schemas | Heterogeneous Excel sheets, merged cells, inconsistent gene names, free-text notes. | Structured JSON/Parquet/relational tables with unique IDs and strict types. | Enforce Pydantic or DuckDB contracts for lab assays and IC50 fits before LLM use. |
| 2. Data access & connectivity | Programmable read APIs | Data trapped in GUIs, vendor portals, ELN systems, or local drives. | Headless REST/GraphQL, object storage, or read-only database replicas. | Mount lakehouse/bucket paths such as S3 or Unity Catalog for programmatic reads. |
| 3. Domain business logic | Deterministic algorithmic baseline | Scientific logic lives in heads or unannotated scripts with hard-coded paths. | Core calculations are unit-tested callable functions. | Refactor biologics triage and biometrics QC into importable Python/R packages. |
| 4. Context & metadata | Curated knowledge stores for RAG | Raw 100-page PDFs without metadata tags or chunk boundaries. | Chunked indexed stores with versioning, dates, and category tags. | Chunk HR policies and SAPs with metadata like `effective_year` and `category`. |
| 5. Evaluation & guardrails | Automated benchmark harness | Manual eyeballing of a few cherry-picked outputs. | Golden test set with programmatic regression scoring. | Build reference antibody and trial-endpoint cases to score agent accuracy. |
| 6. Security & governance | Zero-retention private tenant boundaries | Proprietary sequences, trial designs, or employee data pasted into public LLMs. | Enterprise zero-retention contracts and PII redaction. | Route requests through an enterprise VPC proxy and secure model boundary. |

</div>

---

# Thank you for coming!

<div class="ai-storm">
  <div class="ground">Biology <span>(Domain Knowledge)</span> + Computation <span>(Tools)</span></div>
  <div class="person">
    <div class="head">🙂</div>
    <div class="body"></div>
    <div class="legs"></div>
  </div>
  <div class="ball" style="--i:0;--y:40px">Harness</div>
  <div class="ball" style="--i:1;--y:105px">Hooks</div>
  <div class="ball" style="--i:2;--y:170px">MCPs</div>
  <div class="ball" style="--i:3;--y:235px">AI SDKs</div>
  <div class="ball" style="--i:4;--y:300px">Models</div>
  <div class="ball" style="--i:5;--y:315px">LLMs</div>
  <div class="ball" style="--i:6;--y:75px">AI</div>
  <div class="ball" style="--i:7;--y:140px">More AI models</div>
  <div class="ball" style="--i:8;--y:205px">Another new model</div>
  <div class="ball" style="--i:9;--y:270px">Another new Harness</div>
  <div class="ball" style="--i:10;--y:290px">Another AI concept</div>
  <div class="ball" style="--i:11;--y:320px">Another AI Jargon</div>
  <div class="ball" style="--i:12;--y:52px">New AI jargon</div>
  <div class="ball" style="--i:13;--y:118px">New AI model</div>
  <div class="ball" style="--i:14;--y:184px">New AI jargon</div>
  <div class="ball" style="--i:15;--y:250px">New AI model</div>
  <div class="ball" style="--i:16;--y:305px">New AI jargon</div>
  <div class="ball" style="--i:17;--y:330px">New AI model</div>
  <div class="ball" style="--i:18;--y:95px">Loops</div>
  <div class="ball" style="--i:19;--y:160px">Contexts</div>
  <div class="ball" style="--i:20;--y:225px">Memory</div>
  <div class="ball" style="--i:21;--y:285px">HeartBeat</div>
  <div class="ball" style="--i:22;--y:345px">Orchestration</div>
  <div class="ball" style="--i:23;--y:70px">Skills</div>
  <div class="ball" style="--i:24;--y:135px">Claude</div>
  <div class="ball" style="--i:25;--y:200px">GPT</div>
  <div class="ball" style="--i:26;--y:265px">Codex</div>
</div>
