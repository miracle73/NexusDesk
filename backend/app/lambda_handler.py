"""AWS Lambda Function URL entrypoint (no API Gateway)."""
import logging

from mangum import Mangum

from app.main import app

logging.getLogger().setLevel(logging.WARNING)

handler = Mangum(app, lifespan="off")
