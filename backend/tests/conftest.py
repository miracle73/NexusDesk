import os

import pytest

os.environ.setdefault("AWS_ACCESS_KEY_ID", "testing")
os.environ.setdefault("AWS_SECRET_ACCESS_KEY", "testing")
os.environ.setdefault("AWS_DEFAULT_REGION", "us-east-1")
os.environ.setdefault("DYNAMODB_TABLE", "nexusdesk-test")
os.environ.setdefault("UPLOADS_BUCKET", "nexusdesk-test-uploads")
os.environ.setdefault("JWT_SECRET", "test-secret")


@pytest.fixture
def aws_backend():
    """Mock DynamoDB + S3 and reset the cached boto3 clients around each test."""
    from moto import mock_aws

    from app.store import dynamo

    with mock_aws():
        dynamo._resource.cache_clear()
        dynamo.table.cache_clear()
        dynamo.s3.cache_clear()
        dynamo._resource().create_table(
            TableName=os.environ["DYNAMODB_TABLE"],
            BillingMode="PAY_PER_REQUEST",
            AttributeDefinitions=[
                {"AttributeName": "pk", "AttributeType": "S"},
                {"AttributeName": "sk", "AttributeType": "S"},
            ],
            KeySchema=[
                {"AttributeName": "pk", "KeyType": "HASH"},
                {"AttributeName": "sk", "KeyType": "RANGE"},
            ],
        )
        dynamo.s3().create_bucket(Bucket=os.environ["UPLOADS_BUCKET"])
        yield
        dynamo._resource.cache_clear()
        dynamo.table.cache_clear()
        dynamo.s3.cache_clear()
