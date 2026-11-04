# ADR 0021: Single-provider ASR launch boundary

**Status: accepted.** The first ASR release handles only new preparation tasks and uses Volcengine Doubao Recording File Recognition 2.0 as its sole ASR Provider. Historical tasks and historical ASR attempts are outside this launch decision and are not migrated or replayed by it.

ASR acquisition and translation remain independent capabilities. A new task enters the Volcengine ASR path only after the YouTube content session has confirmed that no usable platform speech captions are available and the media layer has produced identity-matched, decodable audio. The existing Gemini Translation Provider continues to process an accepted `asr_generated` transcript; ASR configuration changes do not change the translation configuration or invalidate an existing translation by themselves.

Transient network errors, provider 5xx/429 responses, provider timeouts and local worker interruptions may receive bounded retries against the same Volcengine Provider, respecting provider retry guidance. Authentication/configuration errors, unsupported audio, identity mismatch, deterministic validation errors and user cancellation do not receive automatic retries. Exhausted quota, sustained provider unavailability or an unresolved remote state becomes an `ASR capability interruption`, preserving the task intent and source identity for later recovery.

Each retry is a new `ASR transcription attempt` with its own provider task identity, configuration digest, timestamps, outcome and diagnostics. A partial or failed attempt cannot enter translation. Edison records audio duration, provider usage when available, estimated or unknown cost, retry count and failure category; there is no hidden Provider fallback and ASR has an independent retry, duration and cost budget.

This keeps the launch contract small and auditable. Adding another ASR Provider later requires a separate decision and acceptance against the common transcript gate; it does not change the Gemini translation boundary.
