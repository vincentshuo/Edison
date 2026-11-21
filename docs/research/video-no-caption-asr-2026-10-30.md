# 无原生字幕视频的插件实现调查（2026-10-30）

## 结论

Trancy 和沉浸式翻译处理“无 YouTube 原生字幕”的核心都不是继续等待 YouTube caption track，而是增加一条独立的 **URL → 服务端取音频 → ASR → 带时间轴字幕 → 浏览器注入 → 翻译** 路径。Edison 当前的 `yt-dlp` 下载器只检查 `subtitles` / `automatic_captions`，没有音频转写分支，因此会把这类视频停在 `waiting_retry` 或判为不可用。

两者的产品形态不同：Trancy 公开说明它使用 OpenAI Whisper，把 YouTube 音频异步转成字幕；沉浸式翻译公开源码显示它把当前页面 URL 发给自己的 `asr-audio/v2/create-task`，轮询任务并拿回字幕结果，然后复用既有的字幕显示和翻译注入代码。沉浸式翻译的 ASR 服务端实现没有在公开仓库中披露，不能把它表述成“浏览器本地 Whisper”。

## Trancy：官方资料能确认的链路

Trancy 的 AI Subtitles 页面明确写道：

> Trancy uses OpenAI's Whisper speech-to-text service to asynchronously convert YouTube audio into subtitles.

它还说明 AI 字幕相对 YouTube 机器字幕改进了分句，处理时间约 2–5 分钟；用户点击播放器控制栏的 AI subtitle 图标后，视频进入 AI 处理队列，完成后原字幕会被新字幕替换。官方页面称该功能属于 Premium，并宣传每月最高 1,000 分钟高质量 AI 视频翻译。

这解释了“没有原生字幕也能用”：插件不依赖 YouTube 的 `captionTracks`，而是把视频 URL/音频交给异步 ASR 任务。由于官方页面只说明“转换 YouTube audio”，没有说明浏览器端如何取得媒体流或服务端具体下载方式，不能据此断言它一定使用某个具体下载器；可以确认的是 ASR 在 Whisper 服务上、结果是异步生成、字幕完成后再替换播放器中的字幕。

官方证据：

- Trancy AI Subtitles：<https://www.trancy.org/ai-subtitle>
- Trancy 首页的产品描述：<https://www.trancy.org/>
- Trancy 更新日志（YouTube 字幕控制、AI 字幕相关功能）：<https://www.trancy.org/changelog>
- Whisper 说明链接（Trancy 页面上的 “Power by Whisper”）：<https://openai.com/research/whisper>

## 沉浸式翻译：公开源码能确认的链路

公开仓库：<https://github.com/immersive-translate/immersive-translate>，本次核对提交为 `2ff98f3e748d`（2026-10-23 更新 dist）。仓库发布的构建产物位于 `dist/chrome/content_main.js` 和 `dist/chrome/video-subtitle/inject.js`。

### 1. 普通字幕路径仍然只读已有字幕

YouTube 适配器从 YouTube 播放器响应中读取 `timedtexttracks` / `captionTracks`，记录字幕 URL；`loadSubtitle()` 随后请求原字幕，优先人工字幕或 YouTube 翻译字幕，再交给字幕合并、翻译和注入逻辑。这条路径本身不能解决没有字幕的视频。

对应源码位置（构建文件中的函数名）：

- `YouTubeSubtitle.loadSubtitle`
- `requestOriginalEvents`
- `requestOriginalSubtitle`
- `requestHumanSubtitle`
- `requestYoutubeTranslateSubtitle`

### 2. “无字幕”按钮启动独立的 AI 字幕任务

同一个 YouTube 适配器在无字幕时显示“当前视频无字幕，可尝试请求 AI 字幕”，并提供 `Request AI subtitles (Beta)`。AI 任务类 `y4` 的关键调用是：

```text
GET  asr-audio/v2/subtitle?url=<encoded page URL>       # 查服务端缓存
POST asr-audio/v2/create-task { url: <page URL> }        # 创建任务
GET  asr-audio/v2/task/<task_id>                         # 每 5 秒轮询
```

代码中的 `createNormalTask()` 只提交页面 URL，并没有把浏览器端提取出的音频 blob 上传到接口。完成后 `pollTaskStatus()` 读取服务端结果，`tH()` / `nH()` 将返回内容解析成字幕 items 或结构化结果；`handleAttachAiSubtitle()` 将这些 items 转成带 `start` / `end` / `text` 的字幕并调用通用 `attachSubtitle()`。

这证明沉浸式翻译采用“URL 任务 + 服务端 ASR + 客户端轮询”的架构。公开客户端代码没有披露 `asr-audio` 服务如何抓取 YouTube 音频、使用哪一个 ASR 模型或其内部切片策略，因此这些部分应在 Edison 设计中作为外部服务适配器，而不是假设为浏览器本地推理。

