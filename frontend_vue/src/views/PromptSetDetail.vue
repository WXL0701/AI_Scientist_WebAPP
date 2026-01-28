<template>
  <div v-loading="loading">
    <div class="page-header">
      <div class="header-left">
        <el-button @click="$router.push('/prompts')" :icon="ArrowLeft" circle class="back-btn" />
        <h2>{{ promptSet?.name || 'Loading...' }} <small>(ID: {{ promptSetId }})</small></h2>
      </div>
      <div>
        <el-button type="primary" @click="fetchData">Refresh</el-button>
      </div>
    </div>

    <el-row :gutter="20">
      <!-- Left Column: Versions History -->
      <el-col :span="8">
        <el-card class="box-card">
          <template #header>
            <div class="card-header">
              <span>History Versions</span>
            </div>
          </template>
          <el-table :data="versions" style="width: 100%" height="500" stripe>
            <el-table-column prop="id" label="Ver" width="60" />
            <el-table-column prop="notes" label="Notes" show-overflow-tooltip />
            <el-table-column prop="created_at" label="Date" width="100">
               <template #default="scope">
                 <span style="font-size: 12px">{{ new Date(scope.row.created_at).toLocaleDateString() }}</span>
               </template>
            </el-table-column>
          </el-table>
        </el-card>
      </el-col>

      <!-- Right Column: Create New Version / Editor -->
      <el-col :span="16">
        <el-card class="box-card">
          <template #header>
            <div class="card-header">
              <span>Create New Version</span>
              <el-button type="success" @click="handleCreateVersion" :disabled="!hasChanges">
                Save Version
              </el-button>
            </div>
          </template>
          
          <div class="editor-workspace">
            <el-form label-position="top">
              <el-form-item label="Version Notes">
                <el-input v-model="newVersionNotes" placeholder="e.g. Optimized Scientist prompt for stability" />
              </el-form-item>
            </el-form>

            <el-divider content-position="left">Agent Configuration</el-divider>
            
            <div class="agent-grid">
              <el-button 
                v-for="(_, filename) in baselinePrompts" 
                :key="filename"
                class="agent-btn"
                :type="isModified(filename) ? 'warning' : 'primary'"
                plain
                @click="openEditor(filename)"
              >
                {{ formatAgentName(filename) }}
                <el-icon v-if="isModified(filename)" class="el-icon--right"><Edit /></el-icon>
              </el-button>
            </div>

            <div v-if="hasChanges" class="changes-summary">
              <p>Modified Agents: {{ modifiedAgents.join(', ') }}</p>
            </div>
          </div>
        </el-card>
      </el-col>
    </el-row>

    <!-- Independent Prompt Editor Dialog -->
    <el-dialog
      v-model="editorVisible"
      :title="`Edit Prompt: ${formatAgentName(currentEditFile)}`"
      width="70%"
      top="5vh"
      destroy-on-close
    >
      <div class="editor-container">
        <el-input
          v-model="currentEditContent"
          type="textarea"
          :rows="20"
          placeholder="Enter prompt content here..."
          class="prompt-textarea"
        />
      </div>
      <template #footer>
        <span class="dialog-footer">
          <el-button @click="editorVisible = false">Cancel</el-button>
          <el-button type="primary" @click="savePrompt">Confirm Changes</el-button>
        </span>
      </template>
    </el-dialog>
  </div>
</template>

<script setup lang="ts">
import { ref, computed, onMounted } from 'vue'
import { useRoute } from 'vue-router'
import { ElMessage } from 'element-plus'
import { ArrowLeft, Edit } from '@element-plus/icons-vue'
import client from '../api/client'

const route = useRoute()
const promptSetId = parseInt(route.params.id as string)

const loading = ref(false)
const promptSet = ref<any>(null)
const versions = ref<any[]>([])
const baselinePrompts = ref<Record<string, string>>({})

// Editor State
const newVersionNotes = ref('')
const draftPayload = ref<Record<string, string>>({}) // Stores modified prompts
const editorVisible = ref(false)
const currentEditFile = ref('')
const currentEditContent = ref('')

// Computed
const hasChanges = computed(() => Object.keys(draftPayload.value).length > 0)
const modifiedAgents = computed(() => Object.keys(draftPayload.value).map(f => formatAgentName(f)))

// Methods
const formatAgentName = (filename: string) => {
  return filename.replace('system_', '').replace('.py', '').toUpperCase()
}

const isModified = (filename: string) => {
  return !!draftPayload.value[filename]
}

const fetchData = async () => {
  loading.value = true
  try {
    // 1. Fetch Prompt Set Details (List all and find)
    const setsRes = await client.get('/promptsets')
    promptSet.value = setsRes.data.find((s: any) => s.id === promptSetId)
    
    // 2. Fetch Versions
    const verRes = await client.get(`/promptsets/${promptSetId}/versions`)
    versions.value = verRes.data.sort((a: any, b: any) => b.id - a.id) // Descending

    // 3. Fetch Baseline Prompts (Agent List)
    const filesRes = await client.get('/promptfiles')
    baselinePrompts.value = filesRes.data.baseline

  } catch (error) {
    ElMessage.error('Failed to fetch data')
  } finally {
    loading.value = false
  }
}

const openEditor = (filename: string) => {
  currentEditFile.value = filename
  // Load draft if exists, otherwise load baseline
  currentEditContent.value = draftPayload.value[filename] || baselinePrompts.value[filename] || ''
  editorVisible.value = true
}

const savePrompt = () => {
  // Save to draft
  draftPayload.value[currentEditFile.value] = currentEditContent.value
  editorVisible.value = false
  ElMessage.success(`Updated ${formatAgentName(currentEditFile.value)} prompt`)
}

const handleCreateVersion = async () => {
  if (!newVersionNotes.value) {
    ElMessage.warning('Please add some notes for this version')
    return
  }
  
  try {
    // Send ONLY the overrides (draftPayload)
    // The backend merges these with baseline.
    await client.post(`/promptsets/${promptSetId}/versions`, {
      notes: newVersionNotes.value,
      payload: draftPayload.value
    })
    
    ElMessage.success('New version created successfully')
    
    // Reset form
    newVersionNotes.value = ''
    draftPayload.value = {}
    
    // Refresh list
    fetchData()
  } catch (error) {
    ElMessage.error('Failed to create version')
  }
}

onMounted(() => {
  fetchData()
})
</script>

<style scoped>
.page-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
  margin-bottom: 20px;
}
.header-left {
  display: flex;
  align-items: center;
  gap: 15px;
}
.back-btn {
  margin-right: 10px;
}
.card-header {
  display: flex;
  justify-content: space-between;
  align-items: center;
}
.agent-grid {
  display: grid;
  grid-template-columns: repeat(auto-fill, minmax(150px, 1fr));
  gap: 15px;
  margin-top: 20px;
  margin-bottom: 20px;
}
.agent-btn {
  width: 100%;
  height: 50px;
  justify-content: space-between;
}
.changes-summary {
  margin-top: 20px;
  color: #e6a23c;
  font-size: 14px;
}
.editor-container {
  /* Ensure textarea takes good height */
}
.prompt-textarea :deep(.el-textarea__inner) {
  font-family: 'Consolas', 'Monaco', monospace;
  font-size: 14px;
  line-height: 1.5;
}
</style>
