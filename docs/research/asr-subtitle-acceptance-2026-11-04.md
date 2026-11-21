# ASR 与字幕质量验收研究（2026-11-04）

## 结论

原生字幕与 ASR 生成字幕应共享一套**最终可用性验收标准**：语言/内容覆盖、词语准确度、时间轴单调且与语音同步、分句可读性、可追溯性，以及长音频任务的完成率、延迟和成本。这样下游翻译、稿件和 `Timed transcript` 只依赖一个稳定契约。

两类来源不能共享全部**前置质量门槛**。原生字幕首先验收来源身份、语言、文件格式和 cue 时间轴完整性；ASR 还必须验收音频确实属于目标视频、提供商/模型/配置可重放、任务完成而非部分输出、音频可解码且覆盖目标时长。ASR 通过前置门槛后，才与原生字幕进入同一最终验收器；来源字段仍须保留，不能把 ASR 伪装成原生字幕。

## 可量化的共同验收维度

- **文字准确度**：以人工参考转录计算 WER（word error rate）和 CER（character error rate）。NIST SCTK 的 `sclite`/`asclite` 是一手评分工具，支持参考与识别文本对齐及统计显著性比较；阈值应按语言、领域和使用目的设定，不能把某个模型或来源的宣传数字直接当产品门槛。来源：[NIST SCTK README](https://github.com/usnistgov/SCTK/blob/master/README.md)。
- **时间轴**：对参考词/句边界计算 start/end 的绝对误差（建议报告 P50/P95）、重叠率/IoU，以及无语音区间的误触发。最终验收至少要求 cue 按时间单调、`end > start`、不越过音频边界、文本与对应语音有重叠；内部保留 provider 时间精度。Whisper 论文说明其时间戳 token 以约 20 ms 量化，因此 20 ms 是模型原生分辨率，不是所有字幕产品都应承诺的用户级误差阈值。[Whisper 论文 §2.3](https://arxiv.org/html/2212.04356)。
- **分句与可读性**：验收 cue 时长、每 cue 字符/词数、阅读速度（CPS/WPM）、标点和断句，避免只优化 WER 而生成不可读字幕。Netflix 的 Timed Text Style Guide 给出字符/行数、阅读速度、分行和时间重叠等发布前规则；这些是 Netflix 交付格式的来源特有门槛，不能直接宣称为通用 ASR 标准。[Netflix English Timed Text Style Guide](https://partnerhelp.netflixstudios.com/hc/en-us/articles/217350977-English-USA-Timed-Text-Style-Guide)。
- **覆盖与完整性**：报告参考语音时长、有效语音区间覆盖率、空 cue/重复 cue、首尾截断和未对齐片段比例。只有任务完成且达到覆盖/完整性门槛的 ASR 结果可成为 `asr_generated` transcript；部分结果保留为 attempt，不进入下游。

## 长音频性能与成本

Whisper 原论文明确指出模型一次只能接收 30 秒音频；长音频依赖按时间窗连续转写、依据时间戳移动窗口，并需要 beam search、temperature scheduling 等策略。错误时间戳会影响后续窗口。因此验收必须包含长音频专项集，而不能只用短句 WER；至少记录整段完成率、跨窗口重复/遗漏、时间轴漂移、端到端 wall-clock latency、实时率（处理秒数/音频秒数）、重试率和峰值内存。[Whisper §3.8、§4.5](https://arxiv.org/html/2212.04356)。

成本应按音频分钟和成功任务计量：`provider/API 成本 + 下载/转码/存储成本`，同时记录失败重试造成的重复费用。对自托管模型记录 GPU/CPU 时间、并发度和能耗代理指标。不要用单次平均延迟替代 P95，也不要把“任务排队时间”与模型推理时间混为一项。

## 来源特有的前置质量门槛

| 来源 | 进入共同验收器前的必要检查 |
|---|---|
| 原生/平台字幕 | 视频身份与语言匹配；字幕响应可解析；cue 序号稳定、时间轴单调且在视频时长内；确认不是仅标题/章节/评论等非语音轨；保留平台 track 与获取时间。|
| ASR 生成字幕 | 音频身份与视频 ID/URL 绑定并可审计；音频完整可解码；记录 provider、模型、版本、参数和语言提示；任务状态为 completed；覆盖率、首尾边界和重复/遗漏检查通过；保存原始响应与配置 digest。|

平台字幕可能已经经过平台人工或自动处理，但“原生”不等于准确或完整，仍须走共同验收。ASR 的模型置信度可用于筛查和抽样复核，不能替代 WER/CER 或时间轴验收。

## 对 Edison 的决策建议

1. 将最终验收器定义在 `TranscriptVersion` 层，输入统一的 cue 序列和可选参考标注，输出准确度、时间轴、可读性、覆盖和性能指标。
2. 在来源适配器内部执行前置门槛，并把失败原因区分为 `source_invalid`、`asr_incomplete`、`quality_rejected`；不要用通用“无字幕”覆盖 ASR 失败。
3. 继续保留 `native > auto > asr_generated` 的来源选择优先级，但只有通过共同验收的版本才具备 downstream eligibility；版本、provider 配置和指标应可重放、可审计。
4. 建立短句、多人说话、口音/噪声、静音、跨 30 秒边界和 30–120 分钟长视频的固定验收集，并按语言分别设定 WER/CER 与时间误差阈值。

## 参考的一手来源

- NIST Speech Recognition Scoring Toolkit (SCTK)：<https://github.com/usnistgov/SCTK>
- Radford et al., *Robust Speech Recognition via Large-Scale Weak Supervision*（Whisper）：<https://arxiv.org/abs/2212.04356>
- OpenAI Whisper 实现与模型说明：<https://github.com/openai/whisper>
- Netflix Studio Timed Text Style Guide（英语）：<https://partnerhelp.netflixstudios.com/hc/en-us/articles/217350977-English-USA-Timed-Text-Style-Guide>
- AWS Transcribe subtitles 文档（供应商输出约束示例）：<https://docs.aws.amazon.com/transcribe/latest/dg/subtitles.html>
- Microsoft Speech recognition results（词级/短语级 offset 示例）：<https://learn.microsoft.com/en-us/azure/ai-services/speech-service/get-speech-recognition-results>
