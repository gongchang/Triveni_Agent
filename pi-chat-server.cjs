const http = require('http')
const { execFile, execFileSync, spawn } = require('child_process')
const pty = require('node-pty')
const { WebSocketServer } = require('ws')

const port = Number(process.env.PI_CHAT_PORT || 18787)
const sessionId = process.env.PI_SLIDEV_SESSION_ID || 'triveni-slidev-demo'
const provider = process.env.PI_PROVIDER || 'openai-codex'
const model = process.env.PI_MODEL || 'gpt-5.5'
const piBin = process.env.PI_BIN || '/Users/xingyuli/.pi/agent/bin/pi'
const triveniExtension = `${process.cwd()}/extensions/triveni.ts`
const edaPort = Number(process.env.TRIVENI_EDA_PORT || 3838)
const edaUrl = `http://127.0.0.1:${edaPort}`
const convPort = Number(process.env.TRIVENI_CONV_PORT || 3840)
const convUrl = `http://127.0.0.1:${convPort}`
let edaProcess
let convProcess
let telegramProcess

function startEda() {
  if (edaProcess && edaProcess.exitCode === null) return edaUrl
  edaProcess = spawn('Rscript', ['-e', `shiny::runApp('tools/triveni_eda_app.R', host='127.0.0.1', port=${edaPort}, launch.browser=FALSE)`], {
    cwd: process.cwd(), stdio: 'ignore', detached: true,
  })
  edaProcess.unref()
  return edaUrl
}

function startConv() {
  if (convProcess && convProcess.exitCode === null) return convUrl
  try { execFileSync('bash', ['-lc', `lsof -tiTCP:${convPort} -sTCP:LISTEN | xargs -r kill`]) } catch {}
  convProcess = spawn('python3', ['tools/triveni_conv_app.py', '--port', String(convPort)], {
    cwd: process.cwd(), stdio: 'ignore', detached: true,
  })
  convProcess.unref()
  return convUrl
}

function startTelegramBridge() {
  if (process.env.PI_TELEGRAM_CONNECT === '0') return
  if (telegramProcess) return

  console.log('[Pi Headless] Connecting Telegram bridge...')
  try {
    telegramProcess = pty.spawn(piBin, [
      '--approve',
      '--extension', triveniExtension,
      '--provider', provider,
      '--model', model,
      '--session-id', sessionId,
    ], { name: 'xterm-256color', cols: 100, rows: 30, cwd: process.cwd(), env: process.env })
  } catch (err) {
    console.error('[Pi Headless] Telegram bridge failed to start:', err.message)
    return
  }

  telegramProcess.onData(data => process.stdout.write(`[Pi Telegram] ${data}`))
  telegramProcess.onExit(({ exitCode }) => {
    telegramProcess = null
    if (exitCode) console.error(`[Pi Headless] Telegram bridge exited with code ${exitCode}`)
  })
  setTimeout(() => telegramProcess?.write('/telegram-connect\r'), 1000)
}

