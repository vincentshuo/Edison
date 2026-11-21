# 多上游独立演进：成熟机制与适用边界

研究日期：2026-11-16。本文是研究资料，不是已接受的架构决策、规格或工作 tracker；后续决策应遵循仓库的 GitHub Issue 与 ADR 约定。

## 结论

这类需求已有成熟解法，但不是某一个 Git 命令：**独立上游依赖 + 自有适配/扩展层 + 受控版本升级**。其中源码来源独立、运行时隔离、接口兼容、产品发布独立是不同维度；一个 submodule 只直接解决其中的源码与版本边界。

对 Edison 的建议是把自身变成产品组合层，让 OpenWorker 与未来开源项目成为可以替换、可以独立推进版本的组件。能使用稳定软件包或制品的优先作为依赖；需要原始源码的采用固定提交的 submodule 或受控 vendor；确实必须修改上游时，维护薄 fork 或显式补丁队列。自研功能归 Edison 所有，不混入各个上游源树。这是从以下成熟实践归纳的架构建议，不意味着 OpenWorker 已经提供现成、稳定的宿主插件接口。

**可自动化的是发现更新、获取源码、重放补丁、构建、验证和生成升级候选；不能承诺任意上游破坏性变化都无需适配。** “一键同步”应当表示一键执行受控升级流程，失败后保留当前可用组合，而不是无条件把所有项目切到远端最新提交。

## 1. Git 能解决什么

| 机制 | 官方能力 | 适合的情形 | 不解决的问题 |
|---|---|---|---|
| Git submodule | 上层仓库记录子仓库的具体提交；各自保留独立历史 | 多上游源码组件、希望清晰表达版本和所有权 | 不会隔离 Python/Node 依赖冲突，也不会消除 API 不兼容 |
| Git subtree | 把子项目放进普通子目录，支持 pull/merge 和 split 回独立历史 | 希望一次普通 clone 获得完整源码、接受 vendor 工作流 | 下游修改仍会与上游冲突；历史整合不等于模块边界 |
| 薄 fork / 补丁队列 | 用 Git 合并或重放维护少量上游差异 | 上游缺少必需扩展点、临时修复尚未被接纳 | 补丁需要持续维护；上游改动后仍可能人工处理冲突 |
| 软件包 / 镜像 / 二进制依赖 | 使用生态自身的版本化分发机制 | 上游已有可消费、可固定版本的正式产物 | 分发机制不能替代公开接口和兼容性验证 |

Git 官方明确将 submodule 用途之一描述为：分别保存两个项目的历史，将子项目固定在任意版本，让其可以独立开发，上层项目只在希望的时候切到新版。[G1]

必须区分两个动作：[G2]

- `git submodule update --init --recursive` 默认恢复上层仓库记录的提交，服务于可重复构建。
- `git submodule update --remote` 从远端分支取得候选提交；上层仓库仍需记录新的指针，才能把新组合发布给其他开发者或部署环境。

Git subtree 官方文档也明确说明，子树是普通子目录、不会要求使用者理解 `.gitmodules`；但 merge 产生冲突时仍要按普通方式解决。因此把当前混合仓库改成 subtree，并不能自动治好侵入式定制。[G3]

## 2. 成熟案例提供的可借鉴结构

### Chromium：依赖清单、固定版本、升级流程、边界检查

Chromium 用 DEPS / gclient 管理外部依赖，支持把某个依赖推进到具体 hash；官方文档把升级称为 rolling dependencies。更改依赖的通常流程是先向上游贡献，然后 roll 进 Chromium；部分项目有 autoroller。其 checkdeps 还检查源代码之间的引用边界。[C1]

启示：真正成熟的“一键”背后是**可重建的版本组合和验证流程**，不是各目录分别执行 `git pull`。Edison 可以借鉴思想，无需为小型项目照搬 Chromium 全套基础设施。

### Yocto：独立定制层与显式补丁

Yocto Layer Model 的直接目的就是把不同类型的定制相互隔离；层可以声明依赖与版本兼容性。`.bbappend` 可以在自己的层中扩展其他层的 recipe，且上游 recipe 版本变化时需检查、调整对应扩展。[Y1]

`devtool finish` 可以把已提交的修改变成补丁并归入长期维护的 layer；`devtool upgrade` 明确包含升级后解决补丁冲突、再构建的过程。[Y2]

启示：这是“上游源 + 下游定制层”的成熟实证，同时也是自动升级不能凭空消除冲突的实证。Edison 可采用同样的所有权与补丁纪律，通常不需要引入面向嵌入式 Linux 的 Yocto 构建系统。

### Backstage：宿主、插件、服务、扩展点

Backstage 的新后端系统区分 backend、plugin、service、extension point 和 module。官方允许一个 backend 容纳全部功能，或按需要拆成多个部署；插件之间必须通过网络通信，扩展 module 则只通过插件注册的 extension point 交互，并与该插件部署在同一 backend。[B1]

