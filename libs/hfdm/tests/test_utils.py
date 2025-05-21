import os
from unittest import mock

from hfdm.utils import VariableProvider, VariableReplacer


def test_variable_provider_none():
    vp_test = VariableProvider("vp_test_id")
    value1 = vp_test.lookup("key1")

    assert vp_test.get_name() == "vp_test_id"
    assert value1 is None


def test_variable_provider_dict():
    kv = {
        "k1": "v1",
        "k2": "v2",
    }

    vp_test = VariableProvider("vp_test_dict_id", kv_dict=kv)

    assert vp_test.get_name() == "vp_test_dict_id"
    assert vp_test.lookup("key1") is None
    assert vp_test.lookup("k1") == "v1"
    assert vp_test.lookup("k2") == "v2"


def test_variable_provider_lookup_fn():
    lookup_fn_dict = {
        "k1_fn": "v1_fn",
        "k2_fn": "v2_fn",
    }

    def lookup_fn(k):
        return lookup_fn_dict.get(k)

    vp_test = VariableProvider("vp_test_fn_id", lookup_fn=lookup_fn)

    assert vp_test.get_name() == "vp_test_fn_id"
    assert vp_test.lookup("key1") is None
    assert vp_test.lookup("k1") is None
    assert vp_test.lookup("k1_fn") == "v1_fn"
    assert vp_test.lookup("k2_fn") == "v2_fn"


def test_variable_provider_combined():
    kv = {
        "k1": "v1",
        "k2": "v2",
    }

    lookup_fn_dict = {
        "k1_fn": "v1_fn",
        "k2_fn": "v2_fn",
    }

    def lookup_fn(k):
        return lookup_fn_dict.get(k)

    vp_test = VariableProvider("vp_test_combined_id", kv_dict=kv, lookup_fn=lookup_fn)

    assert vp_test.get_name() == "vp_test_combined_id"
    assert vp_test.lookup("key1") is None
    assert vp_test.lookup("k1") == "v1"
    assert vp_test.lookup("k2") == "v2"
    assert vp_test.lookup("k1_fn") == "v1_fn"
    assert vp_test.lookup("k2_fn") == "v2_fn"


@mock.patch.dict(os.environ, {"K1": "env_v1"})
def test_variable_replacer():
    kv = {
        "k1": "ext_v1",
        "k2": "ext_v2",
    }

    vp_test = VariableProvider("ext", kv_dict=kv)

    vr = VariableReplacer([vp_test])

    assert vr.lookup("env", "k") is None
    assert vr.lookup("env", "k1") == "env_v1"
    assert vr.lookup("env", "k2") is None

    assert vr.lookup("ext", "k") is None
    assert vr.lookup("ext", "k1") == "ext_v1"
    assert vr.lookup("ext", "k2") == "ext_v2"
