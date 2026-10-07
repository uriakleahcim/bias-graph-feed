# Sandbox Protocol Deployment

MuckScraper is deployed as one Compose target through Docker Sandbox Protocol.
The logical sandbox target is the API container named `muckscraper`; starting
it launches the API, scheduler, PostgreSQL, Meilisearch, and the internal
restart proxy. Local inference is supplied by the separate shared `ollama`
Sandbox target.

Persistent service data belongs under:

```text
/home/uriak/sandbox/groups/agent-services/muckscraper/
```

The active Sandbox declaration supplies this path as
`MUCKSCRAPER_RUNTIME_ROOT`. It contains PostgreSQL and Meilisearch data; none
of these directories belong in the source checkout. The shared Ollama cache is
instead owned by:

```text
/home/uriak/sandbox/groups/agent-models/ollama/
```

It is mounted only into the shared Ollama container as `/root/.ollama`.
Consumers, including MuckScraper, use the shared internal Docker-network
endpoint at `http://ollama:11434` rather than mounting the cache. The same
service is available to host-local clients at `http://127.0.0.1:11434`.

On this host, the declaration also supplies the Sandbox Protocol's selected
rootless Docker socket to the restart proxy. Do not override it with the
rootful `/var/run/docker.sock` unless the Sandbox Docker context is deliberately
changed too.

## Secret setup

Create the runtime-only secret file from
`docs/sandbox-secrets.env.example` at:

```text
/home/uriak/sandbox/groups/agent-services/muckscraper/config/secrets.env
```

Set it to mode `600`. Its `NEWS_API_KEY` and `GNEWS_API_KEY` entries are
references that map the saved provider credentials (`NEWSAPI_API_KEY` and
`GNEWS_API_KEY`) into MuckScraper's application names. API values are never
persisted in this runtime file.

The active Docker Sandbox Protocol declaration supplies the saved Aegis
credential file first through ordered `compose_env_files`, then loads this
wrapper file. Therefore `sandbox start muckscraper` needs no manual `export`.
Outside that declaration, export the provider variables before invoking Compose.
Startup fails closed if either value is absent rather than silently running only
RSS ingestion.

## Lifecycle

Database schema preparation and default pipeline seeding are an idempotent
`database-bootstrap` Compose lifecycle service. The API and scheduler wait for
that service to complete successfully; do not replace it with an ad-hoc
`docker compose exec` command. Future required MuckScraper setup work must be
added to the declared Compose/Sandbox lifecycle before it is relied on at
runtime.

Use the Sandbox command rather than direct Docker commands:

```bash
sandbox explain muckscraper
sandbox explain ollama
sandbox start ollama
sandbox start muckscraper
sandbox status
sandbox rebuild muckscraper
sandbox stop muckscraper
sandbox logs muckscraper
sandbox logs muckscraper app
sandbox in c muckscraper run smoke-test
```

Start `ollama` before `muckscraper`. On a first start, wait for the
`ollama-model-init` service to complete before relying on inference; later
starts reuse the cached model profile. `sandbox logs muckscraper` follows the
scheduler by default. Supply one of the declared service names to inspect that
service instead. `sandbox in c
muckscraper run smoke-test` is the declared MuckScraper command node for a
bounded profile: one scheduled topic, at most 10 NewsAPI and 5 GNews results,
no RSS feeds, and no targeted RSS enrichment. It still runs clustering,
headline generation, publication, and edition-content processing so the API
can be reviewed end to end.

For read-only direct Compose diagnostics, supply the Sandbox-owned runtime root
explicitly because direct Compose commands do not receive the environment that
Sandbox Protocol injects:

```bash
MUCKSCRAPER_RUNTIME_ROOT=/home/uriak/sandbox/groups/agent-services/muckscraper \
  docker compose \
  --env-file /home/uriak/sandbox/groups/agent-services/muckscraper/config/secrets.env \
  logs -f --tail=40 scheduler
```

The restart proxy remains internal. Its Docker socket must match the Docker
context selected by the Sandbox Protocol; validate that mount and the proxy's
allowlist after the first authorized launch.
