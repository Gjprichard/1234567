<template>
  <div class="home">
    <h1>加密货币市场监控</h1>
    
    <market-overview :data="currentMarketData" />
    
    <div class="chart-section">
      <el-select v-model="selectedSymbol" placeholder="选择交易对">
        <el-option
          v-for="item in symbols"
          :key="item"
          :label="item"
          :value="item"
        />
      </el-select>
      
      <candlestick-chart
        v-if="selectedSymbol"
        :data="chartData"
      />
    </div>
    
    <market-table :data="marketData" />
  </div>
</template>

<script>
import MarketOverview from '@/components/MarketOverview.vue';
import CandlestickChart from '@/components/CandlestickChart.vue';
import MarketTable from '@/components/MarketTable.vue';
import { mapState, mapActions } from 'vuex';

export default {
  name: 'Home',
  components: {
    MarketOverview,
    CandlestickChart,
    MarketTable
  },
  data() {
    return {
      selectedSymbol: null
    };
  },
  computed: {
    ...mapState({
      marketData: state => state.market.marketData,
      chartData: state => state.market.chartData
    }),
    currentMarketData() {
      return this.marketData[0] || {};
    },
    symbols() {
      return this.marketData.map(item => item.symbol);
    }
  },
  methods: {
    ...mapActions(['fetchMarketData', 'fetchChartData'])
  },
  watch: {
    selectedSymbol(newVal) {
      if (newVal) {
        this.fetchChartData(newVal);
      }
    }
  },
  created() {
    this.fetchMarketData();
    setInterval(() => {
      this.fetchMarketData();
    }, 60000);
  }
};
</script>

<style scoped>
.home {
  padding: 20px;
  max-width: 1200px;
  margin: 0 auto;
}

h1 {
  text-align: center;
  color: #fff;
  margin-bottom: 30px;
}

.chart-section {
  margin: 20px 0;
}

.el-select {
  margin-bottom: 20px;
}
</style> 