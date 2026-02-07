"""
本地 Agent Schema 规范

所有本地 Agent 必须遵循以下接口规范。
"""


async def main(self, stock_code: str) -> bool:
    """
    Agent 主函数（必须是异步函数）

    Args:
        stock_code: 股票代码，如 "600519" 或 "000001"

    Returns:
        bool: True 表示建议买入 (indicating)，False 表示不买

    说明:
        - Indicating 定义：当返回 True 时，表示买入信号
        - 该信号会在当天收盘前执行交易
        - 卖出规则在 simulator 中单独定义
        - Agent 可以使用 print() 输出日志，会通过 streaming 返回给前端

    Example:
        >>> async def main(stock_code: str) -> bool:
        ...     # 获取股票数据
        ...     # 分析数据
        ...     # 返回买入决策
        ...     return True  # 建议买入
    """
