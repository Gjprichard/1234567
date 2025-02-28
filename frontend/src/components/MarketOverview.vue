<template>
  <div class="market-overview">
    <el-row :gutter="20">
      <el-col :span="8" v-for="metric in metrics" :key="metric.label">
        <el-card class="metric-card">
          <div class="metric-value" :class="getValueClass(metric)">
            {{ metric.value }}
          </div>
          <div class="metric-label">{{ metric.label }}</div>
          <div class="metric-change" v-if="metric.change">
            {{ metric.change }}
          </div>
        </el-card>
      </el-col>
    </el-row>
  </div>
</template>

<script>
export default {
  name: 'MarketOverview',
  props: {
    data: {
      type: Object,
      required: true
    }
  },
  computed: {
    metrics() {
      const { last, price_change_15m, volume_change_15m } = this.data;
      return [
        {
          label: '当前价格',
          value: this.formatPrice(last),
          change: this.formatChange(price_change_15m)
        },
        {
          label: '15分钟涨跌',
          value: this.formatChange(price_change_15m)
        },
        {
          label: '成交量变化',
          value: this.formatChange(volume_change_15m)
        }
      ];
    }
  },
  methods: {
    formatPrice(price) {
      return `$${price.toFixed(4)}`;
    },
    formatChange(change) {
      return `${change >= 0 ? '+' : ''}${change.toFixed(2)}%`;
    },
    getValueClass(metric) {
      if (!metric.change) return '';
      return parseFloat(metric.change) >= 0 ? 'positive' : 'negative';
    }
  }
};
</script>

<style scoped>
.market-overview {
  padding: 20px;
}

.metric-card {
  text-align: center;
  padding: 20px;
  background: #1e1e1e;
  border: 1px solid #333;
}

.metric-value {
  font-size: 24px;
  font-weight: bold;
  margin-bottom: 10px;
}

.metric-value.positive {
  color: #00c853;
}

.metric-value.negative {
  color: #ff5252;
}

.metric-label {
  color: #888;
  font-size: 14px;
}

.metric-change {
  margin-top: 5px;
  font-size: 12px;
}
</style> 