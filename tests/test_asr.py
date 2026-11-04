from __future__ import annotations

from dataclasses import dataclass

import httpx
from shorts_fixture import RegularVideos
from test_workbench_library import FakeManuscripts, candidate
from translation_fixture import EchoModel

from coworker.server.youtube import HostManuscripts
from youtube_strataread.downloader.asr import ASRError, ASRResult, VolcengineASRProvider
from youtube_strataread.downloader.youtube import CaptionsUnavailable
from youtube_strataread.workbench.library import PreparationService
from youtube_strataread.workbench.workspace import LocalWorkspace


@dataclass
class MissingCaptions:
    def acquire(self, url: str):
        raise CaptionsUnavailable("暂无可用字幕，未处理")


@dataclass
class FakeASR:
    result: ASRResult | Exception

    def transcribe(self, **kwargs):
        if isinstance(self.result, Exception):
            raise self.result
        return self.result


def test_new_task_falls_back_to_asr_and_reuses_translation_path(tmp_path):
    ws = LocalWorkspace.open(tmp_path)
    ws.set_meta("drain_paused", "0")
    ws.add_candidate(candidate("one"))
    service = PreparationService(
        ws,
        MissingCaptions(),
        HostManuscripts(type("Manager", (), {"model": "gemini", "provider_complete": EchoModel()})(), ws),
        shorts=RegularVideos(),
        asr=FakeASR(ASRResult("one", "en", "1\n00:00:00,000 --> 00:00:02,000\nhello\n", task_id="task-1")),
    )

    assert service.run_next()
    retained = ws.retained_transcript("one")
    assert retained["source"] == "asr_generated"
    assert retained["provider"] == "volcengine"
    assert retained["attempt_id"] == "task-1"
    assert ws.asset("one")["preparation_state"] == "ready"


def test_asr_transient_failure_uses_existing_bounded_retry_state(tmp_path):
    ws = LocalWorkspace.open(tmp_path)
    ws.set_meta("drain_paused", "0")
    ws.add_candidate(candidate("one"))
    service = PreparationService(
        ws, MissingCaptions(), FakeManuscripts("unused"), shorts=RegularVideos(),
        asr=FakeASR(ASRError("temporary", kind="transient")),
    )

    assert service.run_next()
    assert ws.asset("one")["preparation_state"] == "waiting_retry"
    assert "ASR 能力暂时不可用" in ws.asset("one")["failure_reason"]


def test_volcengine_adapter_polls_and_normalizes_utterances():
    calls = []

    def handler(request: httpx.Request) -> httpx.Response:
        calls.append(request.url.path)
        if request.method == "POST":
            return httpx.Response(200, json={"task_id": "t-1"})
        return httpx.Response(200, json={"status": "completed", "language": "en", "utterances": [
            {"start_time": 0, "end_time": 1500, "text": "Hello"},
        ]})

    provider = VolcengineASRProvider(
        access_token="secret", submit_url="https://asr.test/submit",
        query_url="https://asr.test/task/{task_id}", client=httpx.Client(transport=httpx.MockTransport(handler)),
        audio_url_factory=lambda _video_id, url: url,
        poll_interval=0,
    )
    result = provider.transcribe(video_id="one", video_url="https://audio.test/one", duration_seconds=2, language_hint="en")
    assert result.task_id == "t-1"
    assert "00:00:00,000 --> 00:00:01,500" in result.srt_text
    assert calls == ["/submit", "/task/t-1"]