function summarizeSlash(prompt) {
  const [cmd, ...rest] = prompt.trim().split(/\s+/)
  const args = rest.join(' ')
  if (cmd === '/triveni') {
    if (!args.trim()) return 'Triveni-agent modules: /triveni-ci, /triveni-hr, /triveni-bio, /triveni-clin, /triveni-eda, /triveni-conv, /triveni-assit (Gmail search)\n\nUse /triveni <question> to auto-route.'
    const q = args.toLowerCase()
    let routed = '/triveni-ci'
    if (/gmail|email|mail|inbox/.test(q)) routed = '/triveni-assit'
    else if (/benefit|policy|pto|travel|onboard|hmo|epo|vision|lens|frame|domestic|enrollment/.test(q)) routed = '/triveni-hr'
    else if (/gtex|gene|expression|tissue|plot|scatter|correlat|klk|prss|tp63|tslp|par2/.test(q)) routed = '/triveni-bio'
    else if (/conv|conversational|duckdb|plotly/.test(q)) routed = '/triveni-conv'
    else if (/shiny|interactive|eda app|dashboard/.test(q)) routed = '/triveni-eda'
    else if (/sdy4|clinical|lab|eosinophil|ige|eczema|atopic|healthy control|cbc|t cell|b cell|hsv/.test(q)) routed = '/triveni-clin'
    else if (/competitor|trial|landscape|target|indication|disease|api|patent|ci|netherton|pancreatitis/.test(q)) routed = '/triveni-ci'
    return `Auto-routed to ${routed}\n\n` + summarizeSlash(`${routed} ${args}`)
  }
  if (cmd === '/triveni-assit' || cmd === '/triveni-assist') {
    let query = args.trim() || 'newer_than:1d'
    const raw = query
    query = query
      .replace(/\b(go to|open|search|look in|check)\b/ig, ' ')
      .replace(/\b(my )?gmail\b/ig, ' ')
      .replace(/\b(and )?find( me)?\b/ig, ' ')
      .replace(/\b(show|list|get)\b/ig, ' ')
      .replace(/\b(the )?latest\b/ig, ' ')
      .replace(/\b(news|info|information|emails?|from)\b/ig, ' ')
      .replace(/\s+/g, ' ')
      .trim()
    if (/workshop|conference|symposium|summit/i.test(raw)) query = '(workshop OR conference OR symposium OR summit)'
    if (/argenziano/i.test(raw)) query = 'argenziano'
    if (/\btoday\b/i.test(raw)) query = `${query} newer_than:1d`.trim()
    else if (/past two days|last two days|\b2 days\b/i.test(raw)) query = `${query} newer_than:2d`.trim()
    else if (/\blatest\b/i.test(raw)) query = `${query} newer_than:30d`.trim()
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
console.log(JSON.stringify({ query, rows }));
`
    const out = execFileSync('bash', ['-lc', `ego-browser nodejs <<'EOF' 2>&1\n${script}\nEOF`], { encoding: 'utf8', maxBuffer: 512 * 1024 })
    const j = JSON.parse(out)
    if (!j.rows.length) return `Gmail query: ${j.query}\n\nNo matching emails were visible.`
    return `Gmail query: ${j.query}\n\n` + j.rows.map((r, i) => `${i + 1}. ${r}`).join('\n')
  }
  if (cmd === '/triveni-eda') {
    return `Triveni EDA Shiny app launched: ${startEda()}\n\nUse the embedded Slidev frame below, or open the URL directly.`
  }
  if (cmd === '/triveni-conv') {
    return `Triveni conversational analytics launched: ${startConv()}\n\nDuckDB executes SDY4 SQL; Plotly renders charts in the embedded Slidev frame.`
  }
  if (cmd === '/triveni-int-eda') {
    return `Triveni conversational EDA launched: ${startEda()}\n\nOpen the Ask tab for shinychat + ellmer chat over the selected SDY4 summaries.`
  }
  if (cmd === '/triveni-hr') {
    const j = JSON.parse(execFileSync('python3', ['tools/triveni_hr.py', '--json', args], { encoding: 'utf8', maxBuffer: 1024 * 1024 * 8 }))
    if (!j.evidence || j.evidence.length === 0) return `Nothing was found in the HR benefits memo for: ${args}`
    const hits = j.evidence.slice(0, 2).map((e, i) => `[${i + 1}] ${e.text}`).join('\n')
    return `Found relevant text in ${j.source}.\n\n${hits}`
  }
  if (cmd === '/triveni-bio') {
    const j = JSON.parse(execFileSync('python3', ['tools/triveni_bio.py', args], { encoding: 'utf8', maxBuffer: 1024 * 1024 * 8 }))
    if (j.top_expression) {
      const byGene = new Map()
      for (const r of j.top_expression) if (!byGene.has(r.gene)) byGene.set(r.gene, [])
      for (const r of j.top_expression) byGene.get(r.gene).push(r)
      const table = ['Gene   Rank  Tissue                                  Median TPM', '-----  ----  --------------------------------------  ----------']
      for (const [gene, rows] of byGene) {
        rows.slice(0, 3).forEach((r, i) => table.push(`${gene.padEnd(5)}  ${String(i + 1).padStart(4)}  ${r.tissue.slice(0, 38).padEnd(38)}  ${Number(r.median_tpm).toFixed(2).padStart(10)}`))
      }
      return `GTEx expression summary\nDataset: ${j.dataset}\nTissues searched: ${j.tissues_searched}\nCSV: ${j.result_csv}\nPNG: ${j.plot_png || 'none'}\n\n${j.tui_plot ? j.tui_plot + '\n\n' : ''}${table.join('\n')}\n\nCaveat: GTEx is healthy tissue median TPM, not lesion biopsy or patient-level disease data.`
    }
    if (j.top_correlations) {
      const targets = j.targets || []
      const table = [`${'Gene'.padEnd(18)} ${targets.map(t => t.padStart(8)).join(' ')} ${'Mean'.padStart(8)}`, `${'-'.repeat(18)} ${targets.map(() => '--------').join(' ')} --------`]
      for (const r of j.top_correlations.slice(0, 10)) table.push(`${String(r.gene).slice(0, 18).padEnd(18)} ${targets.map(t => Number(r[t]).toFixed(3).padStart(8)).join(' ')} ${Number(r.mean_corr).toFixed(3).padStart(8)}`)
      return `${j.analysis}\nDataset: ${j.dataset}\nCSV: ${j.result_csv}\n\n${table.join('\n')}\n\nCaveat: ${j.caveat || 'Exploratory tissue-level analysis.'}`
    }
    return JSON.stringify(j, null, 2)
  }
  if (cmd === '/triveni-clin') {
    const raw = execFileSync('python3', ['tools/triveni_clin.py', args], { encoding: 'utf8', maxBuffer: 1024 * 1024 * 8 })
    const j = JSON.parse(raw.replace(/\bNaN\b/g, 'null'))
    const q = args.toLowerCase()
    let rows = j.results || []
    if (/\bincreas|higher|elevat/.test(q)) rows = rows.filter(r => r.direction === 'increased_in_ad')
    else if (/\bdecreas|lower|reduc/.test(q)) rows = rows.filter(r => r.direction === 'decreased_in_ad')
    rows = rows.slice(0, 10)
    const fmt = v => v == null ? 'NA' : (Math.abs(Number(v)) < 0.001 ? Number(v).toExponential(2) : Number(v).toFixed(3))
    const table = ['Measure                              Direction        AD mean  Healthy      Diff     SMD        p      FDR       n', '------------------------------------  ---------------  -------  -------  -------  ------  -------  -------  -------']
    for (const r of rows) table.push(`${r.measure.slice(0, 36).padEnd(36)}  ${String(r.direction || 'screened').padEnd(15)}  ${fmt(r.ad_mean).padStart(7)}  ${fmt(r.healthy_mean).padStart(7)}  ${fmt(r.difference).padStart(7)}  ${fmt(r.smd).padStart(6)}  ${fmt(r.welch_p).padStart(7)}  ${fmt(r.fdr_bh).padStart(7)}  ${String(`${r.case_n}/${r.control_n}`).padStart(7)}`)
    const tableText = table.join('\n')
    const increased = rows.filter(r => r.direction === 'increased_in_ad').slice(0, 5).map(r => r.measure).join(', ') || 'none among listed results'
    const decreased = rows.filter(r => r.direction === 'decreased_in_ad').slice(0, 5).map(r => r.measure).join(', ') || 'none among listed results'
    const focus = /\bincreas|higher|elevat/.test(q) ? `Increased markers requested: ${increased}.` : (/\bdecreas|lower|reduc/.test(q) ? `Decreased markers requested: ${decreased}.` : `Main signal: increased in AD/eczema: ${increased}. Decreased in AD/eczema: ${decreased}.`)
    return `SDY4 clinical EDA summary\nComparison: ${j.comparison}\nSubjects: ${j.subjects}\nCSV: ${j.result_csv}\n\n${focus}\n\nTop screened measures:\n${tableText}\n\nCaveats:\n- ${(j.best_practice_caveats || []).join('\n- ')}`
  }
  if (cmd === '/triveni-ci') {
    const j = JSON.parse(execFileSync('python3', ['tools/triveni_ci.py', args], { encoding: 'utf8', maxBuffer: 1024 * 1024 * 8 }))
    if (j.mode === 'apis') {
      const table = ['Source               Endpoint                                                          Use', '-------------------  ----------------------------------------------------------------  --------------------------------']
      for (const a of j.apis) table.push(`${a.source.slice(0,19).padEnd(19)}  ${a.endpoint.slice(0,64).padEnd(64)}  ${a.use}`)
      return `Triveni-agent CI data sources\n\n${table.join('\n')}`
    }
    if (j.error) return `CI landscape lookup could not run for: ${j.original_query}\n\n${j.error}`
    const trials = Array.isArray(j.trials) ? j.trials : []
    const papers = Array.isArray(j.papers) ? j.papers : []
    const preprints = Array.isArray(j.preprints) ? j.preprints : []
    const t = ['NCT          Status        Phase        Drug / arm name                 Drug target                     Sponsor                         Condition / title', '-----------  ------------  -----------  ------------------------------  ------------------------------  ------------------------------  --------------------------------']
    for (const r of trials.slice(0, 8)) t.push(`${String(r.nct || '').padEnd(11)}  ${String(r.status || '').slice(0,12).padEnd(12)}  ${String(r.phase || '').slice(0,11).padEnd(11)}  ${String(r.drug_names || r.interventions || '').slice(0,30).padEnd(30)}  ${String(r.drug_targets || r.chembl_targets || '').slice(0,30).padEnd(30)}  ${String(r.sponsor || '').slice(0,30).padEnd(30)}  ${String(r.conditions || r.title || '').slice(0,80)}`)
    const p = ['Year  Source  Title', '----  ------  ------------------------------------------------------------']
    for (const r of papers.slice(0, 6)) p.push(`${String(r.year || '').padEnd(4)}  ${String(r.source || '').padEnd(6)}  ${String(r.title || '').slice(0,90)}`)
    const pp = ['Date        Category       Title', '----------  -------------  ------------------------------------------------------------']
    for (const r of preprints.slice(0, 6)) pp.push(`${String(r.date || '').padEnd(10)}  ${String(r.category || '').slice(0,13).padEnd(13)}  ${String(r.title || '').slice(0,90)}`)
    const noTrials = trials.length ? '' : '\nNo ClinicalTrials.gov hits returned for these terms.'
    const noPapers = papers.length ? '' : '\nNo Europe PMC hits returned for these terms, or the API was unavailable.'
    const noPreprints = preprints.length ? '' : '\nNo recent bioRxiv hits matched these terms.'
    const links = (j.drug_target_links || []).slice(0, 8).map(x => `- ${x.drug} (${x.molecule_chembl_id}) → ${x.target}${x.mechanism ? ` — ${x.mechanism}` : ''}`).join('\n')
    const entityLine = `Target: ${(j.target_entities || []).join(', ') || 'not specified'} | Disease: ${(j.disease_entities || []).join(', ') || 'not specified'}`
    return `CI landscape lookup: ${j.profile} (${j.space})\nOriginal query: ${j.original_query}\n${entityLine}\nTerms used: ${j.query_terms.join(', ')}\n\nDrug → target links from ChEMBL\n${links || 'No direct ChEMBL mechanism links found for explicit drug names in the query.'}\n\nClinical trials\n${t.join('\n')}${noTrials}\n\nLiterature\n${p.join('\n')}${noPapers}\n\nRecent bioRxiv preprints\n${pp.join('\n')}${noPreprints}\n\nCaveats: public-source snapshot only. Fast default treats queries like “target in disease” as clinical-trial lookups, requires explicit disease + target concepts to match, expands known targets to curated asset/arm names, and annotates trial interventions with ChEMBL mechanisms where available.`
  }
  return null
}

function json(res, code, body) {
  res.writeHead(code, {
    'content-type': 'application/json',
    'access-control-allow-origin': '*',
    'access-control-allow-methods': 'POST,OPTIONS',
    'access-control-allow-headers': 'content-type',
  })
  res.end(JSON.stringify(body))
}

const server = http.createServer((req, res) => {
  if (req.method === 'OPTIONS') return json(res, 200, {})
  if (req.method !== 'POST' || req.url !== '/ask') return json(res, 404, { error: 'not found' })

  let body = ''
  req.on('data', chunk => (body += chunk))
  req.on('end', () => {
    let prompt = ''
    try { prompt = JSON.parse(body).prompt || '' } catch {}
    if (!prompt.trim()) return json(res, 400, { error: 'empty prompt' })

    try {
      const slash = prompt.trim().match(/\/triveni(?:-[\w-]+)?(?:\s+.*)?$/s)?.[0]
      const direct = slash ? summarizeSlash(slash) : null
      if (direct) return json(res, 200, { answer: direct, sessionId })
    } catch (e) {
      return json(res, 500, { error: e.message })
    }

    execFile('python3', [
      'pi-pty.py', piBin, '--print', '--approve',
      '--extension', triveniExtension,
      '--provider', provider, '--model', model,
      '--session-id', sessionId, prompt,
    ], { timeout: 180000, maxBuffer: 1024 * 1024 * 8 }, (err, stdout, stderr) => {
      if (err) return json(res, 500, { error: stderr || err.message })
      json(res, 200, { answer: stdout.trim(), sessionId })
    })
  })
})

const wss = new WebSocketServer({ server, path: '/tui' })
wss.on('connection', ws => {
  let shell
  try {
    shell = pty.spawn(piBin, [
      '--approve',
      '--extension', triveniExtension,
      '--provider', provider,
      '--model', model,
      '--session-id', sessionId,
    ], {
      name: 'xterm-256color', cols: 100, rows: 30, cwd: process.cwd(), env: process.env,
    })
  } catch (e) {
    ws.send(`Could not start pi TUI: ${e.message}\r\n`)
    return ws.close()
  }

  shell.onData(data => ws.readyState === ws.OPEN && ws.send(data))
  shell.onExit(() => ws.close())
  ws.on('message', msg => {
    try {
      const data = JSON.parse(msg)
      if (data.type === 'resize') shell.resize(data.cols, data.rows)
      else if (data.type === 'input') shell.write(data.data)
    } catch {
      shell.write(String(msg))
    }
  })
  ws.on('close', () => shell.kill())
})

server.listen(port, '127.0.0.1', () => {
  console.log(`pi bridge: http://127.0.0.1:${port}/ask and ws://127.0.0.1:${port}/tui -> ${sessionId}`)
  startTelegramBridge()
})