启示：**独立功能与一个统一产品入口可以并存，模块化不要求每个模块都单独部署。** 可借鉴其显式扩展点与生命周期组织；不能把 Backstage 的网络隔离规则直接等同于 Edison 当前模块规范，也不建议为了这个问题把整个产品迁到 Backstage。

### VS Code：独立扩展需要兼容契约

VS Code 用 Extension Host 管理扩展运行，支持不同宿主形态和按事件激活；extension manifest 必须声明 `engines.vscode` 兼容范围，不能用 `*`。[V1][V2]

启示：插件能独立发布，不代表与所有宿主版本都兼容。Edison 若建设自己的插件接口，需要给契约版本、能力、生命周期和兼容性以明确表达；仅建立 `plugins/` 目录不够。

## 3. 自动升级工具及限制

Renovate 官方提供 `git-submodules` manager，识别 `.gitmodules`，但它**默认关闭**，需要显式启用。[R1] 普通软件包和镜像则可使用相应内置 manager；自定义版本清单也有 regex manager 可扩展，宜先优先采用现有标准格式。[R2]

Renovate 的自动合并默认等待通过的 status checks / check runs。项目仍需配置真实有效的构建、契约和关键用户路径验证；工具的绿灯能力取决于检查覆盖，不是功能正确性的数学保证。[R3]

建议把两个日常操作分开：

1. **同步已验证组合**：每个组件恢复锁定版本，不改变产品基线。
2. **升级某个上游**：选择候选版本 → 更新该组件指针 → 必要时重放薄补丁 → 验证 → 形成可评审升级 → 接受后更新基线。

一次升级优先只改变一个上游，利于定位问题。确有跨组件兼容关系时应按兼容组推进；独立来源不保证可以任意组合版本。

Docker Compose 的 `include` 可把各自拥有配置的 Compose 应用模型组合起来，支持相对路径独立解析和覆盖；该能力适合已经需要独立运行环境的组件，但只处理部署组合，不负责源码同步或 API 兼容。[D1]

## 4. 对 Edison 的适用判断

本节是建议，不是已批准迁移计划：

- 先找出 OpenWorker 原始基线及 Edison 差异，将差异区分为自研业务、宿主接线、上游必须修改的最小部分。无法溯源的“整棵替换”不能叫安全升级。
- 自研业务从上游所有权范围移出；Edison 维护自己的导航、业务编排与适配层。适配层只消费明确接口，避免多处直接依赖上游内部实现。
- OpenWorker 若缺少所需扩展点，可先保留薄 fork，集中有限接线改动；不应以“必须零修改上游”为前提重写既有核心能力。
- 对纯库采用版本依赖、对可独立提供 API/CLI 的应用采用协议适配、对需源码整合的项目采用锁定源码；不强迫所有项目使用同一种运行模型。
- 保持单实例部署目标，只有语言依赖、资源或故障隔离等真实需求才引入进程/容器边界。
- 把代码回滚与数据迁移区分：恢复旧组件指针不保证数据库能回滚；涉及数据格式变化的升级需独立验证恢复策略。

## 一手来源及核验

以下页面均在研究时实际取得并读取正文。Git 官网正文访问返回 403，因此改读 Git 官方仓库中的同源文档；未以搜索摘要作为证据。链接通常指向滚动文档，内容可能后续变化。

- [G1 — Git: gitsubmodules](https://github.com/git/git/blob/master/Documentation/gitsubmodules.adoc)
- [G2 — Git: git-submodule](https://github.com/git/git/blob/master/Documentation/git-submodule.adoc)
- [G3 — Git: subtree documentation](https://github.com/git/git/blob/master/contrib/subtree/git-subtree.adoc)
- [C1 — Chromium: Managing dependencies](https://chromium.googlesource.com/chromium/src/+/main/docs/dependencies.md)
- [Y1 — Yocto: Understanding and Creating Layers](https://docs.yoctoproject.org/dev-manual/layers.html)
- [Y2 — Yocto: Using the devtool command](https://docs.yoctoproject.org/dev-manual/devtool.html)
- [B1 — Backstage: New Backend System](https://backstage.io/docs/plugins/new-backend-system/)
- [V1 — VS Code: Extension Host](https://code.visualstudio.com/api/advanced-topics/extension-host)
- [V2 — VS Code: Extension Manifest](https://code.visualstudio.com/api/references/extension-manifest)
- [R1 — Renovate: Git Submodules](https://docs.renovatebot.com/modules/manager/git-submodules/)
- [R2 — Renovate: Regex custom manager](https://docs.renovatebot.com/modules/manager/regex/)
- [R3 — Renovate: Automerge](https://docs.renovatebot.com/key-concepts/automerge/)
- [D1 — Docker: Include](https://docs.docker.com/compose/how-tos/multiple-compose-files/include/)
