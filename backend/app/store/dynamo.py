"""Single-table DynamoDB access. Every item is scoped by a tenant-prefixed key."""
from functools import lru_cache
from typing import Any

import boto3

from app.core.config import settings


@lru_cache
def _resource():
    kwargs: dict[str, Any] = {"region_name": settings.aws_region}
    if settings.dynamodb_endpoint_url:
        kwargs["endpoint_url"] = settings.dynamodb_endpoint_url
    return boto3.resource("dynamodb", **kwargs)


@lru_cache
def table():
    return _resource().Table(settings.dynamodb_table)


@lru_cache
def s3():
    return boto3.client("s3", region_name=settings.aws_region)


def put(item: dict) -> dict:
    table().put_item(Item={key: value for key, value in item.items() if value is not None})
    return item


def get(pk: str, sk: str) -> dict | None:
    return table().get_item(Key={"pk": pk, "sk": sk}).get("Item")


def query(pk: str, sk_prefix: str = "", limit: int | None = None) -> list[dict]:
    from boto3.dynamodb.conditions import Key

    condition = Key("pk").eq(pk)
    if sk_prefix:
        condition = condition & Key("sk").begins_with(sk_prefix)
    kwargs: dict[str, Any] = {"KeyConditionExpression": condition}
    if limit:
        kwargs["Limit"] = limit
    items: list[dict] = []
    while True:
        page = table().query(**kwargs)
        items.extend(page.get("Items", []))
        token = page.get("LastEvaluatedKey")
        if not token or (limit and len(items) >= limit):
            return items[:limit] if limit else items
        kwargs["ExclusiveStartKey"] = token


def update(pk: str, sk: str, values: dict) -> None:
    names = {f"#f{i}": key for i, key in enumerate(values)}
    attributes = {f":v{i}": value for i, value in enumerate(values.values())}
    expression = "SET " + ", ".join(f"{name} = :v{i}" for i, name in enumerate(names))
    table().update_item(
        Key={"pk": pk, "sk": sk},
        UpdateExpression=expression,
        ExpressionAttributeNames=names,
        ExpressionAttributeValues=attributes,
    )
