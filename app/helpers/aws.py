import logging
from tempfile import SpooledTemporaryFile
from typing import IO, Optional, Union

import boto3
from botocore.exceptions import ClientError

from app.config import get_settings

logger = logging.getLogger(__name__)


async def upload_file(
    file: Union[SpooledTemporaryFile, IO],
    filename: str,
    content_type: Optional[str] = None,
    bucket: Optional[str] = None,
):
    settings = get_settings()

    s3_client = boto3.client("s3")
    if not bucket:
        bucket = settings.aws_media_bucket

    try:
        extra_args = {}
        if content_type:
            extra_args["ContentType"] = content_type
        s3_client.upload_fileobj(file, bucket, filename, ExtraArgs=extra_args)
    except ClientError as e:
        logging.error(e)
        raise e
