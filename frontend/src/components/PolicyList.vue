<script setup>
import { siteLabel, categoryLabel } from '../sites.js'

defineProps({
  items: { type: Array, default: () => [] },
})
</script>

<template>
  <div>
    <p v-if="!items.length" class="empty">暂无政策数据。</p>
    <table v-else class="policy-table">
      <thead>
        <tr>
          <th>标题</th>
          <th class="col-date">发布日期</th>
          <th class="col-cat">分类</th>
          <th class="col-src">来源</th>
          <th class="col-org">发布机关</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="p in items" :key="p.id">
          <td>
            <a :href="p.source_url" target="_blank" rel="noopener">{{ p.title }}</a>
          </td>
          <td class="col-date">{{ p.pub_date || '—' }}</td>
          <td class="col-cat">
            <span class="cat-chip">{{ categoryLabel(p.category) }}</span>
          </td>
          <td class="col-src">{{ siteLabel(p.source_site) }}</td>
          <td class="col-org">{{ p.issuing_authority || '—' }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<style scoped>
.policy-table {
  width: 100%;
  border-collapse: collapse;
  background: var(--card);
  border: 1px solid var(--border);
  border-radius: 10px;
  overflow: hidden;
}
.policy-table th,
.policy-table td {
  text-align: left;
  padding: 10px 12px;
  font-size: 13px;
  border-bottom: 1px solid var(--border);
}
.policy-table th {
  background: #f0f4f8;
  color: var(--muted);
  font-weight: 600;
}
.policy-table tr:last-child td {
  border-bottom: none;
}
.col-date,
.col-src,
.col-org {
  white-space: nowrap;
  color: var(--muted);
}
.cat-chip {
  display: inline-block;
  padding: 2px 8px;
  font-size: 12px;
  border-radius: 999px;
  background: #e8f0fe;
  color: #1a56db;
  white-space: nowrap;
}
.empty {
  color: var(--muted);
  font-size: 14px;
}
</style>
