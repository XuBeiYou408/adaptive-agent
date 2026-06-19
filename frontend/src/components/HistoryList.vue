<script setup>
defineProps({
  conversations: Array,
  selectedId: String,
})

const emit = defineEmits(['select', 'delete'])

function getStatus(conv) {
  if (conv.costTime != null && conv.costTime < 3) return 'success'
  return 'history'
}
</script>

<template>
  <div class="history-list">
    <div v-if="conversations.length === 0" class="list-empty">
      <el-empty description="暂无匹配记录" :image-size="48" />
    </div>
    <div
      v-for="conv in conversations"
      :key="conv.id"
      :class="['history-item', { active: conv.id === selectedId }]"
      @click="emit('select', conv)"
    >
      <div class="item-main">
        <div class="item-top">
          <span :class="['item-status', getStatus(conv)]">
            {{ getStatus(conv) === 'success' ? '成功' : '历史' }}
          </span>
          <span class="item-time">{{ conv.timestamp }}</span>
        </div>
        <div class="item-question">{{ conv.question }}</div>
        <div class="item-preview">{{ conv.answer?.slice(0, 80) }}{{ conv.answer?.length > 80 ? '...' : '' }}</div>
      </div>
      <div class="item-actions">
        <el-button
          text
          size="small"
          class="hover-action"
          @click.stop="emit('delete', conv.id)"
        >
          <el-icon :size="14"><Delete /></el-icon>
        </el-button>
      </div>
    </div>
  </div>
</template>

<style scoped>
.history-list {
  flex: 1;
  overflow-y: auto;
  padding: 0 12px 12px;
}

.list-empty {
  padding: 40px 0;
}

.history-item {
  display: flex;
  align-items: flex-start;
  gap: 8px;
  padding: 14px;
  border-radius: var(--radius-lg);
  cursor: pointer;
  margin-bottom: 4px;
  transition: background-color 0.2s;
}

.history-item:hover {
  background-color: var(--color-surface-low);
}

.history-item.active {
  background-color: #f1f5f9;
  border-left: 3px solid var(--color-primary);
}

.item-main {
  flex: 1;
  overflow: hidden;
  min-width: 0;
}

.item-top {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 6px;
}

.item-status {
  font: var(--text-metadata);
  padding: 1px 8px;
  border-radius: var(--radius-pill);
  text-transform: none;
  letter-spacing: 0;
}

.item-status.success {
  color: var(--color-success-text);
  background: var(--color-success-bg);
}

.item-status.history {
  color: var(--color-secondary);
  background: var(--color-surface-low);
}

.item-time {
  font: var(--text-metadata);
  color: #a8abb2;
  text-transform: none;
  letter-spacing: 0;
}

.item-question {
  font-size: 14px;
  font-weight: 500;
  color: #303133;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
  margin-bottom: 4px;
}

.item-preview {
  font-size: 12px;
  color: #909399;
  line-height: 1.5;
  display: -webkit-box;
  -webkit-line-clamp: 2;
  -webkit-box-orient: vertical;
  overflow: hidden;
}

.item-actions {
  opacity: 0;
  transition: opacity 0.2s;
  flex-shrink: 0;
}

.history-item:hover .item-actions {
  opacity: 1;
}

.hover-action {
  color: var(--color-error-text);
}
</style>
