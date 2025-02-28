"""数据收集模块"""
import requests
import tweepy
import pandas as pd
from typing import Dict, List, Optional
import logging
from datetime import datetime, timedelta
from bs4 import BeautifulSoup
import json
from textblob import TextBlob

logger = logging.getLogger(__name__)

class DataCollector:
    """数据收集器"""
    def __init__(self, config: Dict):
        self.config = config
        self.twitter_api = self._init_twitter_api()
        self.news_sources = self._init_news_sources()
        
    def _init_twitter_api(self) -> Optional[tweepy.API]:
        """初始化Twitter API"""
        try:
            auth = tweepy.OAuthHandler(
                self.config['twitter']['consumer_key'],
                self.config['twitter']['consumer_secret']
            )
            auth.set_access_token(
                self.config['twitter']['access_token'],
                self.config['twitter']['access_token_secret']
            )
            return tweepy.API(auth)
            
        except Exception as e:
            logger.error(f"初始化Twitter API失败: {str(e)}")
            return None
    
    def _init_news_sources(self) -> List[Dict]:
        """初始化新闻源"""
        return [
            {
                'name': 'CoinDesk',
                'url': 'https://www.coindesk.com/feed',
                'type': 'rss'
            },
            {
                'name': 'CoinTelegraph',
                'url': 'https://cointelegraph.com/rss',
                'type': 'rss'
            }
            # ... 添加更多新闻源
        ]
    
    def collect_twitter_data(self, accounts: List[str]) -> List[Dict]:
        """收集Twitter数据"""
        try:
            if not self.twitter_api:
                logger.warning("Twitter API未初始化，使用模拟数据")
                return self._get_mock_twitter_data()
            
            tweets = []
            for account in accounts:
                try:
                    user_tweets = self.twitter_api.user_timeline(
                        screen_name=account,
                        count=100,
                        tweet_mode="extended"
                    )
                    for tweet in user_tweets:
                        tweets.append({
                            'id': tweet.id,
                            'user': account,
                            'text': tweet.full_text,
                            'created_at': tweet.created_at,
                            'retweets': tweet.retweet_count,
                            'likes': tweet.favorite_count
                        })
                except Exception as e:
                    logger.error(f"获取用户 {account} 的推文失败: {str(e)}")
                    continue
                
            return tweets
            
        except Exception as e:
            logger.error(f"收集Twitter数据失败: {str(e)}")
            return self._get_mock_twitter_data()
    
    def _get_mock_twitter_data(self) -> List[Dict]:
        """获取模拟Twitter数据"""
        return [
            {
                'id': 1,
                'user': 'elonmusk',
                'text': 'Crypto is the future of currency',
                'created_at': datetime.now(),
                'retweets': 5000,
                'likes': 20000
            },
            {
                'id': 2,
                'user': 'cz_binance',
                'text': 'BTC looking strong',
                'created_at': datetime.now(),
                'retweets': 3000,
                'likes': 15000
            }
        ]
    
    def collect_news_data(self) -> List[Dict]:
        """收集新闻数据"""
        try:
            news_items = []
            for source in self.news_sources:
                if source['type'] == 'rss':
                    items = self._collect_rss_feed(source['url'])
                else:
                    items = self._collect_web_news(source['url'])
                news_items.extend(items)
            return news_items
            
        except Exception as e:
            logger.error(f"收集新闻数据失败: {str(e)}")
            return []
    
    def _collect_rss_feed(self, url: str) -> List[Dict]:
        """收集RSS源数据"""
        try:
            response = requests.get(url, timeout=10)
            if response.status_code != 200:
                return []
            
            soup = BeautifulSoup(response.content, 'xml')
            items = soup.find_all('item')
            
            news_items = []
            for item in items:
                news_items.append({
                    'title': item.title.text if item.title else '',
                    'description': item.description.text if item.description else '',
                    'link': item.link.text if item.link else '',
                    'published': item.pubDate.text if item.pubDate else '',
                    'source': url
                })
            
            return news_items
            
        except Exception as e:
            logger.error(f"收集RSS数据失败 ({url}): {str(e)}")
            return []

    def collect_economic_data(self) -> Dict:
        """收集经济数据"""
        try:
            # 使用 Alpha Vantage API 获取经济数据
            api_key = self.config['alpha_vantage']['api_key']
            base_url = "https://www.alphavantage.co/query"
            
            # 收集CPI数据
            cpi_params = {
                "function": "CPI",
                "interval": "monthly",
                "apikey": api_key
            }
            cpi_response = requests.get(base_url, params=cpi_params)
            cpi_data = cpi_response.json()
            
            # 收集GDP数据
            gdp_params = {
                "function": "REAL_GDP",
                "interval": "quarterly",
                "apikey": api_key
            }
            gdp_response = requests.get(base_url, params=gdp_params)
            gdp_data = gdp_response.json()
            
            return {
                'cpi': cpi_data,
                'gdp': gdp_data,
                'timestamp': datetime.now().isoformat()
            }
            
        except Exception as e:
            logger.error(f"收集经济数据失败: {str(e)}")
            return {}

    def collect_network_metrics(self) -> Dict:
        """收集区块链网络指标"""
        try:
            # 使用 Blockchain.com API 获取比特币网络数据
            endpoints = {
                'difficulty': 'https://api.blockchain.info/charts/difficulty',
                'hashrate': 'https://api.blockchain.info/charts/hash-rate',
                'transaction_count': 'https://api.blockchain.info/charts/n-transactions'
            }
            
            network_data = {}
            for metric, url in endpoints.items():
                params = {
                    'timespan': '5days',
                    'format': 'json'
                }
                response = requests.get(url, params=params)
                if response.status_code == 200:
                    network_data[metric] = response.json()
            
            return network_data
            
        except Exception as e:
            logger.error(f"收集网络指标失败: {str(e)}")
            return {}

    def _analyze_policy_impact(self, news_data: List[Dict]) -> str:
        """分析政策影响程度"""
        try:
            # 关键词权重
            keyword_weights = {
                'high': ['ban', 'restrict', 'regulate', 'enforce', 'mandate', 'require'],
                'medium': ['review', 'consider', 'propose', 'plan', 'discuss'],
                'low': ['study', 'research', 'monitor', 'observe', 'assess']
            }
            
            # 统计关键词出现次数
            impact_scores = {'high': 0, 'medium': 0, 'low': 0}
            
            for news in news_data:
                text = f"{news['title']} {news['description']}".lower()
                for level, keywords in keyword_weights.items():
                    for keyword in keywords:
                        if keyword in text:
                            impact_scores[level] += 1
            
            # 确定影响程度
            if impact_scores['high'] > 0:
                return 'high'
            elif impact_scores['medium'] > 0:
                return 'medium'
            return 'low'
            
        except Exception as e:
            logger.error(f"分析政策影响失败: {str(e)}")
            return 'medium'
    
    def _calculate_news_sentiment(self, news_data: List[Dict]) -> float:
        """计算新闻情感得分"""
        try:
            if not news_data:
                return 0.0
            
            total_score = 0.0
            total_weight = 0.0
            
            for news in news_data:
                # 使用标题和描述计算情感
                text = f"{news['title']} {news['description']}"
                sentiment = TextBlob(text).sentiment.polarity
                
                # 根据来源和时间计算权重
                source_weight = self._get_source_weight(news['source'])
                time_weight = self._get_time_weight(news['published'])
                weight = source_weight * time_weight
                
                total_score += sentiment * weight
                total_weight += weight
            
            return total_score / total_weight if total_weight > 0 else 0.0
            
        except Exception as e:
            logger.error(f"计算新闻情感得分失败: {str(e)}")
            return 0.0
    
    def _get_source_weight(self, source: str) -> float:
        """获取新闻源权重"""
        source_weights = {
            'reuters.com': 1.0,
            'bloomberg.com': 1.0,
            'coindesk.com': 0.8,
            'cointelegraph.com': 0.7
        }
        return source_weights.get(source, 0.5)
    
    def _get_time_weight(self, published_time: str) -> float:
        """获取时间权重"""
        try:
            published = datetime.fromisoformat(published_time.replace('Z', '+00:00'))
            hours_ago = (datetime.now(published.tzinfo) - published).total_seconds() / 3600
            
            if hours_ago <= 6:
                return 1.0
            elif hours_ago <= 12:
                return 0.8
            elif hours_ago <= 24:
                return 0.6
            elif hours_ago <= 48:
                return 0.4
            else:
                return 0.2
                
        except Exception as e:
            logger.error(f"计算时间权重失败: {str(e)}")
            return 0.5
    
    def _calculate_engagement_rates(self, social_data: List[Dict]) -> List[float]:
        """计算社交媒体参与度"""
        try:
            engagement_rates = []
            for post in social_data:
                # 计算基础参与度
                engagement = (
                    post.get('retweets', 0) * 2 +  # 转发权重更高
                    post.get('likes', 0)
                )
                
                # 获取账号粉丝数（应该从缓存获取）
                follower_count = self._get_follower_count(post['user'])
                
                # 计算参与率
                if follower_count > 0:
                    rate = engagement / follower_count
                    engagement_rates.append(min(rate * 1000, 1.0))  # 归一化到 [0, 1]
                else:
                    engagement_rates.append(0.0)
                    
            return engagement_rates
            
        except Exception as e:
            logger.error(f"计算参与度失败: {str(e)}")
            return []
    
    def _calculate_influence_scores(self, social_data: List[Dict]) -> List[float]:
        """计算社交媒体影响力得分"""
        try:
            # 影响力基准值
            influence_base = {
                'elonmusk': 1.0,
                'cz_binance': 0.9,
                'saylor': 0.8
            }
            
            influence_scores = []
            for post in social_data:
                user = post['user']
                base_score = influence_base.get(user, 0.5)
                
                # 根据互动情况调整得分
                engagement_boost = min(
                    (post.get('retweets', 0) + post.get('likes', 0)) / 10000,
                    0.5
                )
                
                final_score = min(base_score + engagement_boost, 1.0)
                influence_scores.append(final_score)
            
            return influence_scores
            
        except Exception as e:
            logger.error(f"计算影响力得分失败: {str(e)}")
            return []
    
    def _calculate_metric_change(self, values: List[float]) -> float:
        """计算指标变化率"""
        try:
            if not values or len(values) < 2:
                return 0.0
            
            # 计算变化率
            current = values[-1]
            previous = values[-2]
            
            if previous == 0:
                return 0.0
                
            change = (current - previous) / previous * 100
            return change
            
        except Exception as e:
            logger.error(f"计算指标变化率失败: {str(e)}")
            return 0.0 