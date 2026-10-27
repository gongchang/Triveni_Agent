<script setup>
import { onBeforeUnmount, onMounted, ref } from 'vue'
import { Terminal } from '@xterm/xterm'
import { FitAddon } from '@xterm/addon-fit'
import '@xterm/xterm/css/xterm.css'

const props = defineProps({
  url: { type: String, default: 'ws://127.0.0.1:18787/tui' },
})

const el = ref()
let term, fit, ws

onMounted(() => {
  term = new Terminal({ cursorBlink: true, fontSize: 13, fontFamily: 'Menlo, Monaco, monospace' })
  fit = new FitAddon()
  term.loadAddon(fit)
  term.open(el.value)
  fit.fit()
  ws = new WebSocket(props.url)
  ws.onopen = () => {
    ws.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }))
    term.focus()
  }
  ws.onmessage = e => term.write(e.data)
  ws.onclose = () => term.writeln('\r\n[Triveni-agent TUI disconnected: run npm run dev or npm run agent]')
  term.onData(data => ws?.readyState === WebSocket.OPEN && ws.send(JSON.stringify({ type: 'input', data })))
  window.addEventListener('resize', resize)
})

function resize() {
  if (!fit || !ws || ws.readyState !== WebSocket.OPEN) return
  fit.fit()
  ws.send(JSON.stringify({ type: 'resize', cols: term.cols, rows: term.rows }))
}

onBeforeUnmount(() => {
  window.removeEventListener('resize', resize)
  ws?.close()
  term?.dispose()
})
</script>

<template>
  <div ref="el" class="triveni-tui" />
</template>
