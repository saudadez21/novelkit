# ConfigAdapter

`ConfigAdapter` 是用于解析配置文件的高层接口, 负责将原始的 `general` 与 `sites` 配置映射解析为结构化的数据模型 (如 `FetcherConfig`、`ParserConfig`、`ClientConfig` 等)。

它封装了所有的配置合并逻辑:

* general -> site-specific -> built-in defaults
* 结构化转换, 例如: `OCRConfig` / `ProcessorConfig` / `BookConfig`
* 目录路径解析
* 登录/导出/插件等配置的读取

---

## Reference

::: novelkit.infra.config.adapter.ConfigAdapter
