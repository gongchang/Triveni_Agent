import { execFileSync, spawn, type ChildProcess } from "node:child_process";
import { existsSync, mkdirSync, readFileSync, statSync } from "node:fs";
import { dirname, resolve } from "node:path";
import type { ExtensionAPI } from "@earendil-works/pi-coding-agent";

const strategy = `Triveni scientific strategy anchor:
- Genetics-informed targets in epithelial barrier disease, including KLK5/7 and PRSS1.
- Antibody engineering and developability.
- Translational I&I biology using biomarkers, patient cohorts, and lesion/non-lesion biopsy data.
- Treat agentic AI as an extensible operating system for decision-making, not a chatbot.`;

const hrPdf = resolve(process.cwd(), "module_references/triveni-hr/Triveni Bio 2025-26 Employee Benefits Memo.pdf");
const hrText = resolve(process.cwd(), ".cache/triveni-hr-benefits.txt");
const edaPort = Number(process.env.TRIVENI_EDA_PORT || 3838);
const edaUrl = `http://127.0.0.1:${edaPort}`;
const convPort = Number(process.env.TRIVENI_CONV_PORT || 3840);
const convUrl = `http://127.0.0.1:${convPort}`;
let edaProcess: ChildProcess | undefined;
let convProcess: ChildProcess | undefined;

function startEda() {
	if (edaProcess?.exitCode === null) return edaUrl;
	edaProcess = spawn("Rscript", ["-e", `shiny::runApp('tools/triveni_eda_app.R', host='127.0.0.1', port=${edaPort}, launch.browser=FALSE)`], {
		cwd: process.cwd(),
		stdio: "ignore",
		detached: true,
	});
	edaProcess.unref();
	return edaUrl;
}

function startConv() {
	if (convProcess?.exitCode === null) return convUrl;
	try { execFileSync("bash", ["-lc", `lsof -tiTCP:${convPort} -sTCP:LISTEN | xargs -r kill`]); } catch {}
	convProcess = spawn("python3", ["tools/triveni_conv_app.py", "--port", String(convPort)], {
		cwd: process.cwd(),
		stdio: "ignore",
		detached: true,
	});
	convProcess.unref();
	return convUrl;
}


function send(pi: ExtensionAPI, args: string, body: string) {
	pi.sendUserMessage(`${body}\n\nUser context or question: ${args.trim() || "Use the default scenario."}`);
}

function gmailQuery(args: string) {
	const raw = args.trim();
	if (!raw) return "newer_than:1d";
	let q = raw
		.replace(/\b(go to|open|search|look in|check)\b/ig, " ")
		.replace(/\b(my )?gmail\b/ig, " ")
		.replace(/\b(and )?find( me)?\b/ig, " ")
		.replace(/\b(show|list|get)\b/ig, " ")
		.replace(/\b(the )?latest\b/ig, " ")
		.replace(/\b(news|info|information|emails?|from)\b/ig, " ")
		.replace(/\s+/g, " ")
		.trim();
	if (/workshop|conference|symposium|summit/i.test(raw)) q = "(workshop OR conference OR symposium OR summit)";
	if (/argenziano/i.test(raw)) q = "argenziano";
	if (/\btoday\b/i.test(raw)) q += " newer_than:1d";
	else if (/past two days|last two days|\b2 days\b/i.test(raw)) q += " newer_than:2d";
	else if (/\blatest\b/i.test(raw)) q += " newer_than:30d";
	return q.trim();
}

