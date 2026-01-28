<template>
  <div v-loading="loading">
    <div class="page-header" v-if="run">
      <div>
        <h2>Run Detail</h2>
        <div class="meta">
          <span>ID: {{ run.id }}</span>
          <el-tag :type="getStatusType(run.status)" class="ml-2">{{ run.status }}</el-tag>
          <span class="ml-2">{{ run.created_at }}</span>
        </div>
      </div>
      <div>
        <el-button 
          v-if="run.status === 'running' || run.status === 'pending'" 
          type="danger" 
          @click="handleCancel"
        >
          Cancel Run
        </el-button>
        <el-button @click="fetchRun">Refresh</el-button>
      </div>
    </div>

    <el-tabs v-model="activeTab" class="mt-4">
      <el-tab-pane label="Stages" name="stages">
        <el-timeline>
          <el-timeline-item
            v-for="(task, index) in tasks"
            :key="index"
            :timestamp="task.timestamp"
            :type="getStageStatusType(task.status)"
            :hollow="task.status === 'processing'"
          >
            <h4>{{ task.stage }}</h4>
            <p>{{ task.content }}</p>
            <p v-if="task.result_path">Result: {{ task.result_path }}</p>
          </el-timeline-item>
        </el-timeline>
        <el-empty v-if="tasks.length === 0" description="No stages yet" />
      </el-tab-pane>

      <el-tab-pane label="Artifacts" name="artifacts">
        <el-table :data="artifacts" style="width: 100%">
          <el-table-column prop="kind" label="Kind" />
          <el-table-column prop="path" label="Path" />
          <el-table-column label="Actions">
            <template #default="scope">
              <el-button size="small" @click="handleDownload(scope.row.path)">Download</el-button>
            </template>
          </el-table-column>
        </el-table>
      </el-tab-pane>

      <el-tab-pane label="Logs" name="logs">
        <div class="log-viewer" ref="logViewer">
          <pre>{{ logs }}</pre>
        </div>
      </el-tab-pane>
    </el-tabs>
  </div>
</template>

<script setup lang="ts">
import { ref, onMounted, onUnmounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import client from '../api/client'

const route = useRoute()
const runId = route.params.id as string

const loading = ref(false)
const run = ref<any>(null)
const tasks = ref<any[]>([])
const artifacts = ref<any[]>([])
const logs = ref('')
const activeTab = ref('stages')

let pollInterval: any = null

const fetchRun = async () => {
  try {
    const res = await client.get(`/runs/${runId}`)
    run.value = res.data
    
    // Fetch Stages
    const stagesRes = await client.get(`/runs/${runId}/stages`)
    // Backend returns { db_path: ..., tasks: [...] }
    tasks.value = stagesRes.data.tasks || []

    // Fetch Artifacts
    const artRes = await client.get(`/runs/${runId}/artifacts`)
    artifacts.value = artRes.data

    // Fetch Logs (stdout)
    // Note: /download?path=logs%2Fstdout.log
    try {
      const logRes = await client.get(`/runs/${runId}/download`, {
        params: { path: 'logs/stdout.log' },
        responseType: 'text'
      })
      logs.value = logRes.data
    } catch (e) {
      logs.value = '(No logs yet)'
    }

  } catch (error) {
    ElMessage.error('Failed to fetch run details')
  }
}

const handleCancel = async () => {
  try {
    await client.post(`/runs/${runId}/cancel`)
    ElMessage.success('Run canceled')
    fetchRun()
  } catch (error) {
    ElMessage.error('Failed to cancel run')
  }
}

const handleDownload = (path: string) => {
  // Direct window.open or link creation
  // Need to add auth token? Backend /download endpoint checks Bearer token.
  // So we can't just window.open. We need to fetch blob and save.
  downloadFile(path)
}

const downloadFile = async (path: string) => {
  try {
    const res = await client.get(`/runs/${runId}/download`, {
      params: { path },
      responseType: 'blob'
    })
    const url = window.URL.createObjectURL(new Blob([res.data]))
    const link = document.createElement('a')
    link.href = url
    link.setAttribute('download', path.split('/').pop() || 'download')
    document.body.appendChild(link)
    link.click()
    document.body.removeChild(link)
  } catch (error) {
    ElMessage.error('Download failed')
  }
}

const getStatusType = (status: string) => {
  switch (status) {
    case 'completed': return 'success'
    case 'running': return 'primary'
    case 'failed': return 'danger'
    case 'canceled': return 'info'
    default: return 'warning'
  }
}

const getStageStatusType = (status: string) => {
    // Timeline types: primary, success, warning, danger, info
    switch(status) {
        case 'completed': return 'success'
        case 'processing': return 'primary'
        case 'failed': return 'danger'
        default: return 'info'
    }
}

onMounted(() => {
  loading.value = true
  fetchRun().finally(() => {
    loading.value = false
    // Start polling if running
    if (run.value?.status === 'running' || run.value?.status === 'pending') {
      pollInterval = setInterval(fetchRun, 3000)
    }
  })
})

onUnmounted(() => {
  if (pollInterval) clearInterval(pollInterval)
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.meta {
  color: #666;
  margin-top: 5px;
}
.ml-2 {
  margin-left: 10px;
}
.mt-4 {
  margin-top: 20px;
}
.log-viewer {
  background-color: #1e1e1e;
  color: #d4d4d4;
  padding: 15px;
  border-radius: 4px;
  height: 500px;
  overflow-y: auto;
  font-family: monospace;
}
</style>
