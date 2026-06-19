<script setup>
defineProps({
  conversation: Object,
})
</script>

<template>
  <div class="history-detail">
    <div class="detail-inner">
      <div class="question-panel">
        <div class="panel-icon">
          <el-icon :size="16"><ChatDotRound /></el-icon>
        </div>
        <div class="panel-body">
          <h4 class="panel-label">用户提问</h4>
          <p class="panel-text">{{ conversation.question }}</p>
        </div>
      </div>

      <div class="answer-card">
        <div class="answer-header">
          <span class="answer-badge">AI 回答</span>
          <span class="answer-time">{{ conversation.timestamp }}</span>
        </div>
        <div class="answer-body">
          <p class="answer-text">{{ conversation.answer }}</p>
        </div>
      </div>

      <div class="meta-bar">
        <div class="meta-chips">
          <span class="meta-chip">
            <el-icon :size="12"><Timer /></el-icon>
            {{ conversation.costTime != null ? conversation.costTime + 's' : '—' }}
          </span>
          <span class="meta-chip">
            <el-icon :size="12"><Cpu /></el-icon>
            DeepSeek-Chat
          </span>
        </div>
        <div class="meta-actions">
          <el-button text size="small">
            <el-icon :size="14"><CopyDocument /></el-icon>
            复制
          </el-button>
          <el-button text size="small">
            <el-icon :size="14"><Refresh /></el-icon>
            重新生成
          </el-button>
        </div>
      </div>
    </div>
  </div>
</template>

<style scoped>
.history-detail {
  width: 100%;
  height: 100%;
  display: flex;
  align-items: flex-start;
  justify-content: center;
  padding: 40px 32px;
}

.detail-inner {
  width: 100%;
  max-width: 720px;
}

.question-panel {
  display: flex;
  gap: 14px;
  padding: 18px 20px;
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-soft);
  margin-bottom: 20px;
}

.panel-icon {
  width: 36px;
  height: 36px;
  border-radius: var(--radius-md);
  background: var(--color-primary);
  color: #fff;
  display: flex;
  align-items: center;
  justify-content: center;
  flex-shrink: 0;
}

.panel-body { flex: 1; }

.panel-label {
  font: var(--text-metadata);
  color: var(--color-secondary);
  margin: 0 0 6px 0;
  text-transform: none;
  letter-spacing: 0;
}

.panel-text {
  font: var(--text-body);
  color: #303133;
  line-height: 1.7;
}

.answer-card {
  background: var(--color-surface);
  border-radius: var(--radius-xl);
  box-shadow: var(--shadow-card);
  overflow: hidden;
  margin-bottom: 20px;
}

.answer-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  border-bottom: 1px solid var(--color-outline-variant);
}

.answer-badge {
  font: var(--text-metadata);
  color: var(--color-primary);
  background: rgba(0, 74, 198, 0.08);
  padding: 3px 12px;
  border-radius: var(--radius-pill);
  text-transform: none;
  letter-spacing: 0;
}

.answer-time {
  font: var(--text-metadata);
  color: #a8abb2;
  text-transform: none;
  letter-spacing: 0;
}

.answer-body {
  padding: 20px;
}

.answer-text {
  font: var(--text-body);
  color: #303133;
  line-height: 1.8;
  white-space: pre-wrap;
  word-break: break-word;
}

/* === Meta Bar === */
.meta-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 14px 20px;
  background: var(--color-surface);
  border-radius: var(--radius-lg);
  box-shadow: var(--shadow-soft);
}

.meta-chips {
  display: flex;
  gap: 10px;
}

.meta-chip {
  display: inline-flex;
  align-items: center;
  gap: 4px;
  font: var(--text-metadata);
  color: var(--color-secondary);
  background: var(--color-surface-low);
  padding: 4px 12px;
  border-radius: var(--radius-pill);
  text-transform: none;
  letter-spacing: 0;
}

.meta-actions {
  display: flex;
  gap: 4px;
}
</style>
