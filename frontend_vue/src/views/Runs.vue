<template>
  <div>
    <div class="page-header">
      <h2>Runs</h2>
      <el-button type="primary" @click="showCreateDialog">Create Run</el-button>
    </div>

    <el-table :data="runs" style="width: 100%" v-loading="loading" @row-click="handleRowClick" class="clickable-rows">
      <el-table-column prop="id" label="ID" width="300" />
      <el-table-column prop="status" label="Status">
        <template #default="scope">
          <el-tag :type="getStatusType(scope.row.status)">{{ scope.row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="Created At" />
    </el-table>

    <!-- Create Run Dialog -->
    <el-dialog v-model="createVisible" title="Create Run" width="50%">
      <el-form :model="createForm" label-position="top">
        <el-form-item label="Prompt Version">
           <el-cascader
            v-model="selectedPrompt"
            :options="promptOptions"
            :props="{ label: 'name', value: 'id', children: 'versions' }"
            placeholder="Select Prompt Set / Version"
            style="width: 100%"
            @expand-change="handleExpandChange"
           />
        </el-form-item>
        <el-form-item label="YAML Configuration">
          <el-input 
            v-model="createForm.yaml_text" 
            type="textarea" 
            :rows="10" 
            placeholder="Enter YAML configuration..."
          />
        </el-form-item>
      </el-form>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="createVisible = false">Cancel</el-button>
          <el-button type="primary" :loading="creating" @click="handleCreate">Create</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive, onMounted } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage } from 'element-plus'
import client from '../api/client'

const router = useRouter()
const runs = ref([])
const loading = ref(false)
const createVisible = ref(false)
const creating = ref(false)

const createForm = reactive({
  yaml_text: `project_name: my_experiment
username: ignored
max_workers: 1
content: |
  Describe your experiment here...
`,
  yaml_filename: 'challenge.yaml',
  project_id: '',
  prompt_version_id: null as number | null
})

const selectedPrompt = ref([]) // [setId, versionId]
const promptOptions = ref<any[]>([])

const fetchRuns = async () => {
  loading.value = true
  try {
    const res = await client.get('/runs')
    runs.value = res.data
  } catch (error) {
    ElMessage.error('Failed to fetch runs')
  } finally {
    loading.value = false
  }
}

const fetchPromptSets = async () => {
  try {
    const res = await client.get('/promptsets')
    promptOptions.value = res.data.map((s: any) => ({
      id: s.id,
      name: s.name,
      versions: [] // To be loaded
    }))
  } catch (error) {
    console.error(error)
  }
}

const handleExpandChange = async (val: any) => {
  // val is array of keys. Since we only have 2 levels, we care about the first level (setId)
  // Element Plus cascader expand-change emits array of keys for expanded nodes
  if (val && val.length > 0) {
    const setId = val[val.length - 1]
    // Check if versions already loaded for this set
    const setOption = promptOptions.value.find(p => p.id === setId)
    if (setOption && setOption.versions.length === 0) {
      try {
        const res = await client.get(`/promptsets/${setId}/versions`)
        setOption.versions = res.data.map((v: any) => ({
          id: v.id,
          name: v.notes || `v${v.id} (${v.created_at})`
        }))
      } catch (e) {
        console.error(e)
      }
    }
  }
}

const showCreateDialog = () => {
  createVisible.value = true
  if (promptOptions.value.length === 0) {
    fetchPromptSets()
  }
}

const handleCreate = async () => {
  if (!selectedPrompt.value || selectedPrompt.value.length !== 2) {
    ElMessage.warning('Please select a prompt version')
    return
  }
  
  creating.value = true
  try {
    const payload = {
      ...createForm,
      prompt_version_id: selectedPrompt.value[1]
    }
    await client.post('/runs', payload)
    ElMessage.success('Run created')
    createVisible.value = false
    fetchRuns()
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || 'Failed to create run')
  } finally {
    creating.value = false
  }
}

const handleRowClick = (row: any) => {
  router.push(`/runs/${row.id}`)
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

onMounted(() => {
  fetchRuns()
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.clickable-rows :deep(.el-table__row) {
  cursor: pointer;
}
</style>
