# Edison 多上游独立演进：架构研究

研究日期：2026-11-16（Asia/Shanghai）。本文是研究材料，不是已批准的 ADR、规格或工作票；不改变现有架构决策。通用工具的一手证据见 [来源研究附录](multi-upstream-primary-sources-2026-11-16.md)。

## 结论

成熟方案确实存在，但不是一个 Git 命令：**应用组合架构 + 独立上游依赖 + 薄适配层 + 锁定版本 + 自动化升级验证**。

对 Edison，建议让 Edison 成为产品宿主，OpenWorker 成为可升级的能力提供者；YouTube、Curriculum、Reader 等自有模块由 Edison 管理，不再作为长期改动散落在 OpenWorker 的核心入口中。能使用公开 SDK/包的项目优先作为版本依赖；需要整份源码的项目使用独立 checkout/submodule；不得不修改的上游维护独立 fork 和小型补丁集。

“一键同步”的可实现定义是：获取某个上游的新版本、重建候选集成、运行验证、生成可评审的升级差异，在兼容时完成升级；它不能保证任何上游的任意破坏性变更都无需适配。独立升级意味着可以分别选择版本，不意味着所有版本组合永远兼容。

## 1. Edison 当前为何难以同步

本地检查基于 HEAD `e0bb58d` 和当时的工作区；没有修改已有业务文件，也没有运行生产升级。

### 来源关系存在，版本依赖关系缺失

[OpenWorker 来源记录](../upstream/openworker/PROVENANCE.md) 记载：2026-09-18 将 `andrewyng/openworker` 的 `5bc10d928e0b64aae74313349a3b17bd19643ae2` 直接导入 Edison 根目录，保留了许可证和项目元数据，并关闭了上游自动更新通道。当前主仓库只有 Edison 的 `origin`；没有以独立依赖锁住 OpenWorker 源码树。原始 Git 数据仍在本地 `.git/imports/openworker-git`，其 HEAD 与来源记录一致，但不随仓库分发。

因此不是永久失去了同步能力，而是需要恢复“上游原版、Edison 增量、组合版本”三个可单独辨认的对象。关闭桌面自动更新器本身合理：上游桌面发行物不能直接替换 Edison 的定制 Web 产品。

### 耦合集中在产品入口和共享宿主能力

- `coworker/server/app.py` 注册 Edison 的 YouTube、Curriculum、Reader 路由，并添加 Web 登录与认证处理。
- `surfaces/gui/src/App.tsx` 直接编排 Edison 模块；Sidebar、Settings、API、国际化和样式也有改动。
- `coworker/server/youtube.py` 使用宿主 manager 的模型能力；Curriculum 使用其数据目录与设置。需要将这类依赖收敛为 Edison 维护的接口，避免业务模块依赖上游私有对象。
- `pyproject.toml` 把 `coworker`、`youtube_strataread`、`translation_agent` 一并打包；这只是统一构建，不代表三者已经有可独立升级的契约。

以原始 OpenWorker commit 的已跟踪文件为范围，用 Git blob hash 与当前磁盘文件比较：`coworker/` 180 个基线文件中 172 个未变、8 个改变；`surfaces/gui/` 270 个中 231 个未变、39 个改变。**不包括 Edison 新增文件，不衡量改动行数，也不是与最新上游的冲突预测。** 这说明原版保留程度较高，值得先恢复边界，不能据此承诺迁移成本低。

### 项目已经包含三种不同的上游关系

1. **OpenWorker：直接导入并改造的应用宿主。** 最需要重新建立独立版本边界。
2. **translation-agent：带来源快照和补丁的源码依赖。** `UPSTREAM.json` 固定 `e0fc605acbb5d78cb7a58a98bc8bd8f0056df49c`，保留完整压缩包、文件 hash 和 `EDISON.patch`。这是良好起点，但快照本身不是同步流程；当前运行源码仍在 Edison 内部。
3. **Vegapunk：行为移植和局部 UI 源码改造。** ADR 0002 明确选择过行为重实现，发现流程后来又被官方 YouTube API 方案替代。不能把来源署名等同于实时依赖：不再复用的上游行为，应明确属于 Edison 自己维护的实现，不应自动追随整个 Vegapunk。

## 2. 最新的重要发现：OpenWorker 已经提供官方嵌入路径

在线核验上游 `main` 为 `ecb445490fc054d52b8ea610d97ba947f57033d2`。以下链接固定该版本，避免滚动 README 改变证据。

