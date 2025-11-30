<template>
  <el-header class="nav">
    <div class="brand" @click="$router.push('/')">
      <el-icon><Picture /></el-icon>
      <span>Web Image Drive</span>
    </div>
    <el-menu mode="horizontal" :ellipsis="false" class="menu" router>
      <el-menu-item index="/upload">上传</el-menu-item>
      <el-menu-item index="/search/text">文本检索</el-menu-item>
      <el-menu-item index="/search/ocr">OCR 检索</el-menu-item>
      <el-menu-item index="/similar">以图搜图</el-menu-item>
      <el-menu-item index="/health">健康</el-menu-item>
    </el-menu>
    <div class="right">
      <template v-if="auth.user">
        <el-dropdown>
          <span class="el-dropdown-link user">
            <el-avatar size="small">{{ initials }}</el-avatar>
            <span class="username">{{ auth.user.username }}</span>
            <el-icon class="el-icon--right"><ArrowDown /></el-icon>
          </span>
          <template #dropdown>
            <el-dropdown-menu>
              <el-dropdown-item @click="$router.push('/upload')"
                >上传</el-dropdown-item
              >
              <el-dropdown-item divided @click="onLogout"
                >退出登录</el-dropdown-item
              >
            </el-dropdown-menu>
          </template>
        </el-dropdown>
      </template>
      <template v-else>
        <el-button link @click="$router.push('/login')">登录</el-button>
        <el-button type="primary" @click="$router.push('/register')"
          >注册</el-button
        >
      </template>
    </div>
  </el-header>
</template>

<script setup lang="ts">
import { computed } from "vue";
import { useAuth } from "../store_auth";
import { ArrowDown, Picture } from "@element-plus/icons-vue";

const auth = useAuth();
const initials = computed(() =>
  (auth.user?.username?.[0] || "U").toUpperCase()
);

function onLogout() {
  auth.logout();
}
</script>

<style scoped>
.nav {
  display: flex;
  align-items: center;
  gap: 20px;
  border-bottom: 1px solid var(--el-border-color);
}
.brand {
  display: flex;
  align-items: center;
  gap: 8px;
  font-weight: 600;
  cursor: pointer;
}
.menu {
  flex: 1;
}
.right {
  display: flex;
  align-items: center;
  gap: 8px;
}
.user {
  display: inline-flex;
  align-items: center;
  gap: 6px;
}
.username {
  font-size: 14px;
  color: var(--el-text-color-regular);
}
</style>
