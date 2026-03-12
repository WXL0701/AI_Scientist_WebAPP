<template>
  <div v-loading="loading">
    <div class="page-header">
      <h2>Templates</h2>
      <div class="actions">
        <el-button @click="refreshAll">Refresh</el-button>
        <el-button type="primary" @click="openUpload">Upload .md</el-button>
        <input ref="fileInput" type="file" accept=".md" class="hidden-input" @change="handleFileChange" />
      </div>
    </div>

    <el-row :gutter="20">
      <el-col :span="8">
        <el-card>
          <template #header>
            <div class="card-header">
              <el-select v-model="selectedType" style="width: 100%" @change="onTypeChange">
                <el-option v-for="t in templateTypes" :key="t" :label="t" :value="t" />
              </el-select>
            </div>
          </template>
          <el-table :data="items" height="540" stripe @row-click="handleSelectTemplate">
            <el-table-column prop="name" label="Name" />
            <el-table-column prop="updated_at" label="Updated" width="170">
              <template #default="scope">
                {{ formatDate(scope.row.updated_at) }}
              </template>
            </el-table-column>
            <el-table-column label="Size" width="90">
              <template #default="scope">
                {{ formatSize(scope.row.size) }}
              </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <el-col :span="10">
        <el-card>
          <template #header>
            <div class="card-header">
              <span>{{ selectedName ? `${selectedType}/${selectedName}.md` : 'Select a template' }}</span>
              <div>
                <el-button :disabled="!selectedName" @click="reloadSelected">Reload</el-button>
                <el-button type="primary" :disabled="!selectedName" :loading="saving" @click="saveTemplate">Save</el-button>
                <el-button
                  type="danger"
                  :disabled="!selectedName || selectedName === 'default'"
                  :loading="deleting"
                  @click="deleteSelected"
                >
                  Delete
                </el-button>
              </div>
            </div>
          </template>
          <el-input
            v-model="content"
            type="textarea"
            :rows="28"
            resize="none"
            placeholder="Template content"
            :disabled="!selectedName"
          />
        </el-card>
      </el-col>

      <el-col :span="6">
        <el-card>
          <template #header>
            <span>Checks</span>
          </template>
          <el-alert
            v-if="missingTemplatePairs.length === 0 && missingReferencePairs.length === 0 && invalidApplicability.length === 0"
            type="success"
            title="No issues found"
            :closable="false"
            show-icon
          />

          <div v-if="missingTemplatePairs.length > 0" class="check-block">
            <div class="check-title">Missing experiment_template</div>
            <el-tag v-for="name in missingTemplatePairs" :key="`mt-${name}`" type="warning" class="tag">
              {{ name }}
            </el-tag>
          </div>

          <div v-if="missingReferencePairs.length > 0" class="check-block">
            <div class="check-title">Missing experiment_reference</div>
            <el-tag v-for="name in missingReferencePairs" :key="`mr-${name}`" type="warning" class="tag">
              {{ name }}
            </el-tag>
          </div>

          <div v-if="invalidApplicability.length > 0" class="check-block">
            <div class="check-title">Applicability warnings</div>
            <el-tag v-for="item in invalidApplicability" :key="`ra-${item.name}`" type="danger" class="tag">
              {{ item.name }}
            </el-tag>
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'
import { ElMessage, ElMessageBox } from 'element-plus'
import client from '../api/client'

type TemplateItem = {
  name: string
  filename: string
  size: number
  updated_at: string
  is_default: boolean
}

type ApplicabilityCheck = {
  name: string
  ok: boolean
  reason: string
}

const templateTypes = [
  'hypothesis_summary',
  'experiment_reference',
  'experiment_template',
  'experiment_record_completion',
]

const loading = ref(false)
const saving = ref(false)
const deleting = ref(false)
const items = ref<TemplateItem[]>([])
const selectedType = ref<string>('experiment_reference')
const selectedName = ref<string>('')
const content = ref<string>('')
const fileInput = ref<HTMLInputElement | null>(null)

const missingTemplatePairs = ref<string[]>([])
const missingReferencePairs = ref<string[]>([])
const referenceApplicability = ref<ApplicabilityCheck[]>([])

const invalidApplicability = computed(() => referenceApplicability.value.filter((x) => !x.ok))

const formatDate = (value: string) => {
  if (!value) return '-'
  return new Date(value).toLocaleString()
}

