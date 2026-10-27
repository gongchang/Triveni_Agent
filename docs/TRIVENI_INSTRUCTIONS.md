# Triveni instructions

## Run Triveni independently

From the project folder:

```bash
cd /Users/xingyuli/Documents/Zhaojie/Coding/Triveni_Agent

pi --approve \
  --extension ./extensions/triveni.ts \
  --provider openai-codex \
  --model gpt-5.5 \
  --session-id triveni-test
```

Then use slash commands:

```text
/triveni
/triveni-ci TRIV-509 AD KLK5 KLK7 competitor landscape
/triveni-ci TRIV-920 pancreatitis PRSS1 trypsin landscape
/triveni-hr Who is eligible for benefits?
/triveni-hr What is the frame reimbursement policy?
/triveni-bio which genes are positively corrlated with KLK5 and expressed higher than KLK5 in expressions in skin?
/triveni-bio where is PRSS1 highest?
/triveni-clin explore whether people with eczema have altered eosinophils and IgE than healthy controls
/triveni-clin compare CBC measures between atopic dermatitis and healthy controls
/triveni-clin compare T cell and B cell measures between AD and healthy controls
/triveni-clin explore allergen IgE measures in SDY4
```

## Run inside Slidev

```bash
cd /Users/xingyuli/Documents/Zhaojie/Coding/Triveni_Agent
lsof -tiTCP:18787 -sTCP:LISTEN | xargs kill -9 2>/dev/null || true
npm run dev
```

Open the **Live pi TUI** slide and use the same slash commands.

## Current modules

| Command | Purpose | Data/tools |
|---|---|---|
| `/triveni` | List modules | pi command notification |
| `/triveni-ci <query>` | CI landscape lookup for TRIV-509 or TRIV-920 | ClinicalTrials.gov, Europe PMC, bioRxiv |
| `/triveni-hr <question>` | Benefits memo Q&A | `module_references/triveni-hr/Triveni Bio 2025-26 Employee Benefits Memo.pdf` via cached text retrieval |
| `/triveni-bio <question>` | Biology/translational GTEx expression Q&A and plotting | `module_references/triveni-bio/GTEx_Analysis_2017-06-05_v8_RNASeQCv1.1.9_gene_median_tpm.gct`, Python/pandas/matplotlib |
| `/triveni-clin <question>` | ImmPort SDY4 atopic dermatitis observational clinical EDA | `module_references/triveni-clin/SDY4/SDY4-DR65_Tab.zip`, Python/pandas/scipy |

## Develop a new module

Edit:

```text
extensions/triveni.ts
```

Minimal pattern:

```ts
pi.registerCommand("triveni-new", {
  description: "Short description",
  handler: async (args) => send(pi, args, `
Act as Triveni's <function> module.
Capability showcased: <capability>.
Scenario: <scenario>.

Execute:
1. <step>
2. <step>
3. Cite sources or say evidence is missing.
`),
});
```

If the module needs data:

1. Put files under `module_references/triveni-new/`.
2. Add the smallest parser/retriever needed in `extensions/triveni.ts`.
3. Keep outputs grounded: quote retrieved text, cite source/page/URL, and refuse unsupported answers.
4. Update `docs/TRIVENI_PLAN.md` and this file.

## Restart after changes

For independent pi testing, just exit and rerun the `pi --extension ...` command.

For Slidev:

```bash
pkill -f 'slidev'
pkill -f 'node pi-chat-server.cjs'
pkill -f 'node dev.cjs'
npm run dev
```

If port `18787` is stuck:

```bash
lsof -tiTCP:18787 -sTCP:LISTEN | xargs kill -9
npm run dev
```

## Design rule

Keep modules simple until real data requires more:

- one PDF → cached text + keyword retrieval
- a few APIs → direct fetch + structured JSON summary
- growing corpus → then add embeddings/vector store
- repeated analysis → then add saved notebooks/templates
