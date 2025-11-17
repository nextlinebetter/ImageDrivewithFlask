<template>
  <el-card>
    <div class="title"><el-icon><Search /></el-icon><span>文本检索</span></div>
    <el-input v-model="q" placeholder="输入查询，如：a cat on a chair" style="max-width: 520px" @keyup.enter.native="onSearch">
      <template #append>
        <el-button type="primary" :loading="loading" @click="onSearch">搜索</el-button>
      </template>
    </el-input>
    <el-empty v-if="!rows.length && inited" description="无结果，试试其他关键词" style="margin-top: 16px;" />
    <el-table :data="rows" v-if="rows.length" style="margin-top: 16px">
      <el-table-column prop="rank" label="#" width="60" />
      <el-table-column prop="image_id" label="Image ID" width="140" />
      <el-table-column label="Similarity" width="220">
        <template #default="{ row }">
          <el-progress :percentage="Math.round((row.similarity || 0) * 100)" :text-inside="true" :stroke-width="16" status="success" />
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140">
        <template #default="{ row }">
          <el-button size="small" @click="goSimilar(row.image_id)">查看相似</el-button>
        </template>
      </el-table-column>
    </el-table>
  </el-card>
  <el-skeleton v-if="loading" :rows="4" animated style="margin-top: 12px" />
</template>
<script setup lang="ts">
import api from '../api'
import { ref } from 'vue'
import { ElMessage } from 'element-plus'
import { Search } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'

const q = ref('a cat sitting on a chair')
const rows = ref<any[]>([])
const loading = ref(false)
const inited = ref(false)
const router = useRouter()

async function onSearch() {
  loading.value = true
  try {
    const { data } = await api.post('/search/text', { query: q.value, top_k: 10 })
    rows.value = data.data.results || []
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || '检索失败')
  } finally {
    loading.value = false
    inited.value = true
  }
}

function goSimilar(id: number) {
  router.push({ path: '/similar', query: { id } })
}
</script>
