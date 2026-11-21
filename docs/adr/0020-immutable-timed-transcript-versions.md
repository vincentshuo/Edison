# ADR 0020: Immutable timed transcript versions and source trace

**Status: accepted.** Edison models every acquired timed transcript as an immutable version made of ordered cues. A version is identified by the video identity, source kind, language, provider configuration version and content digest; identical reacquisition reuses it, while changed content or source configuration creates a new version.

The knowledge asset selects one eligible version using the deterministic precedence `native > auto > asr_generated`. Selection changes only the asset's pointer. Translations, complete translations and manuscripts retain the transcript version used when they were generated, so a later caption improvement cannot silently change their source meaning.

Provider cue text and integer millisecond timing are retained as source data. Normalized text is a separate derived representation. SQLite stores identities, provenance, selection, cue metadata and queryable text; provider-specific ASR responses and other large raw payloads remain immutable retained files linked to their attempts and transcript versions.

An ASR result becomes usable only after completion and basic integrity/coverage checks. Partial output remains an attempt artifact and cannot enter translation or manuscript generation. Source trace maps each translation/manuscript block to cue ordinals and time ranges when reliable alignment exists; unknown alignment is recorded explicitly rather than guessed. Explicit deletion removes all versions, attempts, raw artifacts and traces for the knowledge asset; retries and regeneration preserve prior versions.

This keeps source evidence auditable and makes provider changes additive at the cost of retaining more historical material and requiring explicit regeneration when a newer source is desired.
