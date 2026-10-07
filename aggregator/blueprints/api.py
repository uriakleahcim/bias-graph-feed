"""Read-only data API for native dashboard clients.

The Flask/Jinja reader has deliberately been removed.  This blueprint is the
small stable boundary for a local client such as Omacale's Agent Bar: it
returns the edition and story data the old views displayed, but never scraped
article text, account data, or administration controls.
"""

from datetime import datetime, timedelta

from flask import Blueprint, abort, jsonify, request
from sqlalchemy import func
from sqlalchemy.orm import joinedload

from aggregator.article_signals import bias_bucket_for_score
from aggregator.models import Article, Edition, EditionStory, Story, Topic
from aggregator.story_view import annotate_edition_story_flags, apply_aggregator_filter


api = Blueprint("api", __name__, url_prefix="/api/v1")


def _iso(value):
    """Return an ISO 8601 UTC-compatible value, or null for an absent value."""
    return value.isoformat() + "Z" if value else None


def _bias_counts(story):
    counts = {"left": 0, "center": 0, "right": 0, "unrated": 0}
    for article in story.articles:
        score = article.outlet.bias_score if article.outlet else None
        bucket = bias_bucket_for_score(score)
        if bucket in ("left", "lean_left"):
            counts["left"] += 1
        elif bucket == "center":
            counts["center"] += 1
        elif bucket in ("lean_right", "right"):
            counts["right"] += 1
        else:
            counts["unrated"] += 1
    return counts


def _featured_image(story):
    return next((article.image_url for article in story.articles if article.image_url), None)


def _story_summary(story):
    return {
        "id": story.id,
        "headline": story.display_headline,
        # Editorial/personalized priority is not configurable yet. Expose the
        # stable baseline now so native clients can adopt the contract without
        # inferring a score from database-only ranking internals.
        "priority": 10,
        "summary": story.summary,
        "has_deep_report": bool(story.deep_report),
        "article_count": len(story.articles),
        "created_at": _iso(story.created_at),
        "updated_at": _iso(story.last_updated),
        "has_updates": bool(getattr(story, "edition_has_updates", False)),
        "bias": _bias_counts(story),
        "topics": [topic.name for topic in story.topics],
        "image_url": _featured_image(story),
    }


def _article_source(article):
    outlet = article.outlet
    score = outlet.bias_score if outlet else None
    return {
        "id": article.id,
        "title": article.title,
        "url": article.url,
        "published_at": _iso(article.date),
        "outlet": {
            "name": outlet.name if outlet else None,
            "url": outlet.url if outlet else None,
            "bias_score": score,
            "bias": bias_bucket_for_score(score),
            "bias_source": outlet.bias_source if outlet else None,
        },
    }


def _published_edition(edition_id=None):
    query = Edition.query.filter_by(published=True)
    if edition_id is not None:
        return query.filter_by(id=edition_id).first_or_404()
    return query.order_by(Edition.created_at.desc()).first()


def _edition_stories(edition, limit):
    if edition:
        rows = edition.edition_stories.order_by(EditionStory.rank).limit(limit).all()
        return annotate_edition_story_flags(rows)

    # A newly provisioned system does not have a published edition yet.  Keep
    # the Agent Bar useful with the same bounded fallback used by the old feed.
    cutoff = datetime.utcnow() - timedelta(days=1)
    return (
        Story.query.options(joinedload(Story.articles).joinedload(Article.outlet))
        .join(Article)
        .group_by(Story.id)
        .having(func.count(Article.id) > 1)
        .filter(Story.created_at >= cutoff, Story.headline_score > 0)
        .order_by(Story.headline_score.desc())
        .limit(limit)
        .all()
    )


def _limit(default=10, maximum=20):
    value = request.args.get("limit", default, type=int)
    if value is None or value < 1:
        abort(400, description="limit must be a positive integer")
    return min(value, maximum)


@api.after_request
def _no_store(response):
    response.headers["Cache-Control"] = "no-store"
    return response


@api.get("/health")
def health():
    return jsonify({"status": "ok", "service": "bias-graph-feed-api", "version": 1})


@api.get("/headlines")
def headlines():
    """Return the latest published edition, or a bounded recent-story fallback."""
    limit = _limit()
    edition = _published_edition()
    stories = _edition_stories(edition, limit)
    for story in stories:
        apply_aggregator_filter(story)

    return jsonify(
        {
            "edition": (
                {
                    "id": edition.id,
                    "date": edition.date.isoformat(),
                    "type": edition.edition_type,
                    "published_at": _iso(edition.created_at),
                }
                if edition
                else None
            ),
            "headlines": [_story_summary(story) for story in stories],
        }
    )


@api.get("/editions")
def editions():
    """List recent published editions for archive navigation."""
    limit = _limit(default=14, maximum=90)
    result = (
        Edition.query.filter_by(published=True)
        .order_by(Edition.created_at.desc())
        .limit(limit)
        .all()
    )
    return jsonify(
        {
            "editions": [
                {
                    "id": edition.id,
                    "date": edition.date.isoformat(),
                    "type": edition.edition_type,
                    "published_at": _iso(edition.created_at),
                }
                for edition in result
            ]
        }
    )


@api.get("/editions/<int:edition_id>/headlines")
def edition_headlines(edition_id):
    edition = _published_edition(edition_id)
    stories = _edition_stories(edition, _limit(default=20))
    for story in stories:
        apply_aggregator_filter(story)
    return jsonify(
        {
            "edition": {
                "id": edition.id,
                "date": edition.date.isoformat(),
                "type": edition.edition_type,
                "published_at": _iso(edition.created_at),
            },
            "headlines": [_story_summary(story) for story in stories],
        }
    )


@api.get("/stories/<int:story_id>")
def story(story_id):
    result = (
        Story.query.options(joinedload(Story.articles).joinedload(Article.outlet))
        .filter_by(id=story_id)
        .first_or_404()
    )
    apply_aggregator_filter(result)
    payload = _story_summary(result)
    payload.update(
        {
            "deep_report": result.deep_report,
            "sources": [_article_source(article) for article in result.display_articles],
            "scrape_quality": result.scrape_quality,
        }
    )
    return jsonify(payload)


@api.get("/topics")
def topics():
    result = Topic.query.filter_by(is_active=True).order_by(Topic.sort_order, Topic.name).all()
    return jsonify({"topics": [{"id": topic.id, "name": topic.name, "icon": topic.icon} for topic in result]})
