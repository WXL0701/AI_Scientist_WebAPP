<template>
  <div>
    <div class="page-header">
      <h2>Runs</h2>
      <el-button type="primary" @click="showCreateDialog">Create Run</el-button>
    </div>

    <el-table :data="runs" style="width: 100%" v-loading="loading" @row-click="handleRowClick" class="clickable-rows">
      <el-table-column prop="id" label="ID" width="300" />
      <el-table-column prop="project_name" label="Project Name" width="200">
        <template #default="scope">
          {{ scope.row.project_name || '-' }}
        </template>
      </el-table-column>
      <el-table-column prop="status" label="Status">
        <template #default="scope">
          <el-tag :type="getStatusType(scope.row.status)">{{ scope.row.status }}</el-tag>
        </template>
      </el-table-column>
      <el-table-column prop="created_at" label="Created At" />
      <el-table-column prop="creator" label="Creator" width="160" />
      <el-table-column label="Actions" width="200">
        <template #default="scope">
          <el-button type="primary" size="small" @click.stop="handleRowClick(scope.row)">
            Detail
          </el-button>
          <el-button type="danger" size="small" @click.stop="handleDelete(scope.row)">
            Delete
          </el-button>
        </template>
      </el-table-column>
    </el-table>

    <!-- Create Run Dialog -->
    <el-dialog v-model="createVisible" title="Create Run" width="50%">
      <el-alert
        v-if="templateRiskCount > 0"
        type="warning"
        :closable="false"
        show-icon
        class="mb-3"
        :title="`Template checks found ${templateRiskCount} issue(s).`"
        :description="templateRiskDescription"
      />
      <el-alert
        v-else-if="templateChecksLoaded"
        type="success"
        :closable="false"
        show-icon
        class="mb-3"
        title="Template checks passed"
      />
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
        <el-form-item label="Project Name (optional)">
          <el-input v-model="createForm.project_name" placeholder="e.g. wxl_test20260128_03" />
        </el-form-item>
        <el-form-item label="Content">
          <el-input
            v-model="createForm.content"
            type="textarea"
            :rows="10"
            placeholder="Describe your experiment here..."
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
import { ref, reactive, onMounted, computed } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, ElMessageBox } from 'element-plus'
import client from '../api/client'

const router = useRouter()
const runs = ref<any[]>([])
const loading = ref(false)
const createVisible = ref(false)
const creating = ref(false)

const createForm = reactive({
  project_name: '',
  content: '',
  yaml_filename: 'challenge.yaml',
  project_id: '',
  prompt_version_id: null as number | null
})

const selectedPrompt = ref([]) // [setId, versionId]
const promptOptions = ref<any[]>([])
const templateChecksLoaded = ref(false)
const missingTemplatePairs = ref<string[]>([])
const missingReferencePairs = ref<string[]>([])
const invalidApplicability = ref<string[]>([])

const templateRiskCount = computed(() => {
  return missingTemplatePairs.value.length + missingReferencePairs.value.length + invalidApplicability.value.length
})

const templateRiskDescription = computed(() => {
  const parts: string[] = []
  if (missingTemplatePairs.value.length > 0) {
    parts.push(`missing experiment_template: ${missingTemplatePairs.value.join(', ')}`)
  }
  if (missingReferencePairs.value.length > 0) {
    parts.push(`missing experiment_reference: ${missingReferencePairs.value.join(', ')}`)
  }
  if (invalidApplicability.value.length > 0) {
    parts.push(`applicability missing: ${invalidApplicability.value.join(', ')}`)
  }
  return parts.join(' | ')
})

const fetchRuns = async () => {
  loading.value = true
  try {
    const res = await client.get('/runs')
    if (Array.isArray(res.data)) {
      runs.value = res.data
    } else {
      console.error('API /runs returned non-array data:', res.data)
      runs.value = []
      ElMessage.warning('Received invalid data format from server')
    }
  } catch (error) {
    ElMessage.error('Failed to fetch runs')
  } finally {
    loading.value = false
  }
}

const fetchPromptVersions = async (setId: number) => {
  const setOption = promptOptions.value.find(p => p.id === setId)
  if (!setOption || setOption.versions.length > 0) {
    return
  }
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

const fetchTemplateChecks = async () => {
  try {
    const res = await client.get('/templates/checks')
    missingTemplatePairs.value = Array.isArray(res.data?.missing_template_pairs) ? res.data.missing_template_pairs : []
    missingReferencePairs.value = Array.isArray(res.data?.missing_reference_pairs) ? res.data.missing_reference_pairs : []
    const applicability = Array.isArray(res.data?.reference_applicability) ? res.data.reference_applicability : []
    invalidApplicability.value = applicability.filter((item: any) => !item.ok).map((item: any) => item.name)
    templateChecksLoaded.value = true
  } catch (error) {
    templateChecksLoaded.value = false
    missingTemplatePairs.value = []
    missingReferencePairs.value = []
    invalidApplicability.value = []
  }
}

const handleExpandChange = async (val: any) => {
  if (val && val.length > 0) {
    const setId = val[val.length - 1]
    await fetchPromptVersions(setId)
  }
}

const showCreateDialog = async () => {
  createVisible.value = true
  if (promptOptions.value.length === 0) {
    await fetchPromptSets()
  }
  const ids = promptOptions.value.map(p => p.id)
  await Promise.all([Promise.all(ids.map((id: number) => fetchPromptVersions(id))), fetchTemplateChecks()])
}

const handleCreate = async () => {
  if (!selectedPrompt.value || selectedPrompt.value.length !== 2) {
    ElMessage.warning('Please select a prompt version')
    return
  }
  if (!createForm.content.trim()) {
    ElMessage.warning('Please enter content')
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

const handleDelete = async (row: any) => {
  try {
    await ElMessageBox.confirm(
      'Are you sure you want to delete this run? This action cannot be undone.',
      'Warning',
      {
        confirmButtonText: 'Delete',
        cancelButtonText: 'Cancel',
        type: 'warning',
      }
    )
    await client.delete(`/runs/${row.id}`)
    ElMessage.success('Run deleted')
    fetchRuns()
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error('Failed to delete run')
    }
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

onMounted(() => {
  fetchRuns()
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
  margin-bottom: 20px;
}
.clickable-rows :deep(.el-table__row) {
  cursor: pointer;
}
.mb-3 {
  margin-bottom: 12px;
}
</style>
