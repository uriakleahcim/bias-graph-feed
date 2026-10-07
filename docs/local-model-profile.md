# Local Model Profile

## Current policy

Bias Graph Feed consumes a shared Ollama service over its configured `OLLAMA_HOST`.
In the Sandbox Protocol deployment, that service owns the model cache at
`/home/uriak/sandbox/groups/agent-models/ollama`, mounted as `/root/.ollama`
inside the Ollama container. Bias Graph Feed does not mount, write, or otherwise
own that directory.

The fixed profile is intentionally capped at 3B parameters:

| Role | Model | Reason |
| --- | --- | --- |
| Quality summaries and deep reports | `qwen2.5:3b-instruct` | Highest quality permitted by the current low-memory policy. |
| Mechanical grouping, topics, headlines, and bias | `qwen2.5:1.5b-instruct` | Reduces the cost of the high-volume fast tier. |
| Story embeddings | `nomic-embed-text:v1.5` | Text embedding model used by pgvector grouping. |

The Ollama container permits one concurrent request and one loaded model. That
is a deliberate responsiveness safeguard, not an automatic hardware benchmark.

## Initial pull and persistence

The shared `ollama` Sandbox target starts a short-lived `ollama-model-init`
container before making the endpoint available to consumers. It pulls all three
pinned model names into the shared cache. Later starts reuse the same blobs and
the initializer becomes a fast availability check. A model pull therefore does
not create or require a path in the user home directory.

## Future adaptive profile

Dynamic model selection is deferred. A future implementation must measure
available RAM, a working GPU driver, usable VRAM, inference latency, and
thermal state before selecting a profile. It must never silently change the
embedding model for an existing corpus: differing vector spaces require an
explicit re-embedding operation and compatible database dimensions.
