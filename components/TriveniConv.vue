<script setup>
import { ref } from 'vue'

const props = defineProps({
  endpoint: { type: String, default: 'http://127.0.0.1:18787/ask' },
  url: { type: String, default: 'http://127.0.0.1:3840' },
})

const started = ref(false)
const busy = ref(false)
const error = ref('')
const frameUrl = ref(props.url)

async function launch() {
  busy.value = true
  error.value = ''
  try {
    const res = await fetch(props.endpoint, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ prompt: '/triveni-conv' }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || res.statusText)
    await new Promise(resolve => setTimeout(resolve, 800))
    frameUrl.value = `${props.url}?q=screen%20increased%20labs&t=${Date.now()}`
    started.value = true
  } catch (e) {
    error.value = e.message
  } finally {
    busy.value = false
  }
}
</script>

<template>
  <div class="triveni-eda-box">
    <div class="pi-bar">
      <span>Triveni Conv · DuckDB + Plotly</span>
      <button @click="launch" :disabled="busy">{{ busy ? 'Launching…' : 'Launch /triveni-conv' }}</button>
      <a :href="url" target="_blank">open</a>
    </div>
    <iframe v-if="started" :src="frameUrl" />
    <div v-else class="pi-note">Click launch to start conversational analytics over SDY4 using DuckDB SQL and Plotly charts.</div>
    <div v-if="error" class="pi-note">Could not launch: {{ error }}</div>
  </div>
</template>
