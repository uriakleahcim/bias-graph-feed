# Bias Graph Feed API

Bias Graph Feed is an API-only ingestion and story-clustering service. Its old
Flask/Jinja reader and administrative presentation layer have been removed;
the scheduler, models, migrations, PostgreSQL/pgvector mapping, and
Meilisearch integration remain unchanged.

The Docker Compose application port is intentionally published only on
`127.0.0.1:5000`.  Treat this loopback-only binding as the API's transport
boundary: the native dashboard must call the HTTP API, not the database.

## Read-only endpoints

All payloads are JSON and respond with `Cache-Control: no-store`.

| Endpoint | Purpose |
| --- | --- |
| `GET /api/v1/health` | Connectivity check. |
| `GET /api/v1/headlines?limit=10` | Latest published edition, or a bounded recent-story fallback before the first edition. |
| `GET /api/v1/editions?limit=14` | Published-edition archive index. |
| `GET /api/v1/editions/<id>/headlines?limit=20` | A historical edition's grouped stories. |
| `GET /api/v1/stories/<id>` | Executive summary, deep report, source links, bias labels, and scrape-quality disclosure. |
| `GET /api/v1/topics` | Active topic names for local filtering. |

Headline results cluster articles by story and include Left/Center/Right/
unrated counts.  Detail results intentionally contain outbound publisher URLs
but never an article's scraped full text, account data, pipeline controls, or
administrative mutation operations.

Each headline also carries an integer `priority`. The current baseline is
`10`; client presentation sorts higher values first, keeps `0` at the end of
the visible list, and suppresses negative values. A future editorial or
personalization capability may set a different value, but this read-only API
does not expose a mutation endpoint for that purpose.

## Client integration boundary

The Agent Bar can present compact headline cards from `/headlines` and open a
native detail popout from `/stories/<id>`.  It must show an unavailable or
empty state when this local service is absent; it must not imply that a topic
filter, refresh, rescrape, or LLM action has run.  Refresh and configuration
controls are not part of this API contract and require a separately designed,
authenticated integration.
