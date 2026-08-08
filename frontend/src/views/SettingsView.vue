<script setup>
import { ref, onMounted } from 'vue'
import { useModelStore } from '../stores/model.js'
import { ElMessage } from 'element-plus'

const modelStore = useModelStore()

const localModels = ref([])
const isOllamaConnected = ref(false)
const testingConnection = ref(false)

const cloudOptions = [
  { label: 'DeepSeek Chat (DeepSeek-V3 通用模型)', value: 'deepseek-chat' },
  { label: 'DeepSeek Reasoner (DeepSeek-R1 推理模型)', value: 'deepseek-reasoner' },
  { label: 'GPT-4o (OpenAI 旗舰通用模型)', value: 'gpt-4o' },
  { label: 'Claude 3.5 Sonnet (Anthropic 高阶架构模型)', value: 'claude-3-5-sonnet' },
  { label: 'Qwen-Max (通义千问旗舰模型)', value: 'qwen-max' },
  { label: 'Kimi Moonshot (长上下文大模型)', value: 'moonshot-v1-8k' }
]

const presetLocalModels = [
  'qwen2.5:7b',
  'deepseek-r1:7b',
  'qwen2.5:3b',
  'qwen2.5:1.5b'
]

async function checkLocalOllama() {
  testingConnection.value = true
  try {
    const res = await fetch('/models/local')
    if (res.ok) {
      const json = await res.json()
      const data = json.data || {}
      if (data.status === 'connected') {
        isOllamaConnected.value = true
        if (data.models && data.models.length > 0) {
          localModels.value = data.models
          if (!localModels.value.includes(modelStore.localModel)) {
            modelStore.setLocalModel(data.models[0])
          }
        } else {
          localModels.value = presetLocalModels
        }
        ElMessage.success('已成功连接到本地 Ollama 服务 (11434 端口)')
      } else {
        isOllamaConnected.value = false
        localModels.value = presetLocalModels
        ElMessage.warning('未能检测到本地 Ollama 服务，请确认 Ollama 已启动')
      }
    }
  } catch (e) {
    isOllamaConnected.value = false
    localModels.value = presetLocalModels
    ElMessage.error('连接本地服务检测异常: ' + e.message)
  } finally {
    testingConnection.value = false
  }
}

onMounted(() => {
  checkLocalOllama()
})

function handleProviderChange(val) {
  modelStore.setProvider(val)
  ElMessage.info(`已切换为【${val === 'cloud' ? '云端 API 模式' : '本地 Ollama 模式'}】`)
}

function handleSave() {
  modelStore.saveConfig()
  ElMessage.success('模型与端云配置已成功保存！新对话将立即应用该配置。')
}
</script>

<template>
  <div class="settings-container">
    <div class="settings-header">
      <h1 class="page-title">⚙️ 模型管理与端云模式切换</h1>
      <p class="page-subtitle">
        灵活配置大模型服务提供商 (Cloud API vs 本地 Ollama)，支持端侧数据离线隐私与云端高并发推理。
      </p>
    </div>

    <!-- 模式选择区域 -->
    <el-card class="box-card provider-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span class="header-title">1. 选择模型运行模式 (Provider Mode)</span>
          <el-tag :type="modelStore.provider === 'cloud' ? 'primary' : 'success'" effect="dark">
            当前生效: {{ modelStore.provider === 'cloud' ? '☁️ 云端 API' : '🏠 本地 Ollama' }}
          </el-tag>
        </div>
      </template>

      <div class="provider-options">
        <div 
          class="provider-option-box" 
          :class="{ active: modelStore.provider === 'cloud' }"
          @click="handleProviderChange('cloud')"
        >
          <div class="option-icon">☁️</div>
          <div class="option-content">
            <div class="option-title">云端 API 模式 (Cloud API)</div>
            <div class="option-desc">
              调用主流云端大模型 API，具备高并发推理能力与集群弹性拓展能力。
            </div>
            <div class="option-tags">
              <span class="mini-tag">高并发</span>
              <span class="mini-tag">云端集群</span>
            </div>
          </div>
          <div class="option-radio">
            <el-radio v-model="modelStore.provider" label="cloud" size="large">&nbsp;</el-radio>
          </div>
        </div>

        <div 
          class="provider-option-box" 
          :class="{ active: modelStore.provider === 'local' }"
          @click="handleProviderChange('local')"
        >
          <div class="option-icon">🏠</div>
          <div class="option-content">
            <div class="option-title">本地部署模式 (Local Ollama)</div>
            <div class="option-desc">
              基于本地硬件平台纯离线推理，数据 100% 隐私安全，零 Token 运营成本。
            </div>
            <div class="option-tags">
              <span class="mini-tag success">数据离线私密</span>
              <span class="mini-tag success">零 Token 成本</span>
            </div>
          </div>
          <div class="option-radio">
            <el-radio v-model="modelStore.provider" label="local" size="large">&nbsp;</el-radio>
          </div>
        </div>
      </div>
    </el-card>

    <!-- 详细模型设置区 -->
    <el-card class="box-card detail-card" shadow="hover">
      <template #header>
        <div class="card-header">
          <span class="header-title">2. 细粒度模型选型与参数调优</span>
        </div>
      </template>

      <!-- 云端设置项 -->
      <div v-if="modelStore.provider === 'cloud'" class="setting-group">
        <el-form label-position="top">
          <el-form-item label="☁️ 选择或输入云端大模型名称">
            <el-select 
              v-model="modelStore.cloudModel" 
              placeholder="请选择或输入云端模型标识"
              filterable
              allow-create
              style="width: 100%"
              size="large"
              @change="modelStore.saveConfig()"
            >
              <el-option
                v-for="item in cloudOptions"
                :key="item.value"
                :label="item.label"
                :value="item.value"
              />
            </el-select>
            <div class="form-tip">
              支持直接选择常用云端模型标识，或手动输入任意符合 OpenAI 兼容标准的模型名称。
            </div>
          </el-form-item>
        </el-form>
      </div>

      <!-- 本地设置项 -->
      <div v-else class="setting-group">
        <div class="ollama-status-bar" :class="{ online: isOllamaConnected }">
          <div class="status-left">
            <span class="status-dot"></span>
            <span>本地 Ollama 服务状态: <strong>{{ isOllamaConnected ? '服务就绪 (http://127.0.0.1:11434)' : '未连接或未启动' }}</strong></span>
          </div>
          <el-button 
            type="primary" 
            link 
            :loading="testingConnection"
            @click="checkLocalOllama"
          >
            刷新测试连接
          </el-button>
        </div>

        <el-form label-position="top" style="margin-top: 16px;">
          <el-form-item label="🏠 选择或指定本地 Ollama 模型">
            <el-select 
              v-model="modelStore.localModel" 
              placeholder="选择本地模型"
              filterable
              allow-create
              style="width: 100%"
              size="large"
              @change="modelStore.saveConfig()"
            >
              <el-option
                v-for="model in (localModels.length ? localModels : presetLocalModels)"
                :key="model"
                :label="model"
                :value="model"
              >
                <div class="model-option-item">
                  <span>{{ model }}</span>
                  <span v-if="model.includes('7b')" class="model-badge">推荐模型</span>
                </div>
              </el-option>
            </el-select>
            <div class="form-tip">
              可直接选择下拉列表中已下载的模型，或手动输入新的 Ollama 模型标识。
            </div>
          </el-form-item>
        </el-form>
      </div>

      <!-- 通用温度参数 -->
      <el-divider />

      <div class="setting-group">
        <div class="slider-header">
          <span>🎯 采样温度 (Temperature): <strong>{{ modelStore.temperature }}</strong></span>
          <span class="slider-hint">
            {{ modelStore.temperature <= 0.2 ? '严谨精准 (适合 RAG/代码)' : modelStore.temperature >= 0.8 ? '发散创意' : '均衡模式' }}
          </span>
        </div>
        <el-slider 
          v-model="modelStore.temperature" 
          :min="0" 
          :max="1" 
          :step="0.1"
          show-stops
          @change="modelStore.saveConfig()"
        />
      </div>

      <!-- 保存操作区 -->
      <div class="action-footer">
        <el-button type="primary" size="large" @click="handleSave">
          保存所有模型配置
        </el-button>
      </div>
    </el-card>
  </div>
