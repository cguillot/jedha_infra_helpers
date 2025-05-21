from hfdm import (
    HuggingFaceAccount,
)


def test_hfdm_module():
    hf_account = HuggingFaceAccount("TEST-NAMESPACE", "TOKEN")
    assert hf_account is not None
