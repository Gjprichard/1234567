import unittest
from datetime import datetime, timedelta
from visualizations import create_habit_heatmap, create_streak_chart, create_completion_rate_chart

class TestVisualizations(unittest.TestCase):
    def setUp(self):
        # 创建测试数据
        # 模拟habit_logs格式: [(id, habit_id, date_str), ...]
        today = datetime.now().date()
        
        # 连续3天的数据
        self.consecutive_logs = [
            (1, 1, (today - timedelta(days=2)).strftime('%Y-%m-%d')),
            (2, 1, (today - timedelta(days=1)).strftime('%Y-%m-%d')),
            (3, 1, today.strftime('%Y-%m-%d'))
        ]
        
        # 空数据
        self.empty_logs = []
        
        # 间断的数据
        self.scattered_logs = [
            (1, 1, (today - timedelta(days=10)).strftime('%Y-%m-%d')),
            (2, 1, (today - timedelta(days=5)).strftime('%Y-%m-%d')),
            (3, 1, today.strftime('%Y-%m-%d'))
        ]

    def test_heatmap_creation(self):
        # 测试热力图创建
        fig = create_habit_heatmap(self.consecutive_logs)
        self.assertIsNotNone(fig)
        
        # 测试空数据
        fig = create_habit_heatmap(self.empty_logs)
        self.assertIsNotNone(fig)

    def test_streak_chart(self):
        # 测试连续数据
        fig = create_streak_chart(self.consecutive_logs)
        self.assertIsNotNone(fig)
        
        # 测试空数据
        fig = create_streak_chart(self.empty_logs)
        self.assertIsNotNone(fig)
        
        # 测试间断数据
        fig = create_streak_chart(self.scattered_logs)
        self.assertIsNotNone(fig)

    def test_completion_rate_chart(self):
        # 测试连续数据
        fig = create_completion_rate_chart(self.consecutive_logs)
        self.assertIsNotNone(fig)
        
        # 测试空数据
        fig = create_completion_rate_chart(self.empty_logs)
        self.assertIsNotNone(fig)
        
        # 测试间断数据
        fig = create_completion_rate_chart(self.scattered_logs)
        self.assertIsNotNone(fig)

if __name__ == '__main__':
    unittest.main() 