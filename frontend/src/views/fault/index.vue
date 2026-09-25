<template>
  <section class="page" data-module="fault">
    <header class="page-head">
      <div>
        <h2>故障登记管理</h2>
        <p class="page-desc">维护设备故障，围绕故障编号、发生设备、故障现象、影响范围做登记、筛选与状态流转。</p>
      </div>
      <div class="page-actions">
        <button class="btn primary" type="button" @click="openCreate">登记设备故障</button>
        <button
          class="btn primary"
          type="button"
          :disabled="!selectedIds.length"
          @click="openGradeDialog"
        >
          批量定级（已选 {{ selectedIds.length }} 条）
        </button>
        <button class="btn" type="button" @click="exportRows">导出故障登记清单</button>
      </div>
    </header>

    <div class="stat-row">
      <article v-for="item in stats" :key="item.label" class="stat-card">
        <span class="stat-label">{{ item.label }}</span>
        <strong class="stat-value">{{ item.value }}</strong>
      </article>
    </div>

    <form class="filter-bar" @submit.prevent="reload">
      <label v-for="field in filterFields" :key="field" class="filter-item">
        <span>{{ field }}</span>
        <input v-model="filters[field]" :placeholder="`按${field}检索`" />
      </label>
      <button class="btn" type="submit">查询</button>
      <button class="btn ghost" type="button" @click="resetFilters">重置条件</button>
    </form>

    <div v-if="gradeResult" class="grade-panel">
      <header class="grade-panel-head">
        <strong>批量定级结果</strong>
        <span>定级依据：{{ gradeResult.basis }}</span>
        <button class="link" type="button" @click="gradeResult = null">收起</button>
      </header>
      <p class="grade-summary">{{ gradeResult.message }}</p>
      <table class="data-table">
        <thead>
          <tr>
            <th>故障编号</th>
            <th>发生设备</th>
            <th>定级结果</th>
            <th>处理期限</th>
            <th>说明</th>
          </tr>
        </thead>
        <tbody>
          <tr v-for="item in gradeResult.results" :key="String(item.id)">
            <td>{{ item.故障编号 ?? item.id }}</td>
            <td>{{ item.发生设备 ?? '—' }}</td>
            <td>{{ item.ok ? item.定级结果 : '未定级' }}</td>
            <td>{{ item.ok ? item.处理期限 : '—' }}</td>
            <td>{{ item.message }}</td>
          </tr>
        </tbody>
      </table>
      <div v-if="gradeResult.todos.length" class="grade-block">
        <strong>合并处置待办（同一台设备合并为一条）</strong>
        <ul>
          <li v-for="todo in gradeResult.todos" :key="String(todo.dispose_id)">
            {{ todo.message }}，关联故障：{{ (todo.关联故障 ?? []).join('、') || '—' }}，处理期限：{{ todo.处理期限 || '—' }}
          </li>
        </ul>
      </div>
      <div v-if="gradeResult.suspended.length" class="grade-block suspended">
        <strong>已挂起故障（单独列出，不参与批量定级）</strong>
        <ul>
          <li v-for="item in gradeResult.suspended" :key="String(item.id)">
            {{ item.故障编号 }}（{{ item.发生设备 }}）：{{ item.message }}
          </li>
        </ul>
      </div>
    </div>

    <table class="data-table">
      <thead>
        <tr>
          <th>
            <input
              type="checkbox"
              :checked="allChecked"
              aria-label="全选"
              @change="toggleAll"
            />
          </th>
          <th v-for="column in columns" :key="column">{{ column }}</th>
          <th>可执行动作</th>
        </tr>
      </thead>
      <tbody>
        <tr v-for="row in rows" :key="String(row.id)">
          <td>
            <input
              type="checkbox"
              :checked="selectedIds.includes(Number(row.id))"
              :aria-label="`选择${row.故障编号 ?? row.id}`"
              @change="toggleRow(Number(row.id))"
            />
          </td>
          <td v-for="column in columns" :key="column">{{ row[column] || '—' }}</td>
          <td class="row-actions">
            <button
              v-for="action in actions"
              :key="action"
              class="link"
              type="button"
              @click="runAction(action, row)"
            >
              {{ action }}
            </button>
          </td>
        </tr>
        <tr v-if="!rows.length">
          <td :colspan="columns.length + 2" class="empty-state">暂无故障登记数据，可先登记设备故障</td>
        </tr>
      </tbody>
    </table>

    <footer class="page-foot">
      <span>共 {{ total }} 条故障登记记录</span>
      <span v-if="errorMessage" class="error-text">{{ errorMessage }}</span>
    </footer>

    <div v-if="gradeDialogOpen" class="modal-mask" @click.self="gradeDialogOpen = false">
      <div class="modal-card">
        <h3>批量定级</h3>
        <p class="modal-desc">
          将对已选的 {{ selectedIds.length }} 条故障套用同一份定级依据，同样的现象定出同样的等级。
        </p>
        <label class="modal-field">
          <span>定级依据</span>
          <textarea
            v-model="gradeBasis"
            rows="3"
            placeholder="例如：《电务设备故障定级细则》2026版"
          ></textarea>
        </label>
        <p v-if="gradeError" class="error-text">{{ gradeError }}</p>
        <div class="modal-actions">
          <button class="btn primary" type="button" :disabled="grading" @click="submitGrade">
            {{ grading ? '定级中…' : '确认定级' }}
          </button>
          <button class="btn ghost" type="button" @click="gradeDialogOpen = false">取消</button>
        </div>
      </div>
    </div>
  </section>
</template>

