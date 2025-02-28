<template>
  <div class="market-table">
    <el-table
      :data="tableData"
      style="width: 100%"
      :row-class-name="getRowClass"
      height="400"
    >
      <el-table-column prop="symbol" label="交易对" width="120" />
      <el-table-column prop="price" label="价格" width="150">
        <template #default="scope">
          {{ formatPrice(scope.row.last) }}
        </template>
      </el-table-column>
      <el-table-column prop="price_change_15m" label="15分钟涨跌" width="150">
        <template #default="scope">
          <span :class="getChangeClass(scope.row.price_change_15m)">
            {{ formatChange(scope.row.price_change_15m) }}
          </span>
        </template>
      </el-table-column>
      <el-table-column prop="volume_change_15m" label="成交量变化">
        <template #default="scope">
          <span :class="getChangeClass(scope.row.volume_change_15m)">
            {{ formatChange(scope.row.volume_change_15m) }}
          </span>
        </template>
      </el-table-column>
    </el-table>
  </div>
</template>

<script>
export default {
  name: 'MarketTable',
  props: {
    data: {
      type: Array,
      required: true
    }
  },
  computed: {
    tableData() {
      return this.data;
    }
  },
  methods: {
    formatPrice(price) {
      return `$${price.toFixed(4)}`;
    },
    formatChange(change) {
      return `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`;
    },
    getChangeClass(value) {
      return value >= 0 ? 'positive-change' : 'negative-change';
    },
    getRowClass({ row }) {
      return row.price_change_15m >= 3 || row.volume_change_15m >= 50 
        ? 'warning-row' 
        : '';
    }
  }
};
</script>

<style>
.market-table {
  margin: 20px 0;
}

.positive-change {
  color: #00c853;
}

.negative-change {
  color: #ff5252;
}

.warning-row {
  background-color: rgba(255, 82, 82, 0.1) !important;
}

.el-table {
  background-color: #1e1e1e !important;
  color: #fff !important;
}

.el-table th {
  background-color: #2c2c2c !important;
  color: #fff !important;
}

.el-table td, .el-table th.is-leaf {
  border-bottom: 1px solid #333 !important;
}
</style> 