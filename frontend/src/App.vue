<script setup>
import { ref, onMounted, onBeforeUnmount } from 'vue'
import { fetchPolicies, fetchReports, connectStream } from './api.js'
import PolicyList from './components/PolicyList.vue'
import ReportList from './components/ReportList.vue'

const tab = ref('policies')
const policies = ref([])
const reports = ref([])
const toast = ref('')
let es = null
let toastTimer = null

function showToast(msg) {
  toast.value = msg
  clearTimeout(toastTimer)
  toastTimer = setTimeout(() => (toast.value = ''), 4000)
}

function upsert(list, item) {
  const i = list.findIndex((x) => x.id === item.id)
  if (i >= 0) list[i] = item
  else list.unshift(item)
}

async function load() {
  try {
    policies.value = await fetchPolicies()
  } catch (e) {
    console.error(e)
  }
  try {
    reports.value = await fetchReports()
  } catch (e) {
    console.error(e)
  }
}

onMounted(() => {
  load()
  es = connectStream((msg) => {
    if (msg.type === 'policy') {
      upsert(policies.value, msg.data)
      showToast('新政策：' + msg.data.title)
    } else if (msg.type === 'report') {
      upsert(reports.value, msg.data)
      showToast('新报告：' + msg.data.title)
    }
  })
})

onBeforeUnmount(() => {
  if (es) es.close()
})
</script>

<template>
  <div class="app">
    <header class="topbar">
      <h1>政策速递</h1>
      <nav>
        <button :class="{ active: tab === 'policies' }" @click="tab = 'policies'">
          政策
        </button>
        <button :class="{ active: tab === 'reports' }" @click="tab = 'reports'">
          报告
        </button>
      </nav>
    </header>

    <transition name="fade">
      <div v-if="toast" class="toast">{{ toast }}</div>
    </transition>

    <main class="content">
      <PolicyList v-if="tab === 'policies'" :items="policies" />
      <ReportList v-else :items="reports" />
    </main>
  </div>
</template>

<style scoped>
.topbar {
  display: flex;
  align-items: center;
  justify-content: space-between;
  padding: 14px 22px;
  background: var(--card);
  border-bottom: 1px solid var(--border);
}
.topbar h1 {
  font-size: 18px;
  margin: 0;
}
nav button {
  border: none;
  background: transparent;
  font-size: 14px;
  color: var(--muted);
  padding: 6px 12px;
  cursor: pointer;
  border-radius: 6px;
}
nav button.active {
  color: var(--accent);
  background: #e8f1fb;
  font-weight: 600;
}
.content {
  padding: 18px 22px;
  max-width: 960px;
  margin: 0 auto;
}
.toast {
  position: fixed;
  top: 16px;
  right: 16px;
  background: var(--accent);
  color: #fff;
  padding: 10px 16px;
  border-radius: 8px;
  font-size: 13px;
  box-shadow: 0 4px 14px rgba(0, 0, 0, 0.15);
  z-index: 50;
}
.fade-enter-active,
.fade-leave-active {
  transition: opacity 0.3s;
}
.fade-enter-from,
.fade-leave-to {
  opacity: 0;
}
</style>
