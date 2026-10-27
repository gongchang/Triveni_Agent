const { spawn } = require('child_process')

const procs = [
  spawn(process.execPath, ['pi-chat-server.cjs'], { stdio: 'inherit' }),
  spawn(process.platform === 'win32' ? 'npx.cmd' : 'npx', ['slidev', '--open'], { stdio: 'inherit' }),
]

function stop(code = 0) {
  for (const p of procs) if (!p.killed) p.kill()
  process.exit(code)
}

for (const p of procs) p.on('exit', code => {
  if (code) stop(code)
})
process.on('SIGINT', () => stop(0))
process.on('SIGTERM', () => stop(0))
