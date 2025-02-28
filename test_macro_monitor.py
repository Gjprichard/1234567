"""宏观监控系统测试"""
import unittest
from datetime import datetime, timedelta
import json
from macro_monitor import MacroMonitor, FactorType, Factor
from database import MacroDatabase
import os
import tempfile

class TestMacroMonitor(unittest.TestCase):
    def setUp(self):
        # 使用临时文件作为测试数据库
        self.temp_db = tempfile.NamedTemporaryFile(delete=False)
        self.monitor = MacroMonitor(db_path=self.temp_db.name)
    
    def tearDown(self):
        # 清理临时文件
        os.unlink(self.temp_db.name)
    
    def test_factor_initialization(self):
        """测试因子初始化"""
        factors = self.monitor.factors
        
        # 检查必要的因子是否存在
        self.assertIn('fed_policy', factors)
        self.assertIn('market_sentiment', factors)
        self.assertIn('social_sentiment', factors)
        
        # 检查权重总和是否为1
        total_weight = sum(f.weight for f in factors.values())
        self.assertAlmostEqual(total_weight, 1.0, places=2)
        
        # 检查因子属性
        for factor in factors.values():
            self.assertIsInstance(factor, Factor)
            self.assertIsInstance(factor.type, FactorType)
            self.assertTrue(0 <= factor.weight <= 1)
    
    def test_score_calculation(self):
        """测试评分计算"""
        # 测试政策评分
        policy_data = {
            'policy_type': 'monetary',
            'impact_level': 'high',
            'sentiment': 0.5
        }
        policy_score = self.monitor._calculate_policy_score(policy_data)
        self.assertTrue(-1 <= policy_score <= 1)
        
        # 测试市场评分
        market_data = {
            'volume_change': 50,
            'price_change': 5,
            'volatility': 20
        }
        market_score = self.monitor._calculate_market_score(market_data)
        self.assertTrue(-1 <= market_score <= 1)
        
        # 测试社交媒体评分
        social_data = {
            'sentiment_scores': [0.5, -0.3, 0.8],
            'engagement_rates': [0.1, 0.2, 0.3],
            'influence_scores': [0.8, 0.7, 0.9]
        }
        social_score = self.monitor._calculate_social_score(social_data)
        self.assertTrue(-1 <= social_score <= 1)
    
    def test_data_update(self):
        """测试数据更新"""
        # 模拟因子数据
        test_data = {
            'fed_policy': {
                'policy_type': 'monetary',
                'impact_level': 'medium',
                'sentiment': 0.2
            },
            'market_sentiment': {
                'volume_change': 30,
                'price_change': 2,
                'volatility': 15
            }
        }
        
        # 更新数据
        for factor_id, data in test_data.items():
            success = self.monitor.update_factor_data(factor_id, data)
            self.assertTrue(success)
        
        # 检查数据是否正确保存
        analysis = self.monitor.get_factor_analysis()
        self.assertIn('fed_policy', analysis)
        self.assertIn('market_sentiment', analysis)
    
    def test_score_history(self):
        """测试评分历史"""
        # 生成测试数据
        test_scores = []
        base_time = datetime.now()
        
        for i in range(5):
            score_time = base_time - timedelta(hours=i)
            test_scores.append({
                'total_score': 0.5 + i * 0.1,
                'factor_scores': {
                    'fed_policy': 0.6 + i * 0.1,
                    'market_sentiment': 0.4 + i * 0.1
                },
                'timestamp': score_time.isoformat()
            })
        
        # 保存测试数据
        for score_data in test_scores:
            self.monitor.db.save_score_history(
                score_data['total_score'],
                score_data['factor_scores']
            )
        
        # 获取历史数据
        history = self.monitor.db.get_score_history(days=1)
        self.assertEqual(len(history), 5)
        
        # 检查数据格式
        for record in history:
            self.assertIn('total_score', record)
            self.assertIn('factor_scores', record)
            self.assertIn('timestamp', record)
    
    def test_error_handling(self):
        """测试错误处理"""
        # 测试无效因子ID
        success = self.monitor.update_factor_data('invalid_factor', {})
        self.assertFalse(success)
        
        # 测试无效数据格式
        success = self.monitor.update_factor_data('fed_policy', None)
        self.assertFalse(success)
        
        # 测试数据库错误
        self.monitor.db = None
        analysis = self.monitor.get_factor_analysis()
        self.assertEqual(analysis, {})

if __name__ == '__main__':
    unittest.main() 