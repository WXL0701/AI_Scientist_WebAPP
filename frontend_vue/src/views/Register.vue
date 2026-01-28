<template>
  <div class="auth-container">
    <el-card class="auth-card">
      <template #header>
        <div class="card-header">
          <h2>AI Scientist Register</h2>
        </div>
      </template>
      <el-form :model="form" :rules="rules" ref="formRef" label-position="top">
        <el-form-item label="Username" prop="username">
          <el-input v-model="form.username" placeholder="Enter username" />
        </el-form-item>
        <el-form-item label="Password" prop="password">
          <el-input v-model="form.password" type="password" placeholder="Enter password" show-password />
        </el-form-item>
        <el-form-item label="Confirm Password" prop="confirmPassword">
          <el-input v-model="form.confirmPassword" type="password" placeholder="Confirm password" show-password @keyup.enter="handleRegister" />
        </el-form-item>
        <el-form-item>
          <el-button type="primary" :loading="loading" @click="handleRegister" class="w-100">Register</el-button>
        </el-form-item>
      </el-form>
      <div class="auth-footer">
        <router-link to="/login">Already have an account? Login</router-link>
      </div>
    </el-card>
  </div>
</template>

<script setup lang="ts">
import { ref, reactive } from 'vue'
import { useRouter } from 'vue-router'
import { ElMessage, type FormInstance } from 'element-plus'
import client from '../api/client'
import { useAuthStore } from '../stores/auth'

const router = useRouter()
const authStore = useAuthStore()
const formRef = ref<FormInstance>()
const loading = ref(false)

const form = reactive({
  username: '',
  password: '',
  confirmPassword: ''
})

const validatePass2 = (_rule: any, value: any, callback: any) => {
  if (value === '') {
    callback(new Error('Please input the password again'))
  } else if (value !== form.password) {
    callback(new Error("Two inputs don't match!"))
  } else {
    callback()
  }
}

const rules = {
  username: [
    { required: true, message: 'Please input username', trigger: 'blur' }
  ],
  password: [{ required: true, message: 'Please input password', trigger: 'blur' }],
  confirmPassword: [{ validator: validatePass2, trigger: 'blur' }]
}

const handleRegister = async () => {
  if (!formRef.value) return
  await formRef.value.validate(async (valid) => {
    if (valid) {
      loading.value = true
      try {
        const res = await client.post('/auth/register', {
          username: form.username,
          password: form.password
        })
        authStore.login(res.data.access_token, res.data.user)
        ElMessage.success('Registration successful')
        router.push('/')
      } catch (error: any) {
        ElMessage.error(error.response?.data?.detail || 'Registration failed')
      } finally {
        loading.value = false
      }
    }
  })
}
</script>

<style scoped>
.auth-container {
  display: flex;
  justify-content: center;
  align-items: center;
  height: 100vh;
  background-color: #f0f2f5;
}
.auth-card {
  width: 400px;
}
.card-header h2 {
  margin: 0;
  text-align: center;
  color: #409EFF;
}
.w-100 {
  width: 100%;
}
.auth-footer {
  text-align: center;
  margin-top: 10px;
}
</style>