function runGmailSearch(args: string) {
	const query = gmailQuery(args);
	const script = `
const task = await taskSpace("triveni-assit");
const page = task.page("p1");
const query = ${JSON.stringify(query)};
await page.goto("https://mail.google.com/mail/u/0/#search/" + encodeURIComponent(query), { timeout: 30000, waitUntil: "domcontentloaded" });
await page.waitForTimeout(1000);
const rows = await page.evaluate(() => [...document.querySelectorAll('[role=row]')]
  .slice(1, 4)
  .map(row => row.innerText?.replace(/\\s+/g, ' ').trim())
  .filter(Boolean));
console.log(JSON.stringify({ taskSpaceId: task.spaceId, page: page.label, query, url: await page.url(), title: await page.title(), rows }, null, 2));
`;
	return execFileSync("bash", ["-lc", `ego-browser nodejs <<'EOF' 2>&1\n${script}\nEOF`], {
		cwd: process.cwd(),
		encoding: "utf8",
		maxBuffer: 512 * 1024,
	});
}

async function fetchJson(url: string, options?: RequestInit) {
	const res = await fetch(url, options);
	if (!res.ok) throw new Error(`${res.status} ${res.statusText}: ${url}`);
	return res.json() as Promise<any>;
}

function ciTerms(question: string) {
	const q = question.toLowerCase();
	if (q.includes("920") || q.includes("pancreatitis") || q.includes("trypsin") || q.includes("prss")) {
		return {
			profile: "TRIV-920",
			space: "pancreatitis / trypsin biology",
			terms: ["PRSS1", "PRSS2", "trypsin", "trypsinogen", "pancreatitis"],
		};
	}
	return {
		profile: "TRIV-509",
		space: "atopic dermatitis / epithelial barrier biology",
		terms: ["KLK5", "KLK7", "kallikrein", "Netherton", "SPINK5", "LEKTI", "atopic dermatitis"],
	};
}

async function ciEvidence(question: string) {
	const cfg = ciTerms(question);
	const term = encodeURIComponent(cfg.terms.join(" OR "));
	const ct = await fetchJson(`https://clinicaltrials.gov/api/v2/studies?query.term=${term}&pageSize=8`).catch((e: Error) => ({ error: e.message, studies: [] }));
	const epmcQuery = encodeURIComponent(`(${cfg.terms.join(" OR ")})`);
	const epmc = await fetchJson(`https://www.ebi.ac.uk/europepmc/webservices/rest/search?query=${epmcQuery}&format=json&pageSize=8`).catch((e: Error) => ({ error: e.message, resultList: { result: [] } }));
	const today = new Date().toISOString().slice(0, 10);
	const bio = await fetchJson(`https://api.biorxiv.org/details/biorxiv/2025-01-01/${today}/0`).catch((e: Error) => ({ error: e.message, collection: [] }));

	const trials = (ct.studies || []).map((s: any) => {
		const p = s.protocolSection || {};
		return {
			nctId: p.identificationModule?.nctId,
			title: p.identificationModule?.briefTitle,
			sponsor: p.sponsorCollaboratorsModule?.leadSponsor?.name,
			conditions: p.conditionsModule?.conditions,
			interventions: (p.armsInterventionsModule?.interventions || []).map((i: any) => i.name),
			phase: p.designModule?.phases,
			status: p.statusModule?.overallStatus,
			primaryCompletionDate: p.statusModule?.primaryCompletionDateStruct?.date,
		};
	});
	const papers = (epmc.resultList?.result || []).map((r: any) => ({
		title: r.title,
		year: r.pubYear,
		source: r.source,
		doi: r.doi,
		journal: r.journalTitle,
		url: r.doi ? `https://doi.org/${r.doi}` : `https://europepmc.org/article/${r.source}/${r.id}`,
	}));
	const lowerTerms = cfg.terms.map(t => t.toLowerCase());
	const preprints = (bio.collection || [])
		.filter((r: any) => lowerTerms.some(t => `${r.title} ${r.abstract}`.toLowerCase().includes(t)))
		.slice(0, 8)
		.map((r: any) => ({ title: r.title, date: r.date, doi: r.doi, category: r.category, url: `https://doi.org/${r.doi}` }));

	return JSON.stringify({ profile: cfg.profile, space: cfg.space, queryTerms: cfg.terms, trials, papers, preprints }, null, 2);
}

