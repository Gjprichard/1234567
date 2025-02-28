from datetime import datetime

def format_price(price: float) -> str:
    """格式化价格显示"""
    return f"${price:,.2f}"

def format_volume(volume: float) -> str:
    """格式化成交量显示"""
    if volume >= 1_000_000_000:
        return f"${volume/1_000_000_000:.2f}B"
    elif volume >= 1_000_000:
        return f"${volume/1_000_000:.2f}M"
    else:
        return f"${volume:,.0f}"

def format_change(change: float) -> str:
    """格式化价格/成交量变化率显示"""
    if change is None:
        return "0.00%"
    return f"{change:+.2f}%"

def format_percentage(value: float) -> str:
    """格式化百分比显示"""
    if value is None:
        return "0.00%"
    return f"{value:.2f}%"

def format_timestamp(ts) -> str:
    """格式化时间戳"""
    try:
        if isinstance(ts, (int, float)):
            # 如果是秒级时间戳
            dt = datetime.fromtimestamp(ts)
            return dt.strftime('%Y-%m-%d %H:%M:%S')
        elif isinstance(ts, datetime):
            return ts.strftime('%Y-%m-%d %H:%M:%S')
        else:
            return str(ts)
    except Exception:
        return '-' 