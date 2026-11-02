# ASR 部署研究：托管 Whisper 与自建 faster-whisper（2026-11-02）

## 问题边界

这份研究只比较“音频已经被 Edison 获取后，如何执行语音转写”。faster-whisper 本身不负责从 YouTube URL 取媒体；YouTube 内容会话、格式选择和音频临时文件仍需要 Edison 的独立媒体获取层。两种方案都应输出稳定的带时间轴 transcript cue，供现有翻译和成稿流程使用。

## 选项 A：外部托管转写 API

OpenAI 的 Speech-to-text 指南规定，录音文件通过 /v1/audio/transcriptions 上传；支持 mp3、mp4、mpeg、mpga、m4a、wav、webm，单文件上限 25 MB。官方示例展示 verbose_json 与 timestamp_granularities: ["word"]，因此可以构造 segment/word 时间轴；实际产品仍需把 word 时间轴合并为 Edison 的 cue。

当前官方文档推荐 gpt-transcribe 处理录音原语言。文档把 whisper-1、gpt-4o-transcribe、gpt-4o-mini-transcribe、gpt-4o-transcribe-diarize 和 /v1/audio/translations 标为已弃用，并写明计划于 2027-02-26 关闭；旧模型的字幕格式示例是兼容性文档。因此“托管 Whisper”不应在接口层硬编码为 whisper-1，应以 provider 配置选择模型，并允许切换当前推荐模型。

官方价格页当前列出录音转写的分钟价格：gpt-transcribe $0.0045/min、gpt-4o-mini-transcribe $0.003/min、gpt-4o-transcribe $0.006/min；价格会变化，规格中只能把它作为测算输入而不是永久常量。例如 60 分钟视频的纯转写费用约为 $0.18、$0.27 或 $0.36，还未计音频下载、重试和翻译费用。

### 托管方案的工程含义

- Edison 必须把音频传到外部服务，需在 UI/设置中明确外传边界，并由 Credential boundary 管理 API key。
- 25 MB 上限意味着长视频通常需要 Edison 先转码/切片，再提交多个请求；每个片段的时间轴需要加回全局偏移，并处理片段边界重复。
- API 返回 JSON/文本和时间戳，但异步队列、幂等、缓存、重试、服务限流仍应由 Edison 负责；“调用成功”不等于任务可恢复。
- 外部服务不需要用户服务器配备 GPU，部署最快，也能把模型升级和推理运维交给供应商；依赖供应商可用性、价格、模型生命周期和网络上传速度。

## 选项 B：Edison 服务器自建 faster-whisper

SYSTRAN 的官方仓库把 faster-whisper 定义为使用 CTranslate2 的 OpenAI Whisper 重实现，并宣称相同准确度下最高约 4 倍于 openai/whisper、占用更少内存，CPU/GPU 都可用 8-bit 量化。仓库要求 Python >=3.9；它用 PyAV 打包的 FFmpeg 库解码音频，因此不要求系统单独安装 FFmpeg。

官方 README 给出了可复现的资源参考：

- GPU（RTX 3070 Ti 8 GB，CUDA 12.4）：large-v2、fp16、beam 5，13 分钟音频约 1:03、4.5 GB VRAM；int8 约 0:59、2.9 GB VRAM；batch size 8 可到 17 秒但占约 6.1 GB VRAM。
- CPU（Intel i7-12700K，8 threads）：small、int8、beam 5，13 分钟约 1:42、1.5 GB RAM；batch size 8 约 0:51、3.6 GB RAM。
- GPU 运行需要 NVIDIA cuBLAS 和 cuDNN；当前 CTranslate2 版本对应 CUDA 12/cuDNN 9，其他 CUDA 组合需要锁定兼容版本。

API 直接返回 segment 起止时间和文本；word_timestamps=True 可返回 word 起止时间；内置 Silero VAD 可过滤无语音部分，默认只移除超过 2 秒的静音。README 还说明 segments 是惰性 generator，必须完整迭代才能真正执行转写，这对任务进度和取消语义很关键。

### 自建方案的工程含义

- 音频不会因为转写请求离开 Edison 所在服务器；但 YouTube 音频获取本身仍受内容会话和平台访问边界约束。
- 没有按分钟的第三方 API 费，但要承担模型下载、磁盘、CPU/GPU、并发队列、热模型驻留、驱动和安全更新。
- CPU 可以运行 small/int8，但长视频批处理时间可能占用共享实例；GPU 会提高吞吐，却引入 CUDA/cuDNN/显存兼容维护。
- 模型、compute type、beam size、VAD 参数和语言提示必须进入生成记录，否则同一视频无法解释为何得到不同字幕。
- faster-whisper 的 segment 输出天然适合 Edison 的 timed cue；word 时间戳可作为质量诊断或更细分句的输入，但不应直接把每个 word 当成阅读字幕。

## 对比矩阵

| 维度 | 外部托管转写 | 自建 faster-whisper |
|---|---|---|
| 首次接入速度 | 快；HTTP API | 慢；模型、运行时、资源探测 |
| 音频隐私 | 音频上传第三方 | 音频留在 Edison 服务器 |
| 直接费用 | 按分钟计费，且价格/模型会变 | 无按分钟费；承担机器和运维成本 |
| 长视频 | 受 25 MB 文件上限，需切片合并 | 可直接处理本地文件，但仍需任务超时和资源上限 |
| 时间轴 | verbose_json/word timestamps 可用 | segment/word timestamps 原生可用 |
| 伸缩 | 由供应商承担模型并发 | Edison 自己管理 worker 并发和队列 |
| 故障面 | 网络、认证、限流、模型弃用 | CPU/GPU、驱动、模型、进程和磁盘 |
| 模型迭代 | 供应商控制，可能发生弃用 | Edison 锁模型和运行时，可复现 |
| YouTube 获取 | 两者都需要 Edison 独立媒体层 | 两者都需要 Edison 独立媒体层 |

## 稳定 Provider 契约建议

无论最终选择哪一个部署方式，Provider 的输入输出应保持一致：

    TranscriptionRequest {
      video_id, source_url, local_audio_path,
      language_hint?, model_profile, idempotency_key
    }

    TranscriptionResult {
      source: "asr_generated",
      language, duration_seconds,
      cues: [{start_ms, end_ms, text, words?}],
      provider, model, model_revision,
      detected_language_probability?,
      raw_artifact_digest
    }

Provider 不应接收或持有 YouTube OAuth/浏览器 Cookie；媒体获取层生成受限生命周期的本地音频文件，再通过受控接口传入 Provider。任务层负责幂等、缓存、重试、取消和超时；Provider 只负责一次可观测的转写执行。

## 尚未由本研究决定的事项

1. Edison 部署是否有稳定 GPU；若没有，需要用 CPU small/int8 做基准，再决定托管或自建。
2. 用户是否接受音频离开自托管服务器；这是产品/隐私决策，不能从技术基准替代。
3. 托管路径选择哪一家当前模型，以及如何处理 25 MB 切片与时间轴拼接。
4. 自建路径的模型大小、并发数、最大视频时长、任务超时和资源配额。

## 一手来源

- OpenAI Speech-to-text 指南：<https://developers.openai.com/api/docs/guides/speech-to-text>
- OpenAI API 定价：<https://developers.openai.com/api/docs/pricing>
- SYSTRAN faster-whisper README（提交 9e472ae9de8bb374552f531f752654554b76b2d6）：<https://github.com/SYSTRAN/faster-whisper/tree/9e472ae9de8bb374552f531f752654554b76b2d6>
- OpenAI Whisper 原始仓库：<https://github.com/openai/whisper>
