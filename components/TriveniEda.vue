<script setup>
import { ref } from 'vue'

const props = defineProps({
  endpoint: { type: String, default: 'http://127.0.0.1:18787/ask' },
  url: { type: String, default: 'http://127.0.0.1:3838' },
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
      body: JSON.stringify({ prompt: '/triveni-eda' }),
    })
    const data = await res.json()
    if (!res.ok) throw new Error(data.error || res.statusText)
    await new Promise(resolve => setTimeout(resolve, 1200))
    frameUrl.value = `${props.url}?t=${Date.now()}`
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
      <span>Triveni EDA · R Shiny</span>
      <button @click="launch" :disabled="busy">{{ busy ? 'Launching…' : 'Launch /triveni-eda' }}</button>
      <a :href="url" target="_blank">open</a>
    </div>
    <iframe v-if="started" :src="frameUrl" />
    <div v-else class="pi-note">Click launch to start the local Shiny app and embed the interactive SDY4 plot.</div>
    <div v-if="error" class="pi-note">Could not launch: {{ error }}</div>
  </div>
</template>
