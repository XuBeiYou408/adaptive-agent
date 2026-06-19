<script setup>
import { ref, onMounted, computed } from 'vue'
import { getEvalResults, getDatasetInfo } from '../api/index.js'
import ScoreCards from '../components/ScoreCards.vue'
import CaseTable from '../components/CaseTable.vue'
import SuggestionsPanel from '../components/SuggestionsPanel.vue'

const loading = ref(true)
const error = ref('')
const evalData = ref(null)
const datasetInfo = ref(null)
const statusFilter = ref('all')

onMounted(async () => {
  try {
    const [results, dataset] = await Promise.all([
      getEvalResults(),
      getDatasetInfo().catch(() => null),
    ])
    evalData.value = results
    datasetInfo.value = dataset
  } catch (e) {
    error.value = e.message || '加载评估数据失败'
  } finally {
    loading.value = false
  }
})

const summary = computed(() => {
  if (!evalData.value) return null
  const cases = evalData.value
  const total = cases.length

  const hits = cases.filter(c => c.retrieval_hit).length
  const hitRate = total > 0 ? (hits / total) * 100 : 0

  const mrrSum = cases.reduce((sum, c) => sum + (c.mrr_score || 0), 0)
  const mrr = total > 0 ? mrrSum / total : 0

  const faithfulCases = cases.filter(c => c.faithfulness != null)
  const relevantCases = cases.filter(c => c.answer_relevance != null)
  const completeCases = cases.filter(c => c.completeness != null)

  const avg = (arr, key) => arr.length > 0
    ? arr.reduce((s, c) => s + c[key], 0) / arr.length
    : 0

  const ttftCases = cases.filter(c => c.ttft_ms != null)
  const latencyCases = cases.filter(c => c.total_latency_ms != null)

  return {
    total,
    hitRate: hitRate.toFixed(1),
    mrr: mrr.toFixed(3),
    avgFaithfulness: faithfulCases.length > 0 ? avg(faithfulCases, 'faithfulness') : null,
    avgRelevance: relevantCases.length > 0 ? avg(relevantCases, 'answer_relevance') : null,
    avgCompleteness: completeCases.length > 0 ? avg(completeCases, 'completeness') : null,
    avgTTFT: ttftCases.length > 0 ? avg(ttftCases, 'ttft_ms') / 1000 : null,
    avgLatency: latencyCases.length > 0 ? avg(latencyCases, 'total_latency_ms') / 1000 : null,
  }
})

const statusCounts = computed(() => {
  if (!evalData.value) return { pass: 0, warn: 0, fail: 0 }
  let pass = 0, warn = 0, fail = 0
  for (const c of evalData.value) {
    const avgScore = (c.faithfulness || 0) + (c.answer_relevance || 0) + (c.completeness || 0)
    const normalized = avgScore / 3
    if (normalized >= 0.7) pass++
    else if (normalized >= 0.4) warn++
    else fail++
  }
  return { pass, warn, fail }
})

const filteredCases = computed(() => {
  if (!evalData.value) return []
  if (statusFilter.value === 'all') return evalData.value
  return evalData.value.filter(c => {
    const avgScore = (c.faithfulness || 0) + (c.answer_relevance || 0) + (c.completeness || 0)
    const normalized = avgScore / 3
    if (statusFilter.value === 'pass') return normalized >= 0.7
    if (statusFilter.value === 'warn') return normalized >= 0.4 && normalized < 0.7
    if (statusFilter.value === 'fail') return normalized < 0.4
    return true
  })
})

function getScoreColor(score) {
  if (score == null) return '#909399'
  if (score >= 0.8) return 'var(--color-success-text)'
  if (score >= 0.5) return 'var(--color-warning-text)'
  return 'var(--color-error-text)'
}
</script>

<template>
  <div class="evaluation-view">
    <header class="eval-header">
      <div class="eval-header-top">
        <div>
          <h1>评估大盘</h1>
          <span v-if="datasetInfo" class="eval-subtitle">
            测试集 {{ datasetInfo.count }} 题
          </span>
        </div>
        <el-input
          placeholder="搜索评估记录..."
          prefix-icon="Search"
          class="eval-search"
          size="small"
        />
      </div>
    </header>

    <div v-if="loading" class="eval-loading">
      <el-skeleton :rows="5" animated />
    </div>

    <div v-else-if="error" class="eval-empty">
      <el-empty description="暂未运行评估">
        <template #extra>
          <p class="eval-empty-hint">请先运行 evaluator/evaluator.py 生成评估结果</p>
        </template>
      </el-empty>
    </div>

    <template v-else-if="summary">
      <ScoreCards :summary="summary" :getColor="getScoreColor" />

      <div class="status-filter">
        <span
          :class="['filter-tag', 'all', { active: statusFilter === 'all' }]"
          @click="statusFilter = 'all'"
        >
          全部 {{ statusCounts.pass + statusCounts.warn + statusCounts.fail }}
        </span>
        <span
          :class="['filter-tag', 'pass', { active: statusFilter === 'pass' }]"
          @click="statusFilter = 'pass'"
        >
          高分 {{ statusCounts.pass }}
        </span>
        <span
          :class="['filter-tag', 'warn', { active: statusFilter === 'warn' }]"
          @click="statusFilter = 'warn'"
        >
          待改进 {{ statusCounts.warn }}
        </span>
        <span
          :class="['filter-tag', 'fail', { active: statusFilter === 'fail' }]"
          @click="statusFilter = 'fail'"
        >
          失败 {{ statusCounts.fail }}
        </span>
      </div>

      <CaseTable
        :cases="filteredCases"
        :getColor="getScoreColor"
      />
      <SuggestionsPanel :summary="summary" />
    </template>
  </div>
</template>

<style scoped>
.evaluation-view {
  padding: 24px 32px;
  max-width: 1280px;
}

.eval-header { margin-bottom: 24px; }

.eval-header-top {
  display: flex;
  justify-content: space-between;
  align-items: flex-start;
}

.eval-header h1 {
  font: var(--text-section);
  color: #303133;
  margin: 0;
}

.eval-subtitle {
  font: var(--text-metadata);
  color: var(--color-secondary);
  margin-top: 4px;
  display: block;
  text-transform: none;
  letter-spacing: 0;
}

.eval-search { width: 260px; }

.eval-loading { padding: 40px 0; }

.eval-empty { padding: 60px 0; text-align: center; }

.eval-empty-hint {
  font-size: 13px;
  color: #a8abb2;
  margin-top: 8px;
}

/* === Status Filter === */
.status-filter {
  display: flex;
  gap: 10px;
  margin-bottom: 20px;
}

.filter-tag {
  padding: 6px 16px;
  border-radius: var(--radius-pill);
  font: var(--text-metadata);
  cursor: pointer;
  transition: all 0.2s;
  text-transform: none;
  letter-spacing: 0;
  border: 1px solid var(--color-outline-variant);
  color: var(--color-secondary);
  background: var(--color-surface);
}

.filter-tag:hover {
  border-color: var(--color-primary);
  color: var(--color-primary);
}

.filter-tag.active {
  color: #fff;
  border-color: transparent;
}

.filter-tag.all.active {
  background: var(--color-primary);
}

.filter-tag.pass.active {
  background: var(--color-success-text);
}

.filter-tag.warn.active {
  background: var(--color-warning-text);
}

.filter-tag.fail.active {
  background: var(--color-error-text);
}
</style>
