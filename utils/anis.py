"""
ANSI 转义序列模块，用于控制台输出彩色文本
"""

# 基础颜色
RED = "\033[91m"     # 红色 - 用于错误和警告
GREEN = "\033[92m"   # 绿色 - 用于成功信息
YELLOW = "\033[93m"  # 黄色 - 用于警告和提示
BLUE = "\033[94m"    # 蓝色 - 用于信息和状态
RESET = "\033[0m"    # 重置所有颜色和样式

# 扩展颜色
MAGENTA = "\033[95m"  # 紫色
CYAN = "\033[96m"     # 青色
WHITE = "\033[97m"    # 白色
BLACK = "\033[30m"    # 黑色

# 背景颜色
BG_RED = "\033[41m"     # 红色背景
BG_GREEN = "\033[42m"   # 绿色背景
BG_YELLOW = "\033[43m"  # 黄色背景
BG_BLUE = "\033[44m"    # 蓝色背景

# 文本样式
BOLD = "\033[1m"        # 粗体
UNDERLINE = "\033[4m"   # 下划线
ITALIC = "\033[3m"      # 斜体
BLINK = "\033[5m"       # 闪烁

def colorize(text, color):
    """
    为文本添加颜色
    
    参数:
        text (str): 要着色的文本
        color (str): ANSI颜色代码
        
    返回:
        str: 着色后的文本
    """
    return f"{color}{text}{RESET}"