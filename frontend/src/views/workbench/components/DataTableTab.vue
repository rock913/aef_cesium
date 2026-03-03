<template>
  <div class="wrap" aria-label="Data Table">
    <div class="title">Data Table (CSV数据)</div>
    <table class="t">
      <thead>
        <tr>
          <th>metric</th>
          <th>value</th>
          <th>unit</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="r in rows" :key="r.metric">
          <td>{{ r.metric }}</td>
          <td>{{ r.value }}</td>
          <td>{{ r.unit }}</td>
        </tr>
      </tbody>
    </table>
  </div>
</template>

<script setup>
defineProps({
  rows: { type: Array, default: () => [] },
})
</script>

<style scoped>
.wrap {
  position: absolute;
  inset: 0;
  padding: 14px;
  overflow: auto;
  background: rgba(0, 0, 0, 0.65);
}

.title {
  font-size: 12px;
  letter-spacing: 0.12em;
  text-transform: uppercase;
  opacity: 0.80;
  font-weight: 900;
  margin-bottom: 10px;
}

.t {
  width: 100%;
  border-collapse: collapse;
  font-size: 12px;
}

th,
 td {
  padding: 10px 10px;
  border-bottom: 1px solid rgba(255, 255, 255, 0.10);
}

th {
  text-align: left;
  opacity: 0.75;
  letter-spacing: 0.08em;
  text-transform: uppercase;
}
</style>
