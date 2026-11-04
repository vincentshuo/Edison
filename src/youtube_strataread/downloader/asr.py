"""Speech-to-text adapters used when YouTube has no speech captions."""

from __future__ import annotations

import json
import os
import time
from dataclasses import dataclass
from typing import Any, Protocol

import httpx

from youtube_strataread.downloader.youtube import YouTubeError


class ASRError(YouTubeError):
    """A classified failure from the speech recognition capability."""

    def __init__(self, message: str, *, kind: str = "fatal", retry_after: float | None = None) -> None:
        super().__init__(message)
        self.kind = kind
        self.retry_after = retry_after


@dataclass(frozen=True)
class ASRResult:
    video_id: str
    language: str
    srt_text: str
    provider: str = "volcengine"
    model: str = "doubao-voice-recognition-2.0"
    task_id: str | None = None
    duration_seconds: float | None = None
    usage_seconds: float | None = None
    cost: float | None = None


class AudioTranscriptionProvider(Protocol):
    def transcribe(
        self,
        *,
        video_id: str,
        video_url: str,
        duration_seconds: float | None,
        language_hint: str | None,
    ) -> ASRResult: ...


def _ms(value: Any) -> int:
    if isinstance(value, bool):
        raise ValueError("boolean timestamp")
    number = float(value)
    # Volcengine file-recognition utterance offsets are milliseconds. Keeping
    # this conversion explicit avoids turning a 1500 ms cue into 25 minutes.
    return max(0, int(round(number)))


def utterances_to_srt(utterances: list[dict[str, Any]]) -> str:
    """Normalize provider utterances into the durable SRT interchange format."""
    lines: list[str] = []
    for ordinal, item in enumerate(utterances, 1):
        text = str(item.get("text") or item.get("utterance") or "").strip()
        if not text:
            continue
        start = _ms(item.get("start_time", item.get("start_ms", item.get("start", 0))))
        end = _ms(item.get("end_time", item.get("end_ms", item.get("end", start + 1))))
        if end <= start:
            raise ASRError("ASR cue has non-positive duration", kind="fatal")
        def stamp(ms: int) -> str:
            hours, remainder = divmod(ms, 3_600_000)
            minutes, remainder = divmod(remainder, 60_000)
            seconds, millis = divmod(remainder, 1_000)
            return f"{hours:02d}:{minutes:02d}:{seconds:02d},{millis:03d}"
        lines.extend((str(ordinal), f"{stamp(start)} --> {stamp(end)}", text, ""))
    if not lines:
        raise ASRError("ASR returned no usable speech cues", kind="fatal")
    return "\n".join(lines)


class VolcengineASRProvider:
    """Small synchronous adapter for the Volcengine async file-recognition API.

    The media URL and API paths are configuration, so tests and deployments can
    provide their own controlled audio service without putting YouTube cookies
    into the Provider request.
    """

    provider_name = "volcengine"

    def __init__(
        self,
        *,
        access_token: str | None = None,
        submit_url: str | None = None,
        query_url: str | None = None,
        audio_url_factory: Any | None = None,
        client: httpx.Client | None = None,
        poll_interval: float = 5.0,
        timeout_seconds: float = 30.0,
        max_polls: int = 120,
    ) -> None:
        self.access_token = access_token or os.environ.get("VOLCENGINE_ASR_TOKEN")
        self.submit_url = submit_url or os.environ.get("VOLCENGINE_ASR_SUBMIT_URL")
        self.query_url = query_url or os.environ.get("VOLCENGINE_ASR_QUERY_URL")
        self.audio_url_factory = audio_url_factory
        self.client = client or httpx.Client(timeout=timeout_seconds)
        self.poll_interval = poll_interval
        self.max_polls = max_polls

    def _headers(self) -> dict[str, str]:
        if not self.access_token:
            raise ASRError("ASR Provider 未配置火山访问凭据", kind="fatal")
        return {"Authorization": f"Bearer {self.access_token}", "Content-Type": "application/json"}

    def transcribe(self, *, video_id: str, video_url: str, duration_seconds: float | None,
                   language_hint: str | None) -> ASRResult:
        if not self.submit_url or not self.query_url:
            raise ASRError("ASR Provider 未配置火山任务接口", kind="fatal")
        if self.audio_url_factory is None:
            raise ASRError("ASR 未配置身份匹配的音频来源", kind="fatal")
        audio_url = self.audio_url_factory(video_id, video_url)
        payload = {"audio_url": audio_url, "language": language_hint,
                   "model": "doubao-voice-recognition-2.0",
                   "metadata": {"video_id": video_id}}
        try:
            response = self.client.post(self.submit_url, headers=self._headers(), json=payload)
            response.raise_for_status()
            submitted = response.json()
            task_id = str(submitted.get("task_id") or submitted.get("id") or "")
            if not task_id:
                raise ASRError("火山 ASR 未返回任务标识", kind="fatal")
            for _ in range(self.max_polls):
                result = self.client.get(self.query_url.format(task_id=task_id), headers=self._headers())
                result.raise_for_status()
                body = result.json()
                status = str(body.get("status") or body.get("state") or "").lower()
                if status in {"failed", "error", "cancelled", "canceled"}:
                    raise ASRError(str(body.get("message") or "火山 ASR 任务失败"), kind="fatal")
                if status in {"succeeded", "success", "completed", "done", "ready"}:
                    cues = body.get("utterances") or body.get("result", {}).get("utterances") or []
                    language = str(body.get("language") or body.get("result", {}).get("language") or language_hint or "und")
                    return ASRResult(video_id, language, utterances_to_srt(cues), task_id=task_id,
                                     duration_seconds=duration_seconds, usage_seconds=duration_seconds)
                time.sleep(self.poll_interval)
            raise ASRError("火山 ASR 远端任务状态确认超时", kind="transient")
        except ASRError:
            raise
        except httpx.HTTPStatusError as error:
            status = error.response.status_code
            kind = "transient" if status in {408, 425, 429, 500, 502, 503, 504} else "fatal"
            raise ASRError(f"火山 ASR HTTP {status}", kind=kind) from error
        except (httpx.TimeoutException, httpx.NetworkError) as error:
            raise ASRError("火山 ASR 网络暂时不可用", kind="transient") from error
        except (ValueError, KeyError, json.JSONDecodeError) as error:
            raise ASRError("火山 ASR 返回结果无法解析", kind="fatal") from error

