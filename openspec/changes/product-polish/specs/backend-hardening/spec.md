## ADDED Requirements

### Requirement: Portfolio 文件原子写入

系统 SHALL 使用原子写入保护 Portfolio 文件完整性。

#### Scenario: 并发写入保护

- **WHEN** 多个请求同时尝试修改 portfolio.json
- **THEN** 系统 SHALL 使用原子写入（先写临时文件，再 replace）
- **AND** 文件 SHALL 不会损坏或丢失数据

#### Implementation

使用 `tempfile.NamedTemporaryFile` 在同目录创建临时文件，写入完成后用 `os.replace` 原子替换。

### Requirement: 回测超时处理

系统 SHALL 限制回测执行时间。

#### Scenario: 回测超时

- **WHEN** 回测执行超过 120 秒
- **THEN** 系统 SHALL 终止回测
- **AND** 返回错误消息 "回测超时，请缩短日期范围"

#### Implementation

使用 `threading` 在子线程中执行回测，主线程用 `thread.join(timeout=120)` 等待。

### Requirement: 孤立代码文档化

系统 SHALL 文档化未使用的代码模块。

#### Scenario: aligner/core.py 文档化

- **WHEN** 开发者查看 `src/quantified/aligner/core.py`
- **THEN** 文件顶部 SHALL 有模块级 docstring 说明：
  - 此模块当前未被 CLI 或 Web 流程使用
  - 提供的功能（历史转股价、停牌日检测）为未来功能预留
  - 如需启用，需在 universe.py 中替换相应调用