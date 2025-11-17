<template>
  <el-card>
    <div class="title"><el-icon><Picture /></el-icon><span>以图搜图</span></div>
    <el-input v-model.number="imageId" placeholder="输入一个已有的 image_id（可用上传返回值）" style="max-width: 360px" @keyup.enter.native="onSearch">
      <template #append>
        <el-button type="primary" :loading="loading" @click="onSearch">搜索</el-button>
      </template>
    </el-input>
    <el-empty v-if="!rows.length && inited" description="无结果，请确认 image_id 是否存在或多上传几张" style="margin-top: 16px;" />
    <el-table :data="rows" v-if="rows.length" style="margin-top: 16px">
      <el-table-column prop="rank" label="#" width="60" />
      <el-table-column prop="image_id" label="Image ID" width="140" />
      <el-table-column label="Similarity" width="220">
        <template #default="{ row }">
          <el-progress :percentage="Math.round((row.similarity || 0) * 100)" :text-inside="true" :stroke-width="16" status="success" />
        </template>
      </el-table-column>
    </el-table>
  </el-card>
  <el-skeleton v-if="loading" :rows="4" animated style="margin-top: 12px" />
</template>
<script setup lang="ts">
import api from '../api'
import { ref, onMounted } from 'vue'
import { ElMessage } from 'element-plus'
import { Picture } from '@element-plus/icons-vue'
import { useRoute } from 'vue-router'

const route = useRoute()
const imageId = ref<number | null>(null)
const rows = ref<any[]>([])
const loading = ref(false)
const inited = ref(false)

async function onSearch() {
  if (!imageId.value) return ElMessage.warning('请输入 Image ID')
  loading.value = true
  try {
    const { data } = await api.get(`/search/image/${imageId.value}/similar`, { params: { top_k: 10 } })
    rows.value = data.data.results || []
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || '检索失败')
  } finally {
    loading.value = false
    inited.value = true
  }
}

onMounted(() => {
  const qid = route.query.id
  if (qid) {
    const num = Number(qid)
    if (!Number.isNaN(num)) {
      imageId.value = num
      onSearch()
    }
  }
})
</script>
<style scoped>
.title { display:flex; align-items:center; gap:8px; font-weight:600; margin-bottom:8px; }
</style>
