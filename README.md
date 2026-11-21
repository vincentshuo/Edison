# Edison

Edison 将 YouTube 阅读资料库与课程周览整合在同一工作区。

- 侧边栏 **YouTube** 阅读按频道整理的 HTML 报告，支持未读、已读和精选。
- 新报告放入 `surfaces/gui/public/youtube/Channel/<频道>/`。运行 `scripts/daily_signal/install_watcher.sh` 安装本机监听器，文件稳定 60 秒后自动重建索引、提交并通过 SSH 推送到 Edison，再更新[公开报告库](https://vincentshuo.github.io/Edison/youtube/)。
- 索引与监听器移植自 [Daily Signal 78453f1](https://github.com/vincentshuo/daily-signal/tree/78453f125129c99be12c1b956dae64a88a1b2701)。报告原样发布，阅读与精选状态保存在当前浏览器。

## 下载

[Edison v0.2.1 — 首个桌面发行版](https://github.com/vincentshuo/Edison/releases/tag/v0.2.1) 面向 Apple Silicon、macOS 14 及以上系统。下载 DMG 后将 Edison 拖入 Applications，也可使用 ZIP 包；校验文件随版本提供。

此版本采用本地 ad-hoc 签名，未经 Apple 公证。macOS 可能要求在“系统设置 → 隐私与安全性”中确认打开。更新通过手动下载安装完成。

## 本地开发

```sh
uv sync --extra dev --extra messaging --extra bedrock --extra browser
cd surfaces/gui
npm ci
npm run tauri dev
```

macOS 客户端入口是 `surfaces/gui`。

## 本地应用包

```sh
bash packaging/build_local_macos.sh
```

生成并打开 `surfaces/gui/src-tauri/target/release/bundle/macos/Edison.app`。设置 `EDISON_OPEN_APP=0` 可只构建、不启动。发布版本同样使用此本地构建流程，不依赖上游自动更新服务。

## 验证

低频弹窗已统一焦点、关闭与可打断过渡；浏览器验收通过，原生窗口手感待验收。见 [实施记录](reports/modal-polish-2026-09-21/verification.md)。

```sh
uv run pytest
npm --prefix surfaces/gui test
npm --prefix surfaces/gui run build
```
