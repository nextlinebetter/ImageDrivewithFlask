<template>
  <el-card>
    <div class="title"><el-icon><Cpu /></el-icon><span>健康检查</span></div>
    <el-button type="primary" @click="load" :loading="loading">刷新</el-button>
    <el-descriptions v-if="parsed" :column="2" border style="margin-top: 12px">
      <el-descriptions-item label="embedding_backend_config">{{ parsed.embedding_backend_config }}</el-descriptions-item>
      <el-descriptions-item label="embedding_backend_loaded">{{ parsed.embedding_backend_loaded }}</el-descriptions-item>
      <el-descriptions-item label="embedding_dim">{{ parsed.embedding_dim }}</el-descriptions-item>
    </el-descriptions>
    <el-collapse style="margin-top: 12px">
      <el-collapse-item title="原始响应 JSON" name="1">
        <pre v-if="json">{{ json }}</pre>
      </el-collapse-item>
    </el-collapse>
  </el-card>
</template>
<script setup lang="ts">
import api from '../api'
import { ref, onMounted } from 'vue'
import { Cpu } from '@element-plus/icons-vue'

const json = ref<any>(null)
const loading = ref(false)
const parsed = ref<any>(null)

async function load() {
  loading.value = true
  try {
    const { data } = await api.get('/health')
    json.value = JSON.stringify(data, null, 2)
    parsed.value = data
  } finally {
    loading.value = false
  }
}

onMounted(load)
</script>
<style scoped>
.title { display:flex; align-items:center; gap:8px; font-weight:600; margin-bottom:8px; }
</style>
