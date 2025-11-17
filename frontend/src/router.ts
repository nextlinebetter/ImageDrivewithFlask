import { createRouter, createWebHistory } from 'vue-router'
import Login from './pages/Login.vue'
import Register from './pages/Register.vue'
import Upload from './pages/Upload.vue'
import SearchText from './pages/SearchText.vue'
import SearchOCR from './pages/SearchOCR.vue'
import Similar from './pages/Similar.vue'
import Health from './pages/Health.vue'

export const router = createRouter({
  history: createWebHistory(),
  routes: [
    { path: '/', redirect: '/upload' },
    { path: '/login', component: Login },
    { path: '/register', component: Register },
    { path: '/upload', component: Upload },
    { path: '/search/text', component: SearchText },
    { path: '/search/ocr', component: SearchOCR },
    { path: '/similar', component: Similar },
    { path: '/health', component: Health }
  ]
})
