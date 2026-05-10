# API Gateway Spec

## 概述

API 网关提供版本化 RESTful API、WebSocket 实时推送、认证限流和 OpenAPI 文档。

## API 版本策略

- `/api/v1/*`：现有接口，保持向后兼容
- `/api/v2/*`：新接口，支持新功能
- v1 和 v2 并存，v1 逐步废弃

## 统一响应格式

### 成功响应
```json
{
  "status": "ok",
  "data": { ... },
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 150,
    "has_next": true
  }
}
```

### 错误响应
```json
{
  "status": "error",
  "error": {
    "code": "VALIDATION_ERROR",
    "message": "日期格式无效，请使用 YYYY-MM-DD 格式",
    "details": { "field": "date", "value": "2025/01/01" }
  }
}
```

### 错误码

| HTTP | Code | 说明 |
|------|------|------|
| 400 | VALIDATION_ERROR | 参数校验失败 |
| 401 | UNAUTHORIZED | 未认证 |
| 403 | FORBIDDEN | 无权限 |
| 404 | NOT_FOUND | 资源不存在 |
| 409 | CONFLICT | 资源冲突 |
| 429 | RATE_LIMITED | 请求过于频繁 |
| 500 | INTERNAL_ERROR | 服务器内部错误 |
| 503 | SERVICE_UNAVAILABLE | 服务不可用 |

## 认证

### API Key 认证
```python
# 请求头
X-API-Key: your-api-key-here

# 或查询参数
?api_key=your-api-key-here
```

### API Key 管理
```python
class APIKeyManager:
    def generate(self, name: str, scopes: list[str]) -> str: ...
    def validate(self, key: str) -> APIKeyInfo | None: ...
    def revoke(self, key: str) -> bool: ...
    def list_keys(self) -> list[APIKeyInfo]: ...
```

### 权限范围 (Scopes)
| Scope | 说明 |
|-------|------|
| `read:universe` | 读取市场数据 |
| `read:portfolio` | 读取持仓 |
| `write:portfolio` | 修改持仓 |
| `read:analytics` | 读取分析数据 |
| `read:monitor` | 读取监控数据 |
| `admin` | 管理权限 |

## 限流

```python
class RateLimiter:
    """基于滑动窗口的限流器"""

    def __init__(self, redis_client=None):
        # 有 Redis 用 Redis，否则用内存
        self._memory_store: dict[str, list[float]] = {}

    def is_allowed(self, key: str, limit: int, window_seconds: int) -> bool:
        """检查是否允许请求"""

    def get_remaining(self, key: str, limit: int, window_seconds: int) -> int:
        """获取剩余请求数"""
```

