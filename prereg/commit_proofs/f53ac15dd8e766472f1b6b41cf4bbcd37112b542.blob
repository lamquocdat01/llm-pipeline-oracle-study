"""Bộ oracle DECISION của pipeline 2 (PREREG_V2 §5): decision lần chạy này == decision golden.

Chỉ chạy khi runner đặt P2_ORACLE_RUN + P2_ORACLE_GOLDEN (task p2_oracle); không thì skip cả module.
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from p2.oracle import ENV_GOLDEN, ENV_RUN, doc_obs  # noqa: E402

if not (os.environ.get(ENV_RUN) and os.environ.get(ENV_GOLDEN)):
    pytest.skip("không phải lần chạy oracle", allow_module_level=True)

RUN, GOLDEN = doc_obs(os.environ[ENV_RUN]), doc_obs(os.environ[ENV_GOLDEN])


@pytest.mark.parametrize("key", sorted(GOLDEN))
def test_decision(key):
    assert key in RUN, "thiếu đầu ra lần này"
    assert RUN[key]["decision"] == GOLDEN[key]["decision"]
