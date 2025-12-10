---
title: アルファポリス
tags:
- 日文
- 原创
- 免费
- 订阅制
- 轻小说
- 综合
---

小説・漫画の投稿サイト「アルファポリス」は、誰でも自由に作品を読めて、書くことができる総合エンターテインメントサイトです。

毎日無料で読める公式連載漫画も充実。ビジネス情報も満載。

## 基本信息

* 标识符: `alphapolis`
* 主页: https://www.alphapolis.co.jp/
* 语言: 日文
* 站点状态: :green_circle: 活跃
* 支持分卷: :material-minus-circle: 部分支持
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

* URL: <https://www.alphapolis.co.jp/novel/547686423/112003230>
* Book ID: `547686423-112003230`

### 章节内容页 (Chapter URL)

* URL: <https://www.alphapolis.co.jp/novel/547686423/112003230/episode/10322710>
* Book ID: `547686423-112003230`
* Chapter ID: `10322710`

---

## 备注

### 其它说明

若出现 `Empty parse result`, 通常表示以下情况之一:

* 访问过于频繁, 服务器暂时拒绝了请求
* 页面使用了懒加载机制, 需要额外获取正文内容
* 章节内容未能正确返回

建议按 `Ctrl+C` 终止程序, 稍候片刻后再次运行。

后续版本将加入:

* 自动重试机制
* 在需要时自动请求额外页面或正文接口
