<script setup>
defineProps({
  message: {
    type: Object,
    required: true,
  },
})
</script>

<template>
  <div :class="['message-bubble', message.role]">
    <div class="bubble-avatar">
      <span v-if="message.role === 'user'">你</span>
      <span v-else>AI</span>
    </div>
    <div class="bubble-body">
      <div :class="['bubble-content', message.role]">
        <div class="content-text" v-text="message.content"></div>
        <div v-if="message.citations && message.citations.length" class="citations">
          <div
            v-for="(cite, idx) in message.citations"
            :key="idx"
            class="citation-card"
          >
            <div class="citation-bar"></div>
            <div class="citation-info">
              <span class="citation-type">PDF</span>
              <span class="citation-source">来源：{{ cite }}</span>
            </div>
          </div>
        </div>
      </div>
      <div v-if="message.costTime != null" class="bubble-meta">
        耗时 {{ message.costTime }}s
      </div>
    </div>
  </div>
</template>

<style scoped>
.message-bubble {
  display: flex;
  gap: 12px;
  max-width: 80%;
  animation: fadeInUp 0.25s ease-out;
}

@keyframes fadeInUp {
  from {
    opacity: 0;
    transform: translateY(8px);
  }
  to {
    opacity: 1;
    transform: translateY(0);
  }
}

.message-bubble.user {
  align-self: flex-end;
  flex-direction: row-reverse;
}

.message-bubble.assistant {
  align-self: flex-start;
}

.bubble-avatar {
  width: 34px;
  height: 34px;
  border-radius: var(--radius-md);
  display: flex;
  align-items: center;
  justify-content: center;
  font-size: 12px;
  font-weight: 600;
  flex-shrink: 0;
}

.user .bubble-avatar {
  background-color: var(--color-primary-container);
  color: #fff;
}

.assistant .bubble-avatar {
  background-color: var(--color-secondary);
  color: #fff;
}

.bubble-body {
  display: flex;
  flex-direction: column;
  min-width: 0;
}

.bubble-content {
  padding: 14px 18px;
  border-radius: var(--radius-lg);
  line-height: 1.7;
  font: var(--text-body);
  white-space: pre-wrap;
  word-break: break-word;
}

.bubble-content.user {
  background-color: var(--color-primary-container);
  color: #ffffff;
  border-top-right-radius: var(--radius-sm);
}

.bubble-content.assistant {
  background-color: var(--color-surface);
  color: #303133;
  border-top-left-radius: var(--radius-sm);
  box-shadow: var(--shadow-soft);
}

.citations {
  margin-top: 14px;
  padding-top: 12px;
  border-top: 1px solid var(--color-outline-variant);
  display: flex;
  flex-direction: column;
  gap: 8px;
}

.citation-card {
  display: flex;
  gap: 0;
  border-radius: var(--radius-md);
  background-color: var(--color-surface-low);
  overflow: hidden;
  transition: background-color 0.2s;
}

.citation-card:hover {
  background-color: #e8eaed;
}

.citation-bar {
  width: 4px;
  flex-shrink: 0;
  background-color: var(--color-primary);
}

.citation-info {
  padding: 10px 14px;
  display: flex;
  align-items: center;
  gap: 8px;
  font-size: 13px;
}

.citation-type {
  font: var(--text-metadata);
  color: var(--color-primary);
  background-color: rgba(0, 74, 198, 0.08);
  padding: 2px 8px;
  border-radius: var(--radius-pill);
  text-transform: none;
  letter-spacing: 0;
}

.citation-source {
  color: var(--color-secondary);
  font-size: 13px;
}

.bubble-meta {
  font: var(--text-metadata);
  color: #a8abb2;
  margin-top: 6px;
  text-transform: none;
  letter-spacing: 0;
}

.user .bubble-meta { text-align: right; }
.assistant .bubble-meta { text-align: left; }
</style>
