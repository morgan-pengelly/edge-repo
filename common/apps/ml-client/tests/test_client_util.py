"""Test Code for Client Utilities"""
from core.models.models import BlobType
import core.util.client_util as client_util


def test_build_blob_name():
    """Test Empty String"""
    name: str = client_util.build_blob_name(BlobType.EVENTVIDEO, "video.mp4")
    print(name)
    print("HELLO THIS IS A PRINT TEST!!!")
    assert len(name) >= 256
