---
source: guide/services.md
source_hash: 3aa1d341057a
---
# 声明式服务

::: info 机器翻译
本页由英文原文机器翻译而来，尚未经过母语审校，欢迎在 GitHub 上提出修改。内容如有出入，以[英文原文](/guide/services)为准。
:::

有些逻辑属于 Python：读取文件系统、启动进程、调用某个库。把它写成普通的 Python 函数，用 `@service` 给它一个名字，然后在页面中用 `q:invoke service=` 调用它。

页面只写明它调用什么；Python 代码按 Python 的方式编写、评审和测试。除非 `quantum.config.yaml` 列出，否则不会导入任何模块。

本页的文件组成一个小应用，CI 会运行并检查它（`tests/docs/test_guide_services.py`）。

## 1. 编写服务 {#_1-write-the-service}

保存为 `myapp/services.py`：

```python
from pathlib import Path
from quantum.services import service


@service("reports.list")
def list_reports(folder: str = "reports", limit: int = 20):
    if not Path(folder).is_dir():
        raise FileNotFoundError(f"no folder named {folder}")
    files = sorted(Path(folder).glob("*.pdf"), key=lambda p: p.name)
    return [{"name": f.name, "size": f.stat().st_size} for f in files[:limit]]
```

服务返回普通数据——列表、字典、文本、数字。它和其他值一样可以在表达式中使用。

## 2. 列出模块 {#_2-list-the-module}

保存为 `quantum.config.yaml`：

```yaml
services:
  - myapp.services
```

模块只有被列出时才会导入（SVC-2）。它必须能从 `quantum start` 运行的位置导入（项目文件夹在路径中），而一个被列出但导入失败的模块会带着导入错误停止页面。

## 3. 调用它 {#_3-call-it}

保存为 `components/reports.q`：

```xml
<q:component name="reports" xmlns:q="https://quantum.lang/ns">
  <q:invoke name="reports" service="reports.list">
    <q:param name="limit" value="10" type="integer" />
  </q:invoke>

  <ul>
    <q:loop items="{reports}" var="r">
      <li>{r.name} — {r.size} bytes</li>
    </q:loop>
  </ul>
</q:component>
```

每个 `q:param` 是一个关键字参数，和任何 [`q:param`](/zh/guide/functions#parameters) 一样按它的 `type` 转换（SVC-3）。`reports/` 中有 `annual.pdf`（1200 字节）和 `q1.pdf`（300 字节）时，`/reports` 显示：

```text
annual.pdf — 1200 bytes
q1.pdf — 300 bytes
```

## 当它失败时 {#when-it-fails}

服务抛出的异常是一次调用失败（INV-2）：没有 `reports/` 文件夹时，`/reports` 会停止。访问者看到一个错误页面，服务器日志写着 `q:invoke 'reports' failed: service 'reports.list' failed: no folder named reports`。如果想在页面中处理它，加上 `onerror="continue"` 并读取 `reports_result`。保存为 `components/safe-reports.q`：

```xml
<q:component name="safe-reports" xmlns:q="https://quantum.lang/ns">
  <q:invoke name="reports" service="reports.list" onerror="continue" />
  <q:if condition="reports_result.success">
    <p>{len(reports)} reports</p>
    <q:else><p>Could not list reports: {reports_result.error.message}</p></q:else>
  </q:if>
</q:component>
```

有这个文件夹时，`/safe-reports` 显示 `2 reports`；没有时显示 `Could not list reports: service 'reports.list' failed: no folder named reports`。

未注册的名字是一个错误，错误信息会列出已注册的名字。`onerror` 接受 `fail`（默认）或 `continue`；其他值无法通过解析：

```xml
<q:invoke name="reports" service="reports.list" onerror="ignore" />
```

**Error:** `onerror must be "fail" or "continue", not "ignore"`

## 服务还是 `q:python`？ {#services-or-q-python}

优先使用服务。`q:python` 把 Python 放进页面里，在那里它无法单独测试，也很容易膨胀成页面的全部逻辑。规则是 [SVC-1 到 SVC-3](../../reference/spec#SVC-1)。
