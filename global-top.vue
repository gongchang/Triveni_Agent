<script setup>
function toggleFullscreen() {
  if (document.fullscreenElement) document.exitFullscreen()
  else document.documentElement.requestFullscreen()
}
</script>

<template>
  <button class="triveni-fullscreen" @click.stop="toggleFullscreen" title="Enter fullscreen">
    ⛶
  </button>
</template>
