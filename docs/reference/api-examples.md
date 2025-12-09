# API 描述文档

本页展示如何使用 NovelKit 的核心 API

---

## 基础示例: 下载并导出书籍

```python
import asyncio
from novelkit.plugins import hub
from novelkit.schemas import ClientConfig

async def main() -> None:
    # 指定站点标识
    site = "n23qb"

    # 指定书籍 ID
    book_id = "12282"

    # 创建客户端配置
    cfg = ClientConfig(request_interval=0.5)

    # 获取站点客户端实例
    client = hub.build_client(site, cfg)

    # 在异步上下文中执行下载
    async with client:
        await client.download_book(book_id)

    # 下载完成后执行导出操作
    client.export_book(book_id, formats=["txt", "epub"])

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 下载部分章节范围

```python
import asyncio
from novelkit.plugins import hub
from novelkit.schemas import BookConfig, ClientConfig

async def main() -> None:
    site = "n23qb"

    # 指定书籍 ID + 章节范围
    book = BookConfig(
        book_id="12282",
        start_id="7909000",  # 第11章
        end_id="7909009",    # 第20章
    )
    cfg = ClientConfig(request_interval=0.5)
    async with hub.build_client(site, cfg) as client:
        await client.download_book(book)

    # 只导出为 TXT
    client.export_book(book, formats=["txt"])

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 仅导出为 EPUB

如果本地已有缓存, 可直接导出 EPUB:

```python
from novelkit.plugins import hub

site = "n23qb"  # 站点标识
client = hub.build_client(site)

client.export_book("12282", formats=["epub"])
```

---

## 搜索 + 下载 + 导出

```python
import asyncio
from novelkit.plugins import hub

async def main() -> None:
    keyword = "三体"
    site = "n23qb"

    async with hub.build_client(site) as client:
        results = await client.search(keyword)
        if not results:
            print(f"未找到与 '{keyword}' 匹配的结果")
            return

        print(f"共找到 {len(results)} 个结果:")
        for idx, item in enumerate(results[:5], start=1):
            print(f"[{idx}] {item['title']} - {item['author']} ({item['site_name']})")

        # 选择第一个结果进行下载
        first = results[0]
        book_id = first["book_id"]

        print(f"\n开始下载: {first['title']} - {first['author']} (站点: {site})")
        await client.download_book(book_id)

        # 导出为 txt 与 epub
        client.export_book(book_id, formats=["txt", "epub"])

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 登录示例 (账号)

如果站点需要登录, 只需在进入 `async with client:` 后调用 `client.login()`:

```py
import asyncio
from novelkit.plugins import hub

async def main() -> None:
    site = "esjzone"

    client = hub.build_client(site)
    book_id = "1615526434"

    async with client:
        # 登录 (示例: 账号+密码)
        ok = await client.login(
            username="myusername",
            password="mypassword",
        )

        if not ok:
            print("登录失败")
            return

        print("登录成功")

        # 登录后即可正常下载
        await client.download_book(book_id)

    # 导出书籍
    client.export_book(book_id, formats=["epub"])

if __name__ == "__main__":
    asyncio.run(main())
```

---

## 登录示例 (Cookie)

某些站点可无需账号密码, 仅用 cookies:

```py
async with client:
    ok = await client.login(cookies={
        "session": "abcd1234",
        "auth": "xyz987",
    })

    if not ok:
        print("Cookie 已失效")
        return
```

---

## 下载过程进度回调

```python
import asyncio

from novelkit.plugins import hub
from novelkit.schemas import BookConfig, ClientConfig

class SimpleDownloadUI:
    async def on_start(self, book: BookConfig) -> None:
        print(f"\n开始下载: {book.book_id}")

    async def on_progress(self, done: int, total: int) -> None:
        percent = (done / total * 100) if total else 0.0
        print(f"\r进度: {done}/{total} ({percent:.1f}%)", end="", flush=True)

    async def on_complete(self, book: BookConfig) -> None:
        print(f"\n下载完成: {book.book_id}")

async def main() -> None:
    cfg = ClientConfig(request_interval=0.5)

    site = "n23qb"
    book = BookConfig(book_id="12282")

    client = hub.build_client(site, cfg)

    async with client:
        await client.download_book(book, ui=SimpleDownloadUI())

    # 导出为 txt 与 epub
    export_result = client.export_book(book, formats=["txt", "epub"])

if __name__ == "__main__":
    asyncio.run(main())
```
