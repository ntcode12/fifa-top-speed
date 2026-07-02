import boto3
import pytest
from moto import mock_aws

from pipeline import storage


def test_bucket_name_env_override(monkeypatch):
    monkeypatch.setenv("FIFA_BUCKET", "custom-bucket")
    assert storage.bucket_name() == "custom-bucket"
    monkeypatch.delenv("FIFA_BUCKET")
    assert storage.bucket_name() == "fifa-topspeed-032968994565"


@pytest.fixture
def s3_bucket(monkeypatch):
    monkeypatch.setenv("FIFA_BUCKET", "test-bucket")
    with mock_aws():
        boto3.client("s3", region_name="us-east-1").create_bucket(Bucket="test-bucket")
        yield


def test_roundtrip_and_exists(s3_bucket):
    assert not storage.object_exists("raw/pdfs/x.pdf")
    storage.upload_bytes("raw/pdfs/x.pdf", b"hello")
    assert storage.object_exists("raw/pdfs/x.pdf")
    assert storage.download_bytes("raw/pdfs/x.pdf") == b"hello"
    assert storage.list_keys("raw/pdfs/") == ["raw/pdfs/x.pdf"]
    assert storage.list_keys("curated/") == []