const formatSize = (size: number) => {
  if (size < 1024) return `${size} B`
  if (size < 1024 * 1024) return `${(size / 1024).toFixed(1)} KB`
  return `${(size / 1024 / 1024).toFixed(1)} MB`
}

const fetchItems = async () => {
  loading.value = true
  try {
    const res = await client.get('/templates', { params: { template_type: selectedType.value } })
    items.value = Array.isArray(res.data?.items) ? res.data.items : []
    if (items.value.length === 0) {
      selectedName.value = ''
      content.value = ''
    } else if (!selectedName.value || !items.value.some((x) => x.name === selectedName.value)) {
      const firstItem = items.value[0]
      if (firstItem) {
        selectedName.value = firstItem.name
        await fetchContent(selectedName.value)
      }
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || 'Failed to fetch templates')
  } finally {
    loading.value = false
  }
}

const fetchContent = async (name: string) => {
  if (!name) {
    content.value = ''
    return
  }
  try {
    const res = await client.get(`/templates/${selectedType.value}/${name}`)
    selectedName.value = name
    content.value = typeof res.data?.content === 'string' ? res.data.content : ''
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || 'Failed to fetch template content')
  }
}

const fetchChecks = async () => {
  try {
    const res = await client.get('/templates/checks')
    missingTemplatePairs.value = Array.isArray(res.data?.missing_template_pairs) ? res.data.missing_template_pairs : []
    missingReferencePairs.value = Array.isArray(res.data?.missing_reference_pairs) ? res.data.missing_reference_pairs : []
    referenceApplicability.value = Array.isArray(res.data?.reference_applicability) ? res.data.reference_applicability : []
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || 'Failed to fetch checks')
  }
}

const refreshAll = async () => {
  await Promise.all([fetchItems(), fetchChecks()])
}

const onTypeChange = async () => {
  selectedName.value = ''
  content.value = ''
  await fetchItems()
}

const handleSelectTemplate = async (row: TemplateItem) => {
  await fetchContent(row.name)
}

const reloadSelected = async () => {
  if (!selectedName.value) return
  await fetchContent(selectedName.value)
}

const saveTemplate = async () => {
  if (!selectedName.value) return
  saving.value = true
  try {
    await client.put(`/templates/${selectedType.value}/${selectedName.value}`, { content: content.value })
    ElMessage.success('Saved')
    await Promise.all([fetchItems(), fetchChecks()])
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || 'Failed to save template')
  } finally {
    saving.value = false
  }
}

const deleteSelected = async () => {
  if (!selectedName.value) return
  try {
    await ElMessageBox.confirm(
      `Delete ${selectedType.value}/${selectedName.value}.md ?`,
      'Warning',
      {
        confirmButtonText: 'Delete',
        cancelButtonText: 'Cancel',
        type: 'warning',
      }
    )
    deleting.value = true
    await client.delete(`/templates/${selectedType.value}/${selectedName.value}`)
    ElMessage.success('Deleted')
    selectedName.value = ''
    content.value = ''
    await Promise.all([fetchItems(), fetchChecks()])
  } catch (error: any) {
    if (error !== 'cancel') {
      ElMessage.error(error.response?.data?.detail || 'Failed to delete template')
    }
  } finally {
    deleting.value = false
  }
}

const openUpload = () => {
  if (!fileInput.value) return
  fileInput.value.value = ''
  fileInput.value.click()
}

const handleFileChange = async (event: Event) => {
  const input = event.target as HTMLInputElement
  const file = input.files?.[0]
  if (!file) return
  const formData = new FormData()
  formData.append('template_type', selectedType.value)
  formData.append('file', file)
  try {
    await client.post('/templates/upload', formData)
    ElMessage.success('Uploaded')
    await Promise.all([fetchItems(), fetchChecks()])
    const nextName = file.name.replace(/\.md$/i, '')
    if (nextName) {
      await fetchContent(nextName)
    }
  } catch (error: any) {
    ElMessage.error(error.response?.data?.detail || 'Failed to upload template')
  } finally {
    input.value = ''
  }
}

onMounted(async () => {
  await refreshAll()
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
.actions {
  display: flex;
  gap: 10px;
}
.hidden-input {
  display: none;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  gap: 8px;
}
.check-block {
  margin-top: 12px;
}
.check-title {
  font-weight: 600;
  margin-bottom: 8px;
}
.tag {
  margin-right: 6px;
  margin-bottom: 6px;
}
</style>
