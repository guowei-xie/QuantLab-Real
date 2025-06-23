# QuantLab-Real

QuantLab-Real 是一个基于迅投 xtQuant 的实盘量化交易系统，专为 A 股市场设计，提供自动选股、行情订阅、信号生成和交易执行的完整解决方案。

## 功能特性

- **实时行情订阅**：支持分钟级、日线级行情数据订阅和处理
- **策略实现**：内置涨停打板策略，支持自定义交易策略
- **自动交易**：根据策略信号自动执行买入卖出操作
- **风险控制**：支持持仓限制、单日交易限制等风险控制措施
- **数据管理**：历史数据下载与管理，支持增量更新

## 安装指南

### 系统要求

- Windows 操作系统
- Python 3.8+
- 迅投 QMT 交易终端

### 安装步骤

1. 克隆项目代码

```bash
git clone https://github.com/yourusername/QuantLab-Real.git
cd QuantLab-Real
```

2. 安装依赖包

```bash
pip install -r requirements.txt
```

3. 配置交易账户
编辑 `config.ini` 文件，填入您的账户信息和交易参数。

## 使用方法

1. 配置交易参数

编辑 `config.ini` 文件，设置账户信息和交易参数：

```ini
[ACCOUNT]
ACCOUNT_ID = 您的账户ID
MINI_QMT_PATH = 迅投QMT交易终端路径

[POSTION]
TOTAL_POSITION_VALUE = 100000 # 总持仓市值限制(元)
MAX_BUY_VALUE_PER_DAY = 50000 # 单日总买入市值限制(元)
MAX_BUY_VALUE_PER_STOCK = 10000 # 单股最大买入市值限制(元)
```

2. 运行主程序

```bash
python main.py
```

系统将自动下载历史数据、创建股票池、订阅行情并执行交易策略。

## 主要模块

### broker - 交易执行模块

- `broker.py`: 交易执行核心，负责下单、撤单、查询等操作
- `data.py`: 行情数据获取与处理
- `trader.py`: 交易接口封装

### laboratory - 选股与信号生成

- `pool.py`: 股票池管理与筛选
- `graph.py`: 技术分析图表
- `signal.py`: 交易信号生成
- `utils.py`: 辅助工具函数

### strategys - 策略实现

- `board_hitting.py`: 板块打板策略实现

### utils - 工具函数

- `logger.py`: 日志管理
- `anis.py`: 终端彩色输出
- `util.py`: 通用工具函数

## 开发自定义策略

要开发自定义策略，可以参考 `strategys/board_hitting.py` 的实现方式，创建新的策略类并实现以下核心方法：

1. `__init__`: 初始化策略参数
2. `set_buy_stock_pool`: 创建买入股票池
3. `set_sell_stock_pool`: 创建卖出股票池
4. `buy_signal`: 生成买入信号
5. `sell_signal`: 生成卖出信号
6. `run`: 策略主循环

## 注意事项

- 本系统仅供学习研究使用，不构成投资建议
- 策略仅供学习参考，请勿直接实盘运行，可能会造成不可追回的损失