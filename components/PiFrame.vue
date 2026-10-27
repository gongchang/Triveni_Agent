<script setup>
import { ref, onMounted } from 'vue'

const props = defineProps({
  defaultUrl: { type: String, default: 'http://localhost:3141' },
  sessionId: { type: String, default: '01a0e9c1-3b0b-7279-8b1a-52c958b6050a' },
})

const url = ref(props.defaultUrl)
onMounted(() => {
  url.value = localStorage.getItem('pi-url') || props.defaultUrl
})
function save() {
  localStorage.setItem('pi-url', url.value)
}
</script>

<template>
  <div class="pi-frame">
    <div class="pi-bar">
      <span>Triveni-agent live session</span>
      <input v-model="url" @change="save" placeholder="http://localhost:3141" />
      <a :href="url" target="_blank">open</a>
    </div>
    <iframe :src="url" />
    <div class="pi-note">Session: {{ sessionId }} · If the frame is blank, paste your Triveni-agent URL above or click “open”.</div>
  </div>
</template>