</template>

<style scoped>
.settings-container {
  padding: 32px;
  max-width: 900px;
  margin: 0 auto;
}

.settings-header {
  margin-bottom: 24px;
}

.page-title {
  font-size: 24px;
  font-weight: 700;
  color: var(--color-text-main, #1e293b);
  margin-bottom: 8px;
}

.page-subtitle {
  font-size: 14px;
  color: #64748b;
  line-height: 1.5;
}

.box-card {
  margin-bottom: 24px;
  border-radius: 12px;
}

.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.header-title {
  font-size: 16px;
  font-weight: 600;
}

.provider-options {
  display: grid;
  grid-template-columns: 1fr 1fr;
  gap: 16px;
}

.provider-option-box {
  border: 2px solid #e2e8f0;
  border-radius: 10px;
  padding: 20px;
  display: flex;
  gap: 16px;
  cursor: pointer;
  transition: all 0.2s ease;
  position: relative;
}

.provider-option-box:hover {
  border-color: #93c5fd;
  background-color: #f8fafc;
}

.provider-option-box.active {
  border-color: #2563eb;
  background-color: #eff6ff;
}

.option-icon {
  font-size: 32px;
}

.option-title {
  font-size: 16px;
  font-weight: 600;
  color: #0f172a;
  margin-bottom: 6px;
}

.option-desc {
  font-size: 13px;
  color: #475569;
  line-height: 1.4;
  margin-bottom: 12px;
}

.option-tags {
  display: flex;
  gap: 8px;
}

.mini-tag {
  font-size: 11px;
  background-color: #e0f2fe;
  color: #0369a1;
  padding: 2px 8px;
  border-radius: 4px;
}

.mini-tag.success {
  background-color: #dcfce7;
  color: #15803d;
}

.option-radio {
  position: absolute;
  top: 16px;
  right: 16px;
}

.ollama-status-bar {
  display: flex;
  justify-content: space-between;
  align-items: center;
  padding: 12px 16px;
  background-color: #fef2f2;
  border: 1px solid #fecaca;
  border-radius: 8px;
  font-size: 13px;
  color: #991b1b;
}

.ollama-status-bar.online {
  background-color: #f0fdf4;
  border-color: #bbf7d0;
  color: #166534;
}

.status-left {
  display: flex;
  align-items: center;
  gap: 8px;
}

.status-dot {
  width: 8px;
  height: 8px;
  border-radius: 50%;
  background-color: #ef4444;
}

.ollama-status-bar.online .status-dot {
  background-color: #22c55e;
}

.form-tip {
  font-size: 12px;
  color: #94a3b8;
  margin-top: 6px;
}

.model-option-item {
  display: flex;
  justify-content: space-between;
  align-items: center;
}

.model-badge {
  font-size: 11px;
  color: #2563eb;
  background-color: #eff6ff;
  padding: 1px 6px;
  border-radius: 4px;
}

.slider-header {
  display: flex;
  justify-content: space-between;
  margin-bottom: 12px;
  font-size: 14px;
}

.slider-hint {
  color: #64748b;
  font-size: 13px;
}

.action-footer {
  margin-top: 24px;
  display: flex;
  justify-content: flex-end;
}
</style>
