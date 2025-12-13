---
title: 哔哩哔哩 (专栏)
tags:
- 简体中文
- 原创
- 转载
- 免费
- 二次元
---

哔哩哔哩专栏是为全体UP主开放的个人空间、自媒体平台，UP主可通过专栏平台分享自己的经验、攻略、心得等文章信息

## 基本信息

* 标识符: `bilibili`
* 主页: https://search.bilibili.com/article
* 语言: 简体中文
* 站点状态: :green_circle: 活跃
* 支持分卷: :material-close: 否
* 支持插图: :material-check: 是
* 支持登录: :material-minus-circle: 部分支持
* 支持搜索: :material-open-in-new: 站点支持，需站内操作

---

## 健康检查报告

| 后端    | 状态     |
| ------- | -------- |
| `aiohttp` | :green_circle: |
| `curl_cffi` | :green_circle: |
| `httpx` | :green_circle: |

---

## URL 示例

### 书籍页面 (Book URL)

* URL: <https://www.bilibili.com/read/readlist/rl73910>
* Book ID: `rl73910`

### 章节内容页 (Chapter URL)

* URL: <https://www.bilibili.com/opus/117568184198533819/>
* Chapter ID: `117568184198533819`

---

## 备注

### 访问频率限制

当请求过于频繁时, 服务器可能返回验证码页面, 导致内容暂时无法获取

应对方式:

* 控制请求频率: 合理设置请求间隔, 避免在短时间内连续请求大量资源
* 等待限制解除后重试: 该类限制通常为临时措施, 在访问频率降低后, 会在数分钟内自动解除, 可稍后再次尝试
