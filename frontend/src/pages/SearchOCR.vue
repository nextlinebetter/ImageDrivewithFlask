<template>
  <el-card>
    <div class="title">
      <el-icon><Document /></el-icon><span>OCR 文本检索</span>
    </div>
    <el-input
      v-model="q"
      placeholder="输入 OCR 关键词，如：invoice/日期"
      style="max-width: 520px"
      @keyup.enter.native="onSearch"
    >
      <template #append>
        <el-button type="primary" :loading="loading" @click="onSearch"
          >搜索</el-button
        >
      </template>
    </el-input>
    <el-empty
      v-if="!rows.length && inited"
      description="无结果，尝试其他关键词或先进行 OCR 入库"
      style="margin-top: 16px"
    />
    <el-table :data="rows" v-if="rows.length" style="margin-top: 16px">
      <el-table-column prop="image_id" label="Image ID" width="140" />
      <el-table-column label="Snippet">
        <template #default="{ row }">
          <el-tooltip :content="row.snippet" placement="top-start">
            <span class="clip">{{ row.snippet }}</span>
          </el-tooltip>
        </template>
      </el-table-column>
      <el-table-column label="操作" width="140">
        <template #default="{ row }">
          <el-button size="small" @click="goSimilar(row.image_id)"
            >查看相似</el-button
          >
        </template>
      </el-table-column>
    </el-table>
  </el-card>
  <el-skeleton v-if="loading" :rows="4" animated style="margin-top: 12px" />
</template>
<script setup lang="ts">
import api from "../api";
import { ref } from "vue";
import { ElMessage } from "element-plus";
import { Document } from "@element-plus/icons-vue";
import { useRouter } from "vue-router";

const q = ref("invoice");
const rows = ref<any[]>([]);
const loading = ref(false);
const inited = ref(false);
const router = useRouter();

async function onSearch() {
  loading.value = true;
  try {
    const { data } = await api.post("/search/ocr", {
      query: q.value,
      top_k: 10,
    });
    rows.value = data.data.results || [];
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || "检索失败");
  } finally {
    loading.value = false;
    inited.value = true;
  }
}

function goSimilar(id: number) {
  router.push({ path: "/similar", query: { id } });
}
</script>
<style scoped>
.clip {
  display: inline-block;
  max-width: 520px;
  white-space: nowrap;
  overflow: hidden;
  text-overflow: ellipsis;
}
.title {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  margin-bottom: 8px;
}
</style>