### 默认限流策略
| 端点 | 限制 |
|------|------|
| 通用 | 100/分钟 |
| /api/v2/backtest | 10/分钟 |
| /api/v2/analytics/* | 30/分钟 |
| /api/v2/portfolio/write | 20/分钟 |

### 限流响应头
```
X-RateLimit-Limit: 100
X-RateLimit-Remaining: 75
X-RateLimit-Reset: 1640000000
```

## CORS 配置

```python
CORS_CONFIG = {
    "origins": ["http://localhost:*", "http://127.0.0.1:*"],
    "methods": ["GET", "POST", "PUT", "DELETE", "OPTIONS"],
    "allow_headers": ["Content-Type", "X-API-Key"],
    "max_age": 3600,
}
```

## v2 端点清单

### 市场数据
```
GET /api/v2/universe?date=2025-01-15&page=1&page_size=50
GET /api/v2/universe/{cb_code}?date=2025-01-15
GET /api/v2/universe/audit?date=2025-01-15
```

### 策略
```
GET /api/v2/strategies
GET /api/v2/strategies/{name}
GET /api/v2/strategies/{name}/versions
POST /api/v2/strategies/{name}/backtest
```

### 因子
```
GET /api/v2/factors
GET /api/v2/factors/{name}?date=2025-01-15
GET /api/v2/factors/composite?date=2025-01-15
```

### 持仓组合
```
GET /api/v2/portfolios
POST /api/v2/portfolios                    # 创建组合
GET /api/v2/portfolios/{name}
DELETE /api/v2/portfolios/{name}
PUT /api/v2/portfolios/{name}/rename

GET /api/v2/portfolios/{name}/holdings
POST /api/v2/portfolios/{name}/buy
POST /api/v2/portfolios/{name}/sell
GET /api/v2/portfolios/{name}/history
GET /api/v2/portfolios/{name}/snapshots
POST /api/v2/portfolios/{name}/snapshot

POST /api/v2/portfolios/compare            # 组合对比
```

### 推荐
```
GET /api/v2/recommendation?date=2025-01-15&portfolio=default
```

### 分析
```
GET /api/v2/analytics/metrics?portfolio=default&start=2024-01-01&end=2025-01-15
GET /api/v2/analytics/attribution?portfolio=default&start=2024-01-01&end=2025-01-15
GET /api/v2/analytics/drawdown?portfolio=default
GET /api/v2/analytics/factor-exposure?portfolio=default&date=2025-01-15
GET /api/v2/analytics/benchmark-comparison?portfolio=default&benchmark=csi_cb
GET /api/v2/analytics/report?portfolio=default&period=monthly&year=2025&month=1
GET /api/v2/analytics/charts/{chart_type}?portfolio=default  # 图表数据
```

### 风控
```
GET /api/v2/risk/status?portfolio=default
GET /api/v2/risk/var?portfolio=default&confidence=0.95
GET /api/v2/risk/violations?portfolio=default
POST /api/v2/risk/stress-test?portfolio=default
```

### 监控
```
GET /api/v2/monitor/alerts?severity=warning&limit=20
GET /api/v2/monitor/health
GET /api/v2/monitor/health/history?days=30
POST /api/v2/monitor/alerts/{id}/acknowledge
```

### 回测
```
POST /api/v2/backtest
GET /api/v2/backtest/{job_id}              # 查询回测状态
GET /api/v2/backtest/{job_id}/result       # 获取回测结果
```

### 系统
```
GET /api/v2/health
GET /api/v2/stats
GET /api/v2/config
GET /api/v2/docs                           # OpenAPI 文档
```

## WebSocket

### 连接
```javascript
const socket = io('http://localhost:5000', {
  auth: { api_key: 'your-key' }
});
```

### 事件

| 事件 | 方向 | 说明 |
|------|------|------|
| `subscribe` | Client → Server | 订阅组合更新 |
| `unsubscribe` | Client → Server | 取消订阅 |
| `portfolio:update` | Server → Client | 持仓变动 |
| `alert:new` | Server → Client | 新告警 |
| `health:update` | Server → Client | 健康度更新 |
| `backtest:progress` | Server → Client | 回测进度 |

### 消息格式
```json
{
  "event": "portfolio:update",
  "data": {
    "portfolio": "default",
    "timestamp": "2025-01-15T15:00:00",
    "changes": [
      { "action": "buy", "cb_code": "123001", "volume": 100 }
    ]
  }
}
```

## OpenAPI 文档

使用 `flask-smorest` 或 `apispec` 自动生成：

```python
from flask_smorest import Api, Blueprint

api = Api(app)
api.spec.title = "Quantified API"
api.spec.version = "2.0.0"

blp = Blueprint("universe", "universe", url_prefix="/api/v2")

@blp.route("/universe")
class UniverseResource(MethodView):
    @blp.arguments(UniverseSchema, location="query")
    @blp.response(UniverseResponseSchema)
    def get(self, args):
        """获取全市场转债截面数据"""
        ...
```

访问路径：`/api/v2/docs`（Swagger UI）

## 分页

### 请求参数
```
?page=1&page_size=20&sort=composite_score&order=asc
```

### 响应 meta
```json
{
  "meta": {
    "page": 1,
    "page_size": 20,
    "total": 150,
    "total_pages": 8,
    "has_next": true,
    "has_prev": false
  }
}
```
