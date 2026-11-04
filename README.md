# quantumult-x-musk-rules

给 **Quantumult X（圈叉）** 用的马斯克 / X 全家分流规则，顺带提供 Loon 版。覆盖 **Grok / xAI**、**X（推特）** 和 **SpaceX / 星链**，外加推特自有 IP 段。

> **刻意不包含特斯拉。** 国内特斯拉 App、车机（`tesla.cn` 等）需要直连，所以 Tesla 的所有域名都被脚本强制过滤掉了，任何上游带进来的也会被删掉。

规则由 GitHub Actions **每天自动从上游重新生成**：合并、去重、校验语法，有变化才提交。

## 规则文件

| 文件 | 用途 | 订阅地址 |
| --- | --- | --- |
| `QuantumultX/X.list` | **合集（推荐）**：Grok/xAI + X/推特 + SpaceX/星链 + 推特 IP | https://raw.githubusercontent.com/lizimeng996/quantumult-x-musk-rules/main/QuantumultX/X.list |
| `QuantumultX/Grok.list` | 只含 Grok / xAI | https://raw.githubusercontent.com/lizimeng996/quantumult-x-musk-rules/main/QuantumultX/Grok.list |
| `QuantumultX/Twitter.list` | 只含 X / 推特（含 IP 段） | https://raw.githubusercontent.com/lizimeng996/quantumult-x-musk-rules/main/QuantumultX/Twitter.list |
| `QuantumultX/SpaceX.list` | 只含 SpaceX / 星链 / Starshield | https://raw.githubusercontent.com/lizimeng996/quantumult-x-musk-rules/main/QuantumultX/SpaceX.list |
| `Loon/*.list` | 上面四个的 Loon 版 | https://raw.githubusercontent.com/lizimeng996/quantumult-x-musk-rules/main/Loon/X.list 等 |

`raw.githubusercontent.com` 在国内拉不下来时，换成 jsdelivr：`https://cdn.jsdelivr.net/gh/lizimeng996/quantumult-x-musk-rules@main/QuantumultX/X.list`（其它文件同理）。

合集文件里用 `# ===== 分组 =====` 注释分段，文件开头有各类规则条数和更新日期。

## 覆盖范围

- **Grok / xAI**：`grok.com`、`grok.x.com`、`grokipedia.com`、`x.ai`
- **X / 推特**：`x.com`、`twitter.com`、`twimg.com`、`t.co`、`pscp.tv`、`periscope.tv`、`tweetdeck.com`、`twttr.com` 等
- **SpaceX / 星链**：`spacex.com`、`starlink.com`、`starshield.com`（手动维护，均已核实能解析）
- **IP**：推特 ASN 13414 当前宣告的网段（RIPEstat）+ blackmatrix7 里的推特 IP 段，已合并
- 不含 `HOST-KEYWORD,twitter` 这类过宽关键字，也不含特斯拉

## Quantumult X 用法

```ini
[filter_remote]
https://raw.githubusercontent.com/lizimeng996/quantumult-x-musk-rules/main/QuantumultX/X.list, tag=X, force-policy=美国节点, update-interval=86400, opt-parser=false, enabled=true
```

想让 Grok 单独走一个节点，就把 `Grok.list` 放在 `X.list` **上面**：

```ini
https://raw.githubusercontent.com/lizimeng996/quantumult-x-musk-rules/main/QuantumultX/Grok.list, tag=Grok, force-policy=美国节点, update-interval=86400, opt-parser=false, enabled=true
https://raw.githubusercontent.com/lizimeng996/quantumult-x-musk-rules/main/QuantumultX/X.list, tag=X, force-policy=代理, update-interval=86400, opt-parser=false, enabled=true
```

格式与 blackmatrix7 一致：规则行末尾写列表名（如 `X`、`Twitter`），订阅时请用 `force-policy=` 指定你实际的策略组，否则圈叉会报“未知策略”。

## Loon 用法

```ini
[Remote Rule]
https://raw.githubusercontent.com/lizimeng996/quantumult-x-musk-rules/main/Loon/X.list, policy=美国节点, tag=X, enabled=true
```

## 和其他规则冲突吗

不会出错，只有“谁先匹配”的问题：

- QX 的 `[filter_remote]` **从上到下匹配，命中第一条就停**。
- 如果你还订阅了别的规则（比如通用的「国外 / Proxy」大列表，或者单独的 Twitter 列表）也包含推特域名，那么**在 `[filter_remote]` 里排得更靠上的那条生效**。
- 建议：把本规则放在通用规则**上面**；原来单独订阅的 Twitter / Grok 列表可以删掉或 `enabled=false`，免得重复。
- 不删也没坏处，只是重复的那份不会被用到。
- 特斯拉不在本规则里，你原来的直连 / 国内规则照常生效。

## 自己构建

```bash
python3 scripts/build.py   # 只用 Python 标准库
```

工作流在 `.github/workflows/update.yml`：每天北京时间 10:27 运行，也可以在 Actions 页面手动运行。

## 规则来源与致谢

- [blackmatrix7/ios_rule_script](https://github.com/blackmatrix7/ios_rule_script)（GPL-2.0）：Twitter 规则
- [VPSDance/ai-proxy-rules](https://github.com/vpsdance/ai-proxy-rules)：x-ai 规则
- [v2fly/domain-list-community](https://github.com/v2fly/domain-list-community)（MIT）：twitter、xai、spacex
- [RIPEstat](https://stat.ripe.net/)：AS13414 网段
