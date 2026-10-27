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
    const frameUrl = data.answer?.match(/https?:\/\/127\.0\.0\.1:(?:3838|3840)\S*/)?.[0]
    messages.value.push({ role: 'agent', text: data.answer, frameUrl })
  } catch (e) {
    messages.value.push({ role: 'agent', text: `Could not reach local Triveni-agent bridge. Run \`npm run dev\` or \`npm run agent\`, or use “Copy”.\n\n${e.message}` })
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="triveni-agent-box">
    <div class="triveni-agent-head">
      <strong>Triveni-agent · {{ title }}</strong>
    </div>
    <div class="triveni-agent-chat-log">
      <div v-for="(m, i) in messages" :key="i" :class="['triveni-agent-msg', m.role]">
        <b>{{ m.role === 'you' ? 'You' : 'Triveni-agent' }}</b>
        <pre>{{ m.text }}</pre>
        <iframe v-if="m.frameUrl" class="triveni-agent-frame" :src="m.frameUrl" />
      </div>
    </div>
    <textarea v-model="input" spellcheck="false" />
    <div class="triveni-agent-actions triveni-agent-actions-bottom">
      <button class="triveni-ask-button" @click="ask" :disabled="busy">{{ busy ? 'Thinking…' : 'Ask Triveni-agent' }}</button>
    </div>
  </div>
</template>
