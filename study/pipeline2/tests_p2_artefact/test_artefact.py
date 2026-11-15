"""Bộ oracle ARTEFACT của pipeline 2 (PREREG_V2 §5): chuỗi chuẩn hoá lần này == golden.

Chuẩn hoá = `mrunner.oracle.chuan_hoa` (luật A04.3 của M6: lower, bỏ dấu câu Unicode, gộp khoảng trắng) —
cùng hàm, không chép, để biên p2 so được với biên Microduck.
"""
import os
import sys
from pathlib import Path

import pytest

sys.path.insert(0, str(Path(__file__).resolve().parents[1]))
from p2.oracle import ENV_GOLDEN, ENV_RUN, doc_obs  # noqa: E402
from mrunner.oracle import chuan_hoa  # noqa: E402

if not (os.environ.get(ENV_RUN) and os.environ.get(ENV_GOLDEN)):
    pytest.skip("không phải lần chạy oracle", allow_module_level=True)

RUN, GOLDEN = doc_obs(os.environ[ENV_RUN]), doc_obs(os.environ[ENV_GOLDEN])


@pytest.mark.parametrize("key", sorted(GOLDEN))
def test_artefact(key):
    assert key in RUN, "thiếu đầu ra lần này"
    assert chuan_hoa(RUN[key]["artefact"]) == chuan_hoa(GOLDEN[key]["artefact"])
