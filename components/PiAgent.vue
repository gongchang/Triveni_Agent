<script setup>
import { ref } from 'vue'

const props = defineProps({
  title: { type: String, default: 'Triveni-agent' },
  prompt: { type: String, default: '' },
  endpoint: { type: String, default: 'http://127.0.0.1:18787/ask' },
})

const input = ref(props.prompt)
const messages = ref([{ role: 'agent', text: 'Ready. Edit the slash command and ask Triveni-agent from inside the slide.' }])
const busy = ref(false)
const copied = ref(false)

async function copy() {
  await navigator.clipboard.writeText(input.value)
  copied.value = true
  setTimeout(() => (copied.value = false), 1200)
}

async function ask() {
  const prompt = input.value.trim()
  if (!prompt || busy.value) return
  messages.value.push({ role: 'you', text: prompt })
  busy.value = true
  try {
    const res = await fetch(props.endpoint, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ prompt }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || res.statusText)
    messages.value.push({ role: 'agent', text: data.answer })
  } catch (e) {
    messages.value.push({ role: 'agent', text: `Could not reach local Triveni-agent bridge. Run \`npm run dev\` or \`npm run agent\`, or use “Copy”.\n\n${e.message}` })
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="pi-agent">
    <div class="pi-head">
      <strong>Triveni-agent · {{ title }}</strong>
      <div class="pi-actions">
        <button @click="copy">{{ copied ? 'Copied' : 'Copy' }}</button>
        <button @click="ask" :disabled="busy">{{ busy ? 'Thinking…' : 'Ask Triveni-agent' }}</button>
      </div>
    </div>
    <div class="pi-chat-log">
      <div v-for="(m, i) in messages" :key="i" :class="['pi-msg', m.role]">
        <b>{{ m.role === 'you' ? 'You' : 'Triveni-agent' }}</b>
        <pre>{{ m.text }}</pre>
      </div>
    </div>
    <textarea v-model="input" spellcheck="false" />
  </div>
</template>
