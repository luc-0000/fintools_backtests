from dataclasses import dataclass
from datetime import datetime
from typing import List


@dataclass
class NewsItem:
    """新闻项目数据结构"""
    title: str
    content: str
    source: str
    publish_time: datetime
    url: str
    urgency: str  # high, medium, low
    relevance_score: float


def deduplicate_news(news_items: List[NewsItem]) -> List[NewsItem]:
    """去重新闻"""
    seen_titles = set()
    unique_news = []

    for item in news_items:
        # 简单的标题去重
        title_key = item.title.lower().strip()
        if title_key not in seen_titles and len(title_key) > 10:
            seen_titles.add(title_key)
            unique_news.append(item)

    return unique_news

def format_news_report(news_items: List[NewsItem], ticker: str) -> str:
    """格式化新闻报告"""
    if not news_items:
        return f"未获取到{ticker}的实时新闻数据。"

    report = f"# {ticker} 实时新闻分析报告\n\n"
    report += f"📅 生成时间: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}\n"
    report += f"📊 新闻总数: {len(news_items)}条\n\n"

    for news in news_items:  # 最多显示5条
        report += f"### {news.title}\n"
        report += f"**来源**: {news.source} | **时间**: {news.publish_time}\n"
        report += f"{news.content}\n\n"

    # 添加时效性说明
    latest_news = max(news_items, key=lambda x: x.publish_time)
    time_diff = datetime.now() - latest_news.publish_time

    report += f"\n## ⏰ 数据时效性\n"
    report += f"最新新闻发布于: {time_diff.total_seconds() / 60:.0f}分钟前\n"

    if time_diff.total_seconds() < 1800:  # 30分钟内
        report += "🟢 数据时效性: 优秀 (30分钟内)\n"
    elif time_diff.total_seconds() < 3600:  # 1小时内
        report += "🟡 数据时效性: 良好 (1小时内)\n"
    else:
        report += "🔴 数据时效性: 一般 (超过1小时)\n"

    return report