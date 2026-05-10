# Data Pipeline V2 Spec

## 概述

数据管道增强：质量校验、增量同步状态机、多数据源容错、数据血缘追踪。

## 数据质量校验

### QualityReport
```python
@dataclass
class QualityCheck:
    name: str
    passed: bool
    message: str
    affected_rows: int
    details: list[dict]     # 具体异常行

@dataclass
class QualityReport:
    entity: str             # "bond_daily" | "stock_daily"
    check_date: str
    total_rows: int
    checks: list[QualityCheck]
    overall_score: float    # 0.0 ~ 1.0

    @property
    def is_acceptable(self) -> bool:
        return self.overall_score >= 0.8
```

### 校验规则

| 规则 | 检查内容 | 严重程度 |
|------|----------|----------|
| price_range | 价格在 [50, 500] 范围内 | warning |
| ohlc_consistency | high >= max(open, close), low <= min(open, close) | error |
| volume_non_negative | 成交量 >= 0 | error |
| missing_dates | 交易日无缺失（排除节假日） | warning |
| sudden_jump | 相邻日涨跌幅 < 30% | warning |
| zero_volume | 连续 N 日成交量为 0 | warning |
| stale_data | 数据日期超过 N 天 | error |

### 校验流程
```
数据写入前 → DataQualityChecker.check()
  ↓
score >= 0.8 → 写入数据库 + 记录血缘
score < 0.8  → 标记为待审核，人工确认后写入
```

## 增量同步状态机

### 状态转换
```
[idle] → start() → [syncing]
[syncing] → complete() → [idle]
[syncing] → error() → [error]
[syncing] → pause() → [paused]
[paused] → resume() → [syncing]
[error] → retry() → [syncing]
[error] → reset() → [idle]
```

### SyncState
```python
class SyncState:
    def __init__(self, db_path: Path):
        self._state = "idle"
        self._progress: dict[str, str] = {}  # entity → last_synced_date
        self._errors: list[SyncError] = []
        self._load_from_db()

    def start(self, entity: str) -> None: ...
    def mark_progress(self, entity: str, last_date: str) -> None: ...
    def complete(self, entity: str) -> None: ...
    def error(self, entity: str, error: Exception) -> None: ...
    def pause(self) -> None: ...
    def resume(self) -> None: ...
    def get_progress(self, entity: str) -> str | None: ...
    def get_errors(self) -> list[SyncError]: ...
```

### SyncTaskQueue
```python
@dataclass
class SyncTask:
    entity: str             # "bond_daily" | "stock_daily" | "conv_price"
    cb_code: str
    start_date: str
    end_date: str
    priority: int           # 0=最高
    retry_count: int = 0
    status: str = "pending" # "pending" | "running" | "done" | "failed"

class SyncTaskQueue:
    def enqueue(self, task: SyncTask) -> None: ...
    def dequeue(self) -> SyncTask | None: ...
    def mark_done(self, task: SyncTask) -> None: ...
    def mark_failed(self, task: SyncTask, error: Exception) -> None: ...
    def retry_failed(self, max_retries: int = 3) -> int: ...
    def get_progress(self) -> SyncProgress: ...
```

### RetryPolicy
```python
class RetryPolicy:
    max_retries: int = 3
    base_delay: float = 1.0     # 秒
    max_delay: float = 60.0     # 秒
    backoff_factor: float = 2.0

    def get_delay(self, retry_count: int) -> float:
        """指数退避：base * factor^count"""
        return min(self.base_delay * self.backoff_factor ** retry_count, self.max_delay)
```

## 多数据源容错

### DataSourceManager
```python
class DataSourceManager:
    def __init__(self, sources: list[IDataFetcher]):
        self.sources = sources
        self._health: dict[str, bool] = {}

    def fetch_bond_list(self) -> pd.DataFrame:
        """依次尝试各数据源，第一个成功即返回"""
        for source in self.sources:
            try:
                result = source.fetch_bond_list()
                if not result.empty:
                    self._mark_healthy(source)
                    return result
            except DataFetchError:
                self._mark_unhealthy(source)
                continue
        raise DataFetchError("所有数据源均失败")

    def get_health_status(self) -> dict[str, bool]:
        """返回各数据源健康状态"""
```

### 数据源优先级
1. AkShare（主数据源）
2. Tushare（备用数据源，需 token）
3. 本地缓存（离线模式）

## 数据血缘

### DataLineage 模型
```python
class DataLineage(Base):
    __tablename__ = "data_lineage"

    id: Mapped[int] = mapped_column(primary_key=True, autoincrement=True)
    entity_type: Mapped[str] = mapped_column(String(50))     # "bond_daily"
    entity_key: Mapped[str] = mapped_column(String(200))     # "123001:2025-01-15"
    source: Mapped[str] = mapped_column(String(100))         # "akshare:bond_zh_hs_cov_daily"
    fetched_at: Mapped[datetime] = mapped_column(DateTime)
    row_count: Mapped[int]
    quality_score: Mapped[float]
    quality_report: Mapped[str | None] = mapped_column(Text)  # JSON
```

### 血缘记录时机
- 每次 fetcher 成功获取数据后
- 每次数据写入数据库后
- 质量校验完成后

### 血缘查询
```python
class LineageTracker:
    def record(self, entity_type, entity_key, source, row_count, quality_score): ...
    def get_history(self, entity_type, entity_key) -> list[DataLineage]: ...
    def get_by_source(self, source: str, limit: int = 100) -> list[DataLineage]: ...
    def get_stale_entities(self, max_age_days: int) -> list[str]: ...
```

## 数据库迁移

新增表：
- `data_lineage`：数据血缘追踪
- `sync_state`：同步状态持久化
- `quality_reports`：质量报告存储

迁移策略：使用 Alembic 或手动 SQL 迁移脚本。