- [官方主 README](https://github.com/andrewyng/openworker/blob/ecb445490fc054d52b8ea610d97ba947f57033d2/README.md) 已将 Desktop App 与 Harness SDK 区分。
- [Harness SDK README](https://github.com/andrewyng/openworker/blob/ecb445490fc054d52b8ea610d97ba947f57033d2/harness/README.md) 明确由应用拥有 UI、认证、用户与会话归属，由 Harness 提供 Agent 循环、工具调用、审批、流式输出和持久会话。
- [架构指南](https://github.com/andrewyng/openworker/blob/ecb445490fc054d52b8ea610d97ba947f57033d2/docs/harness/guides/architecture.md)：TypeScript SDK 管理 Rust 子进程；Rust 可进程内嵌入。共享服务是另一种选择，不是强制条件。
- [Web 指南](https://github.com/andrewyng/openworker/blob/ecb445490fc054d52b8ea610d97ba947f57033d2/docs/harness/guides/server.md) 提供一个容器内应用服务器与 Harness 子进程的示例。
- [版本指南](https://github.com/andrewyng/openworker/blob/ecb445490fc054d52b8ea610d97ba947f57033d2/docs/harness/guides/releases.md) 与 [npm registry](https://registry.npmjs.org/@openworkerai%2fharness-sdk/latest) 实查一致：SDK `0.1.0-beta.4`，匹配的平台 runtime `0.1.0-beta.3`。二者版本号不同是官方配套关系，不能分别追 latest。

**适合方向，不是直接替换。** 官方声明 SDK API 仍在演进；桌面应用仍使用独立 Python 引擎。Edison 当前的 Python 引擎、对话持久化、连接器、模型设置、自动化和 UI 不能假定全部可以无损换成 SDK。这需要单独验证功能覆盖、数据迁移与资源占用。npm 包存在只证明嵌入路径可获得，不证明 Edison 已兼容。

## 3. 成熟方案分别解决什么

| 方案 | 独立更新的对象 | 主要收益 | 没有解决的问题 | Edison 适用性 |
|---|---|---|---|---|
| 官方包 / SDK / 固定镜像 | 发布版本或制品摘要 | 消费公开契约，上游内部重构影响较小 | API、行为与数据迁移仍可能变化 | 新集成首选；OpenWorker SDK 是候选 |
| Git submodule | 独立仓库的确切 commit | 保留上游完整树与历史，宿主锁定组合 | 不隔离运行依赖，也不阻止业务耦合 | 必须使用源码时的默认候选 |
| Git subtree | 导入宿主的子目录与合并关系 | 普通 clone 即获得源码，工具门槛较低 | 改上游文件仍有合并成本，独立性约束更弱 | 更重视单仓库分发时的备选 |
| 独立 fork + 小补丁集 | 上游版本加自有增量 | 支持缺失的扩展点和必要修补 | 仍需处理补丁与语义冲突 | 现有 OpenWorker 的渐进迁移路线 |
| SDK / 插件接口 / 适配层 | 能力契约 | 把变化挡在模块边界 | 上游不提供接口时须建立边界 | 架构主干，不能由 Git 工具代替 |
| 进程或容器组合 | 独立运行环境与制品 | 隔离依赖冲突、运行生命周期 | UI、鉴权、数据迁移与 API 兼容仍需治理 | 按需采用，不要求所有模块微服务化 |

工具细节与一手出处见附录。尤其注意：`git submodule update --init --recursive` 是恢复宿主锁定的版本；`--remote` 才会按远端跟踪设置选取更新。升级结果仍需要写入父仓库的 gitlink 并验证，不能把这两件事混称“同步最新”。

### 可借鉴的成熟案例

- **Chromium DEPS / gclient**：在组合清单里管理大量独立源码依赖，并统一同步工作区；证明“多上游 + 一个可复现产品版本”是成熟实践。Edison 不需要照搬其规模和工具复杂度。
- **Yocto layers / recipes / patches**：上游源版本、产品定制层与补丁分别管理；证明长期下游定制可以被显式维护，而不是混成不可辨认的源码。
- **Backstage 插件架构**：由宿主组合独立插件，通过明确的服务接口连接；官方同时支持一个 backend 承载多个功能或拆开部署，说明模块独立与微服务数量不是同一个问题。
- **VS Code Extension API**：插件通过公开 API 和兼容版本要求接入宿主，体现扩展边界的价值；它不是让任意第三方应用自动变成可嵌入插件的通用方案。

这些案例证明的是组合方法的成熟度，不代表 OpenWorker beta SDK 自身已经达到同样成熟度。

## 4. 建议的 Edison 目标结构

产品关系应是：

```text
Edison 产品宿主：导航、登录、业务编排、应用配置与知识资产
  ├─ 自有模块：YouTube / Curriculum / Reader / 后续模块
  ├─ Edison 能力接口与适配器
  │    ├─ OpenWorker adapter → 固定版本的引擎或 SDK
  │    ├─ Translation adapter → 固定版本 translation-agent
  │    └─ 其他 adapter → 其他上游 SDK / 源码 / 服务
  └─ 组合清单：版本、补丁、依赖锁、验证与发布
```

“适配器”应把 Edison 的需求映射到上游能力，而不是重写上游算法。上游应拥有自己的引擎、内部状态格式和实现；Edison 拥有产品实体、用户体验及模块间的协作规则。避免把上游私有数据库表、manager 内部字段或前端组件目录变成自有模块的长期接口。

**源码边界、运行边界、发布边界是三件不同的事。** 独立仓库可以在同一进程中运行，也可以统一构建一个发行物。Edison 仍可保持 ADR 0013 的一个自托管实例；其中必要的子进程并不意味着拆成多个产品实例。该 ADR 记录的服务器内存预算为 2.5 GB，是否增加运行时需实测，不能凭架构图宣称可承受。

### 前端需要作出的实质取舍

若仍要完整继承 OpenWorker 每次最新 UI，又深度改动同一套 App/Sidebar/Settings，长期就仍是 UI fork。三条路线分别是：

1. Edison 自有 shell，消费上游正式提供的 UI 扩展点或组件包（如果有）。不能假定当前 OpenWorker 已提供稳定的整个产品 UI 插件 API。
2. Edison 自有 shell 与业务页面，上游提供引擎/SDK。源码独立性较强，但 Edison 要维护自己的产品 UI。
3. 保留上游完整 Web UI，通过路由、反向代理或 iframe 接入。代码改动少，但登录、路径、WebSocket、嵌入策略和视觉交互要验证；OpenWorker 的桌面导向不能直接等同于可无缝嵌入的 Web 服务。

建议渐进走向第 2 条，并允许过渡阶段保留小型 UI fork。不能同时承诺任意深度改造原版 UI、原样继承所有上游 UI 更新、以及永远零冲突。

## 5. 一键升级应该怎样运作

目标体验可以是“更新 OpenWorker”或“检查全部上游”，背后是一条明确流程，而非在生产机对各目录直接 pull：

1. 读取当前产品锁定的上游版本与补丁版本，为选定依赖获取候选版本。
2. 在候选工作区还原源码/制品，应用少量必要补丁；冲突时明确停止并定位到适配层或补丁。
3. 解析并锁定依赖，检查上游相关测试、Edison 契约测试、关键用户流程及数据迁移。
4. 输出独立升级差异或升级 PR。Renovate 可处理常见依赖和 submodule 的候选更新；submodule manager 默认关闭，需要显式启用。任意自定义补丁和数据库兼容并不由 Renovate 自动解决。
5. 验证通过后提升整个已验证版本组合。保留旧代码/制品与数据恢复方案；数据库升级后仅回退代码未必可行。

每次优先升级一个上游便于定位问题；对 SDK 与其配套 runtime 等强耦合版本应作为一组升级。全部检查可以一键触发，但不应把所有不兼容版本同时合进主干。

“彼此独立”至少有四项验收含义：有清晰源码所有权；有确切版本；业务只依赖契约；单个依赖升级失败不迫使其余模块跟着重写。包管理器、Git 与 CI 各负责其中一部分。

## 6. 渐进迁移建议（研究建议，尚未批准实施）

**第一步：恢复可追踪的 OpenWorker 下游。** 利用原始 commit 与保留的 Git 数据，将现有改动识别为上游原版、自有功能、适配补丁三类。先保持当前功能与版本不变，再形成独立的源码依赖或 fork。不能先搬目录后认为已解耦；构建路径、打包、CI、认证、资源文件及新增文件归属都需核对。

**第二步：将自有产品入口移出上游。** 把自有模块注册、业务路由和导航组合的所有权收回 Edison；用薄适配层连接现有 Python OpenWorker。若没有可用扩展点，少量有来源、有理由的补丁比伪装成“零修改”的 monkey patch 更可维护。

**第三步：以 translation-agent 验证多上游更新流程。** 它已有完整来源、补丁和契约测试，更适合先跑通可复现升级。保持 ADR 0019 对完整上游翻译流程与独立保留结果的要求；不能以同步便利为由重写翻译算法。将来可上游化的注入点应争取上游接受，不能假定维护者一定合并。

**第四步：独立验证 OpenWorker Harness SDK。** 比较会话/审批/连接器/模型/自动化等实际必需能力；验证数据迁移、重启恢复及内存。通过后再选择替换现有 Python adapter，未通过则继续维护可同步的 Python fork。这是引擎迁移选项，不是恢复上游同步的前置条件。

**第五步：确立后续开源项目的接入规则。** 入场时就决定是包、完整源码、服务还是一次性移植；记录版本与许可证；禁止在未声明的情况下修改上游源码；必要补丁单独管理；接入前先确认有可维护的接口和数据边界。

## 7. 尚未验证、不能据此承诺的内容

- 未执行 Edison 与最新 OpenWorker 的完整合并，没有计算实际冲突数或迁移工期。
- 未安装或运行新 SDK，没有验证其与现有功能、凭据和存储格式的兼容性，也没有测内存。
- 本地 blob 统计不包含新增业务文件、依赖差异和运行行为差异。
- 未建立 CI 升级流水线或修改 remote/submodule/fork；本次仅研究。
- 未将建议写成已接受 ADR，也未创建规格或工作票；后续决策与实施追踪应按仓库约定进入 GitHub Issues。

最终建议：**先把“Edison 是 OpenWorker 的深度改版”转为“Edison 组合多个独立演进的能力”。工具默认包优先、源码 submodule 次之、必要 fork 显式化；通过版本清单和验证流程实现可控的一键升级。**