### 3. ASR 结果仍进入原有双语字幕管线

AI 字幕完成后，插件会：

1. 校验字幕 item 的时间轴和文本长度；
2. 用语言检测确定源语言；
3. 调用通用 `attachSubtitle(items, language, isAiSubtitle=true)`；
4. 沿用原有双语/仅译文显示、翻译服务、播放器注入和下载逻辑。

因此它不是“另一套翻译 UI”，而是先把 ASR 输出规范化成与原生字幕相同的中间表示，再复用普通字幕渲染器。

### 4. 服务端缓存、额度和时长限制是产品关键

客户端先查 URL 缓存；若已有结果，直接挂载。否则创建任务并显示预计时间。代码还检查登录、会员/试用额度和最大视频时长；构建产物的中文文案明确写出 Pro 每月最高 1,000 分钟，AI 字幕当前支持不超过配置的小时数。AI 结果还会根据 URL 在服务端缓存，使后续用户可以直接使用已生成的字幕。

官方/一手证据：

- 代码仓库：<https://github.com/immersive-translate/immersive-translate>
- 固定版本构建文件：<https://github.com/immersive-translate/immersive-translate/blob/2ff98f3e748d/dist/chrome/content_main.js>
- 视频字幕注入器：<https://github.com/immersive-translate/immersive-translate/blob/2ff98f3e748d/dist/chrome/video-subtitle/inject.js>
- 仓库 README 的产品范围（在线视频双语字幕）：<https://github.com/immersive-translate/immersive-translate/blob/2ff98f3e748d/README.md>

## 对 Edison 的直接启示

### 现状差距

Edison 的 `src/youtube_strataread/downloader/youtube.py` 只执行：探测视频信息 → 从 `subtitles` / `automatic_captions` 选语言 → 下载 SRT。`speech_only=True` 还会明确排除 `live_chat`。当两个字幕字典都为空时，代码抛出“暂无可用字幕，未处理”或“no subtitles ... available”，重试策略只能再次探测同一个事实，永远不会产生新字幕。

### 建议的最小可行架构

新增 `AudioTranscriptionProvider`，把它作为 caption provider 的第二条策略：

```text
YouTube metadata
  ├─ native/auto captions available → existing yt-dlp caption path
  └─ no usable captions
       → ASR task provider(url, duration, language hint)
          → pending(task_id, retry_at)
          → timed transcript (same internal cue schema)
          → existing normalization / translation / manuscript pipeline
```

必须保留来源类型，例如 `native_caption`、`auto_caption`、`asr_generated`，并把 ASR 结果与原始字幕一样持久化、可重放、可审计。`waiting_retry` 需要区分“字幕尚未发布”和“ASR 任务处理中”；后者不是重复请求 YouTube，而是轮询任务状态。

### 不应直接照搬的部分

- 不要把“无字幕”任务伪装成原生字幕；UI 和数据模型应标明 `asr_generated`。
- 不要在客户端假设可以安全取得任意 YouTube 音频 URL；应由服务端/受控下载器完成 URL 解析和音频获取，并记录权限、限额、失败原因。
- 不要把 ASR 结果直接送进翻译而丢失时间轴。插件的稳定性来自统一的 timed-cue 中间表示。
- 不要无限轮询。需要任务 TTL、视频最大时长、单账号分钟配额、重试退避和幂等任务键（至少 URL/video ID + ASR 配置哈希）。

### 推荐的实施顺序

1. 先定义 `CaptionSource` / `TranscriptCue` 的来源字段和状态机，加入 `asr_pending`、`asr_failed`、`asr_ready`。
2. 用一个受控 ASR 服务适配器做端到端试验：输入 YouTube URL，输出带时间轴 JSON/SRT；先不绑定某一家模型。
3. 在 `download_subtitles()` 之后增加 fallback，但只在“确实没有 speech captions”时触发，不能覆盖权限、私有视频、地区限制等不可恢复错误。
4. 复用现有 `normalize_captions`、翻译和稿件流程；增加 ASR 与原生字幕的质量对照实验（词错率、分句、时间轴漂移、长视频成本）。
5. 最后再决定是托管 ASR、用户自带 API key，还是本地 Whisper；这取决于隐私、成本、YouTube 获取稳定性和桌面端资源，而不是由插件表面 UI 决定。

## 证据边界

Trancy 的 Whisper、异步 2–5 分钟、队列和 Premium 限制来自其官方产品页。沉浸式翻译的客户端任务接口、轮询、缓存、无字幕入口和注入方式来自其公开构建源码。两家服务端实际如何下载媒体、切片、选择 Whisper 模型、做说话人分离或后处理，公开资料没有给出；这些应标为待验证项，不能当成已确认事实。
