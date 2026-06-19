import { defineStore } from 'pinia'
import { ref } from 'vue'

export const useChatStore = defineStore('chat', () => {
  const messages = ref([])
  const isStreaming = ref(false)
  const mode = ref('stream')

  function addUserMessage(question) {
    messages.value.push({
      role: 'user',
      content: question,
      timestamp: Date.now(),
    })
  }

  function addAssistantChunk(token) {
    const last = messages.value[messages.value.length - 1]
    if (last && last.role === 'assistant') {
      last.content += token
    } else {
      messages.value.push({
        role: 'assistant',
        content: token,
        timestamp: Date.now(),
      })
    }
  }

  function finishStreaming(costTime) {
    const last = messages.value[messages.value.length - 1]
    if (last && last.role === 'assistant') {
      last.costTime = costTime
    }
    isStreaming.value = false
  }

  function clearMessages() {
    messages.value = []
  }

  function setMode(m) {
    mode.value = m
  }

  return {
    messages,
    isStreaming,
    mode,
    addUserMessage,
    addAssistantChunk,
    finishStreaming,
    clearMessages,
    setMode,
  }
})