function hrChunks(question: string) {
	if (!existsSync(hrPdf)) throw new Error(`Missing HR reference PDF: ${hrPdf}`);
	if (!existsSync(hrText) || statSync(hrText).mtimeMs < statSync(hrPdf).mtimeMs) {
		mkdirSync(dirname(hrText), { recursive: true });
		execFileSync("pdftotext", [hrPdf, hrText]);
	}

	const pages = readFileSync(hrText, "utf8").split("\f");
	const chunks = pages.flatMap((page, pageIndex) =>
		page
			.split(/\n\s*\n/g)
			.map(text => text.replace(/\s+/g, " ").trim())
			.filter(text => text.length > 60)
			.map(text => ({ page: pageIndex + 1, text })),
	);

	const terms = [...new Set(question.toLowerCase().match(/[a-z0-9]+/g) || [])]
		.filter(t => t.length > 2);
	return chunks
		.map(chunk => ({
			...chunk,
			score: terms.reduce((n, term) => n + (chunk.text.toLowerCase().includes(term) ? 1 : 0), 0),
		}))
		.sort((a, b) => b.score - a.score || a.page - b.page)
		.slice(0, 6);
}

export default function (pi: ExtensionAPI) {
	pi.registerCommand("triveni", {
		description: "Auto-route a question to the right Triveni module",
		handler: async (args, ctx) => {
			if (!args.trim()) {
				ctx.ui.notify(
					"Triveni modules: /triveni-ci, /triveni-hr, /triveni-bio, /triveni-clin, /triveni-eda, /triveni-conv, /triveni-assit (Gmail search). Use /triveni <question> to auto-route.",
					"info",
				);
				return;
			}
			const q = args.toLowerCase();
			let routed = "/triveni-ci";
			if (/gmail|email|mail|inbox/.test(q)) routed = "/triveni-assit";
			else if (/benefit|policy|pto|travel|onboard|hmo|epo|vision|lens|frame|domestic|enrollment/.test(q)) routed = "/triveni-hr";
			else if (/gtex|gene|expression|tissue|plot|scatter|correlat|klk|prss|tp63|tslp|par2/.test(q)) routed = "/triveni-bio";
			else if (/conv|conversational|duckdb|plotly/.test(q)) routed = "/triveni-conv";
			else if (/shiny|interactive|eda app|dashboard/.test(q)) routed = "/triveni-eda";
			else if (/sdy4|clinical|lab|eosinophil|ige|eczema|atopic|healthy control|cbc|t cell|b cell|hsv/.test(q)) routed = "/triveni-clin";
			else if (/competitor|trial|landscape|target|indication|disease|api|patent|ci|netherton|pancreatitis/.test(q)) routed = "/triveni-ci";
			ctx.ui.notify(`Auto-routed to ${routed}. In Slidev embedded boxes this executes directly; in native TUI run: ${routed} ${args}`, "info");
			pi.sendUserMessage(`Route this request to ${routed} and answer using that module's rules and available local data/API tools: ${args}`);
		},
	});

	pi.registerCommand("triveni-assit", {
		description: "Fast Gmail search via Ego Lite; returns top 3 matching rows",
		handler: async (args, ctx) => {
			ctx.ui.notify("Searching Gmail...", "info");
			const gmailOutput = runGmailSearch(args);
			send(pi, args, `Act as Triveni's Gmail search assistant.
Capability showcased: fast Gmail search through Ego Lite without expensive snapshots.

Gmail output:
${gmailOutput}

Answer rules:
1. List only the returned email rows, up to 3.
2. If no rows were returned, say no matching emails were visible for the Gmail query.
3. Mention the exact Gmail query used.
4. Keep the answer concise.`);
		},
	});

	pi.registerCommand("triveni-assist", {
		description: "Alias for /triveni-assit",
		handler: async (args, ctx) => {
			ctx.ui.notify("Searching Gmail...", "info");
			const gmailOutput = runGmailSearch(args);
			send(pi, args, `Act as Triveni's Gmail search assistant.
Capability showcased: fast Gmail search through Ego Lite without expensive snapshots.

Gmail output:
${gmailOutput}

Answer rules:
1. List only the returned email rows, up to 3.
2. If no rows were returned, say no matching emails were visible for the Gmail query.
3. Mention the exact Gmail query used.
4. Keep the answer concise.`);
		},
	});

	pi.registerCommand("triveni-ci", {
		description: "CI landscape lookup using ClinicalTrials.gov, Europe PMC, and bioRxiv",
		handler: async (args, ctx) => {
			ctx.ui.notify("Searching public CI sources...", "info");
			const evidence = execFileSync("python3", ["tools/triveni_ci.py", args || "TRIV-509 competitors in AD epithelial barrier disease"], {
				cwd: process.cwd(),
				encoding: "utf8",
				maxBuffer: 1024 * 1024 * 8,
			});
			send(pi, args, `${strategy}

Act as Triveni's Competitive Intelligence module.
Capability showcased: autonomous surveillance and competitive synthesis.
Scenario: flexible target, clinical-trial, competitor, indication, and disease-landscape lookup.

Fetched public evidence from configured APIs:
${evidence}

Execute:
1. Answer the user's specific CI question, not a generic profile summary.
2. Extract NCT ID, sponsor, condition, intervention/modality if visible, phase, status, primary completion date, title, DOI/URL, and source when available.
3. Separate clinical-trial evidence from publication/preprint evidence.
4. If no source returns relevant hits, say so clearly and list the exact terms used.
5. End with concise CI implications for the relevant Triveni profile or target space.`);
		},
	});

	pi.registerCommand("triveni-hr", {
		description: "Ask the Triveni HR benefits memo with grounded citations",
		handler: async (args, ctx) => {
			if (!args.trim()) {
				ctx.ui.notify("Usage: /triveni-hr <benefits question>", "warning");
				return;
			}
			const chunks = hrChunks(args);
			const evidence = chunks
				.map((c, i) => `[${i + 1}] Triveni Bio 2025-26 Employee Benefits Memo.pdf, page ${c.page}\n"${c.text}"`)
				.join("\n\n");

			send(pi, args, `Act as Triveni's HR benefits RAG module.
Capability showcased: grounded RAG and policy retrieval.
Source corpus: Triveni Bio 2025-26 Employee Benefits Memo.pdf.

Retrieved evidence:
${evidence || "No relevant chunks found."}

Answer rules:
1. If no relevant evidence was retrieved, say that nothing was found in the HR benefits memo.
2. If evidence was retrieved, answer in no more than 2 short paragraphs.
3. Use only the retrieved evidence above and quote exact supporting text with bracket number plus page, e.g. [2, p.3].
4. Do not infer missing benefits details.`);
		},
	});

	pi.registerCommand("triveni-eda", {
		description: "Launch interactive R Shiny EDA for ImmPort SDY4 clinical lab data",
		handler: async (args, ctx) => {
			const url = startEda();
			ctx.ui.notify(`Triveni EDA Shiny app: ${url}`, "info");
			pi.sendUserMessage(`Triveni EDA Shiny app is running at ${url}. In Slidev, use the embedded iframe/component to show this URL. Dataset: ImmPort SDY4 clinical lab data. User context: ${args.trim() || "open the interactive EDA dashboard"}`);
		},
	});

	pi.registerCommand("triveni-conv", {
		description: "Launch conversational DuckDB + Plotly analytics for ImmPort SDY4 clinical lab data",
		handler: async (args, ctx) => {
			const url = startConv();
			ctx.ui.notify(`Triveni conversational analytics: ${url}`, "info");
			pi.sendUserMessage(`Triveni conversational analytics is running at ${url}. It uses DuckDB over ImmPort SDY4 subject-level lab data and Plotly for charts. In Slidev, embed it with <TriveniConv />. User context: ${args.trim() || "open conversational analytics"}`);
		},
	});

	pi.registerCommand("triveni-int-eda", {
		description: "Launch conversational R Shiny EDA with shinychat and ellmer for ImmPort SDY4 clinical lab data",
		handler: async (args, ctx) => {
			const url = startEda();
			ctx.ui.notify(`Triveni conversational EDA: ${url}`, "info");
			pi.sendUserMessage(`Triveni conversational EDA is running at ${url}. Open the Ask tab for shinychat + ellmer conversational analysis over the selected SDY4 lab summaries. User context: ${args.trim() || "interactive conversational analysis"}`);
		},
	});

	pi.registerCommand("triveni-clin", {
		description: "ImmPort SDY4 atopic dermatitis clinical EDA",
		handler: async (args, ctx) => {
			if (!args.trim()) {
				ctx.ui.notify("Usage: /triveni-clin <observational clinical EDA question>", "warning");
				return;
			}
			ctx.ui.notify("Running NHANES clinical EDA...", "info");
			const analysis = execFileSync("python3", ["tools/triveni_clin.py", args], {
				cwd: process.cwd(),
				encoding: "utf8",
				maxBuffer: 1024 * 1024 * 8,
			});
			send(pi, args, `Act as Triveni's Clinical Observational EDA module.
Capability showcased: quick, cautious exploratory analysis of ImmPort SDY4 atopic dermatitis / eczema herpeticum clinical lab data.

Python analysis output:
${analysis}

Answer rules:
1. Summarize cohort definition, AD/healthy counts, selected measures, effect sizes, and p-values.
2. Note unavailable measurements clearly, e.g. if a lab has no healthy-control values.
3. Emphasize observational best practices: no causal claims, repeated biosamples averaged, no multiplicity correction, subgroup/visit/confounder modeling needed for follow-up.
4. Point to the result CSV for details.
5. Keep the answer concise and clinically cautious.`);
		},
	});

	pi.registerCommand("triveni-bio", {
		description: "GTEx expression Q&A and natural-language plotting",
		handler: async (args, ctx) => {
			if (!args.trim()) {
				ctx.ui.notify("Usage: /triveni-bio <expression question or plot request>", "warning");
				return;
			}
			ctx.ui.notify("Analyzing GTEx median TPM data...", "info");
			const analysis = execFileSync("python3", ["tools/triveni_bio.py", args], {
				cwd: process.cwd(),
				encoding: "utf8",
				maxBuffer: 1024 * 1024 * 8,
			});
			const prompt = `${strategy}

Act as Triveni's Biology and Translational Science analytics module.
Capability showcased: natural-language-driven EDA over GTEx median gene TPM data.
Scenario: answer quick expression questions and create simple plots for biomarkers such as PAR2/F2RL1, TSLP, KLK5, KLK7, PRSS1, and PRSS2.

Python analysis output:
${analysis}

Answer rules:
1. Answer from the Python output only.
2. Mention the dataset, genes, tissues searched, and top expression findings.
3. If a plot was requested, display the tui_plot text chart directly, then point to the PNG path and CSV path. The PNG is attached for Pi TUI inline-image rendering when terminal.showImages is enabled.
4. Caveat that GTEx is healthy tissue median TPM, not lesion biopsy or patient-level disease data.
5. Keep the answer concise and analysis-focused.

User context or question: ${args.trim()}`;
			try {
				const parsed = JSON.parse(analysis);
				if (parsed.plot_png && existsSync(parsed.plot_png)) {
					pi.sendUserMessage([
						{ type: "text", text: prompt },
						{ type: "image", data: readFileSync(parsed.plot_png).toString("base64"), mimeType: "image/png" } as any,
					]);
					return;
				}
			} catch {}
			pi.sendUserMessage(prompt);
		},
	});
}