<script setup lang="ts">
import { computed, onMounted, ref } from 'vue'

import { request } from '@/api/client'

type Row = Record<string, string | number | null>

interface GradeItem {
  id: number | string
  ok: boolean
  message: string
  故障编号?: string
  发生设备?: string
  定级结果?: string
  处理期限?: string
}

interface GradeTodo {
  dispose_id: number
  message: string
  关联故障?: string[]
  处理期限?: string
}

interface GradeBatch {
  ok: boolean
  message: string
  basis: string
  results: GradeItem[]
  todos: GradeTodo[]
  suspended: GradeItem[]
}

const ENDPOINT = '/api/fault'
const columns = ["故障编号", "发生设备", "故障现象", "影响范围", "发生时间", "报告人", "恢复时间", "定级结果", "处理期限", "故障状态"]
const actions = ["确认定级", "提交恢复", "挂起故障"]
const statuses = ["待定级", "已定级", "处置中", "已恢复", "已挂起"]
const stats = [{"label": "待定级故障", "value": 0}, {"label": "处置中故障", "value": 0}, {"label": "今日恢复数", "value": 0}]

const rows = ref<Row[]>([])
const total = ref(0)
const errorMessage = ref('')
const filters = ref<Record<string, string>>({})
const filterFields = columns.slice(0, 3)

const selectedIds = ref<number[]>([])
const gradeDialogOpen = ref(false)
const gradeBasis = ref('')
const gradeError = ref('')
const grading = ref(false)
const gradeResult = ref<GradeBatch | null>(null)

const allChecked = computed(() => {
  if (!rows.value.length) {
    return false
  }
  return rows.value.every((row) => selectedIds.value.includes(Number(row.id)))
})

function toggleRow(id: number) {
  selectedIds.value = selectedIds.value.includes(id)
    ? selectedIds.value.filter((item) => item !== id)
    : [...selectedIds.value, id]
}

function toggleAll() {
  selectedIds.value = allChecked.value ? [] : rows.value.map((row) => Number(row.id))
}

function openGradeDialog() {
  gradeError.value = ''
  gradeDialogOpen.value = true
}

async function submitGrade() {
  gradeError.value = ''
  const basis = gradeBasis.value.trim()
  if (!basis) {
    gradeError.value = '定级依据不能为空，请填写统一定级依据'
    return
  }
  grading.value = true
  try {
    const response = await request(`${ENDPOINT}/grade`, {
      method: 'POST',
      body: JSON.stringify({ ids: selectedIds.value, basis }),
    })
    const payload = await response.json()
    if (!response.ok) {
      throw new Error(payload?.detail ?? '批量定级未生效，请稍后重试')
    }
    gradeResult.value = payload as GradeBatch
    gradeDialogOpen.value = false
    selectedIds.value = []
    // 返回列表后定级结果不能变：重新拉取列表，展示后端已保存的定级结果
    await reload()
  } catch (error) {
    gradeError.value = error instanceof Error ? error.message : '批量定级失败'
  } finally {
    grading.value = false
  }
}

function resetFilters() {
  filters.value = {}
  void reload()
}

function exportRows() {
  window.open(`${ENDPOINT}/export`, '_blank')
}

function openCreate() {
  errorMessage.value = '设备故障登记入口尚未接入审批流'
}

async function runAction(action: string, row: Row) {
  errorMessage.value = ''
  try {
    const response = await request(`${ENDPOINT}/${row.id}/actions`, {
      method: 'POST',
      body: JSON.stringify({ action }),
    })
    if (!response.ok) {
      throw new Error('故障登记动作未生效，请稍后重试')
    }
    await reload()
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '故障登记操作失败'
  }
}

async function reload() {
  errorMessage.value = ''
  const query = new URLSearchParams(filters.value as Record<string, string>).toString()
  try {
    const response = await request(`${ENDPOINT}?${query}`)
    if (!response.ok) {
      throw new Error('设备故障列表读取失败')
    }
    const payload = await response.json()
    rows.value = payload.items ?? []
    total.value = payload.total ?? rows.value.length
  } catch (error) {
    errorMessage.value = error instanceof Error ? error.message : '故障登记列表读取失败'
  }
}

onMounted(reload)
</script>

<style scoped>
.grade-panel {
  background: #fff;
  border: 1px solid var(--border);
  border-radius: 8px;
  padding: 12px;
  margin-bottom: 12px;
}
.grade-panel-head {
  display: flex;
  gap: 12px;
  align-items: center;
  margin-bottom: 6px;
}
.grade-summary {
  color: var(--muted);
  font-size: 13px;
  margin: 4px 0 10px;
}
.grade-block {
  margin-top: 10px;
  font-size: 13px;
}
.grade-block ul {
  margin: 6px 0 0;
  padding-left: 18px;
}
.grade-block.suspended {
  color: #b42318;
}
.modal-mask {
  position: fixed;
  inset: 0;
  background: rgba(15, 23, 42, 0.45);
  display: flex;
  align-items: center;
  justify-content: center;
}
.modal-card {
  background: #fff;
  border-radius: 8px;
  padding: 16px 20px;
  width: 420px;
}
.modal-desc {
  color: var(--muted);
  font-size: 13px;
}
.modal-field span {
  display: block;
  font-size: 12px;
  color: var(--muted);
  margin-bottom: 4px;
}
.modal-field textarea {
  width: 100%;
  border: 1px solid var(--border);
  border-radius: 6px;
  padding: 6px 8px;
  font-family: inherit;
}
.modal-actions {
  display: flex;
  gap: 8px;
  margin-top: 12px;
}
</style>
