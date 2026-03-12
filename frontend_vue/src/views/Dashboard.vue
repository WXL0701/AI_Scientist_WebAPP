<template>
  <div>
    <div class="page-header">
      <h2>Dashboard</h2>
    </div>
    <el-row :gutter="16" class="summary-row">
      <el-col :span="6">
        <el-card class="summary-card">
          <div class="summary-title">Total Tasks</div>
          <div class="summary-value">{{ summary.total }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="summary-card">
          <div class="summary-title">Running</div>
          <div class="summary-value running">{{ summary.running }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="summary-card">
          <div class="summary-title">Succeeded</div>
          <div class="summary-value success">{{ summary.succeeded }}</div>
        </el-card>
      </el-col>
      <el-col :span="6">
        <el-card class="summary-card">
          <div class="summary-title">Failed</div>
          <div class="summary-value danger">{{ summary.failed }}</div>
        </el-card>
      </el-col>
    </el-row>

    <el-row :gutter="16">
      <el-col :span="12">
        <el-card>
          <div class="card-title">Recent Activity (Last 7 Days)</div>
          <v-chart :option="activityOption" style="height: 280px" autoresize />
        </el-card>
      </el-col>
      <el-col :span="12">
        <el-card>
          <div class="card-title">Task Status Distribution</div>
          <v-chart :option="distributionOption" style="height: 280px" autoresize />
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, computed } from 'vue'
import client from '../api/client'
import { use } from 'echarts/core'
import { CanvasRenderer } from 'echarts/renderers'
import { BarChart, PieChart } from 'echarts/charts'
import { GridComponent, TooltipComponent, LegendComponent } from 'echarts/components'
import VChart from 'vue-echarts'

use([CanvasRenderer, BarChart, PieChart, GridComponent, TooltipComponent, LegendComponent])

const summary = ref({
  total: 0,
  running: 0,
  succeeded: 0,
  failed: 0
})
const recentActivity = ref<{ date: string; count: number }[]>([])
const statusDistribution = ref<{ status: string; count: number }[]>([])

const activityOption = computed(() => ({
  tooltip: { trigger: 'axis' },
  xAxis: {
    type: 'category',
    data: recentActivity.value.map(item => item.date)
  },
  yAxis: { type: 'value' },
  grid: { left: 40, right: 20, bottom: 30, top: 20 },
  series: [
    {
      type: 'bar',
      data: recentActivity.value.map(item => item.count),
      itemStyle: { color: '#409EFF' }
    }
  ]
}))

const distributionOption = computed(() => ({
  tooltip: { trigger: 'item' },
  legend: { bottom: 0 },
  series: [
    {
      type: 'pie',
      radius: ['45%', '70%'],
      data: statusDistribution.value.map(item => ({
        value: item.count,
        name: item.status
      }))
    }
  ]
}))

const fetchStats = async () => {
  const res = await client.get('/stats/dashboard')
  summary.value = res.data.summary
  recentActivity.value = res.data.recent_activity
  statusDistribution.value = res.data.status_distribution
}

onMounted(() => {
  fetchStats()
})
</script>

<style scoped>
h2 {
  color: #303133;
}
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 16px;
}
.summary-row {
  margin-bottom: 16px;
}
.summary-card {
  text-align: center;
}
.summary-title {
  font-size: 14px;
  color: #909399;
}
.summary-value {
  font-size: 28px;
  font-weight: 600;
  margin-top: 8px;
  color: #303133;
}
.summary-value.running {
  color: #409EFF;
}
.summary-value.success {
  color: #67C23A;
}
.summary-value.danger {
  color: #F56C6C;
}
.card-title {
  font-weight: 600;
  margin-bottom: 8px;
  color: #303133;
}
</style>
