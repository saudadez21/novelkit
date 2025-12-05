# Sessions

The `infra.sessions` module provides the unified HTTP session interface
used across NovelKit, including:

* `BaseSession` - abstract session API
* `AiohttpSession`, `HttpxSession`, `CurlCffiSession` - backend implementations
* `BaseResponse` - lightweight response wrapper
* `Headers` - case-insensitive multi-value header mapping
* `create_session()` - factory function for constructing session backends

---

## BaseSession

::: novelkit.infra.sessions.base.BaseSession

---

## BaseResponse

::: novelkit.infra.sessions.response.BaseResponse

---

## Headers

::: novelkit.infra.sessions.response.Headers

---

## create_session

::: novelkit.infra.sessions.create_session
