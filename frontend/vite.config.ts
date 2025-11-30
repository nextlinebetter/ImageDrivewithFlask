import { defineConfig } from "vite";
import vue from "@vitejs/plugin-vue";

export default defineConfig({
  plugins: [vue()],
  server: {
    port: 5173,
    proxy: {
      // 本地开发代理到后端，绕过 CORS
      "/api/v1": "http://127.0.0.1:5000",
    },
  },
});
