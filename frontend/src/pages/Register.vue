<template>
  <el-card class="card">
    <div class="title"><el-icon><UserFilled /></el-icon><span>注册</span></div>
    <el-form :model="form" :rules="rules" ref="formRef" label-width="80px" @keyup.enter="onRegister">
      <el-form-item label="用户名" prop="username"><el-input v-model="form.username" clearable /></el-form-item>
      <el-form-item label="密码" prop="password"><el-input v-model="form.password" show-password /></el-form-item>
      <el-form-item>
        <el-button type="primary" @click="onRegister" :loading="loading">注册</el-button>
        <el-button link @click="$router.push('/login')">去登录</el-button>
      </el-form-item>
    </el-form>
  </el-card>
  <el-result v-if="success" icon="success" title="注册成功" sub-title="现在可以登录啦" />
</template>
<script setup lang="ts">
import { reactive, ref } from 'vue'
import { ElMessage, FormInstance, FormRules } from 'element-plus'
import { UserFilled } from '@element-plus/icons-vue'
import { useRouter } from 'vue-router'
import { useAuth } from '../store_auth'

const router = useRouter()
const auth = useAuth()
const form = reactive({ username: '', password: '' })
const rules: FormRules = {
  username: [{ required: true, message: '请输入用户名', trigger: 'blur' }],
  password: [{ required: true, message: '请输入密码', trigger: 'blur' }]
}
const formRef = ref<FormInstance>()
const loading = ref(false)
const success = ref(false)

async function onRegister() {
  success.value = false
  await formRef.value?.validate()
  loading.value = true
  try {
    await auth.register(form.username.trim(), form.password)
    success.value = true
    ElMessage.success('注册成功，请登录')
    router.push('/login')
  } catch (e: any) {
    ElMessage.error(e?.response?.data?.message || '注册失败')
  } finally {
    loading.value = false
  }
}
</script>
<style scoped>
.card { max-width: 420px; margin: 56px auto; }
.title { display:flex; align-items:center; gap:8px; font-weight:600; margin-bottom:8px; }
</style>
