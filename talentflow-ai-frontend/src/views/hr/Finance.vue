<template>
  <div class="finance-container">
    <!-- 资金概览 -->
    <el-row :gutter="20" class="mb-4">
      <el-col :span="8">
        <el-card shadow="hover" class="balance-card">
          <p class="label">当前账户余额</p>
          <p class="amount">¥ 12,450.00</p>
          <el-button type="primary" size="small" class="mt-2">充值</el-button>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="balance-card">
          <p class="label">本月总支出</p>
          <p class="amount">¥ 3,200.00</p>
        </el-card>
      </el-col>
      <el-col :span="8">
        <el-card shadow="hover" class="balance-card">
          <p class="label">待结算金额</p>
          <p class="amount">¥ 500.00</p>
        </el-card>
      </el-col>
    </el-row>

    <!-- 交易流水 -->
    <el-card header="近期交易流水">
      <el-table :data="records" stripe>
        <el-table-column prop="orderId" label="订单号" width="180" />
        <el-table-column prop="taskName" label="关联任务" />
        <el-table-column prop="type" label="类型" width="100">
          <template #default="scope">
            <span :class="scope.row.type === '支出' ? 'text-red' : 'text-green'">
              {{ scope.row.type }}
            </span>
          </template>
        </el-table-column>
        <el-table-column prop="amount" label="金额" width="100">
          <template #default="scope">¥{{ scope.row.amount }}</template>
        </el-table-column>
        <el-table-column prop="time" label="时间" width="160" />
      </el-table>
    </el-card>
  </div>
</template>

<script setup>
const records = [
  { orderId: '20260503001', taskName: 'Logo 设计 VI 规范', type: '支出', amount: 1200, time: '2026-05-03 10:00' },
  { orderId: '20260501005', taskName: '账户充值', type: '收入', amount: 5000, time: '2026-05-01 09:30' },
  { orderId: '20260428009', taskName: '前端开发任务', type: '支出', amount: 2000, time: '2026-04-28 14:20' },
]
</script>

<style scoped>
.mb-4 { margin-bottom: 20px; }
.mt-2 { margin-top: 10px; }

.balance-card { text-align: center; }
.amount { font-size: 28px; font-weight: bold; color: #303133; margin: 10px 0; }
.label { color: #606266; margin: 0; }

.text-red { color: #F56C6C; }
.text-green { color: #67C23A; }
</style>