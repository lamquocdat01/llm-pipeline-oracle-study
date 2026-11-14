# FROZEN — script phân tích v2 đóng băng trước lần đọc thật đầu tiên (V2-05 D2)

- Commit script + test: `4dbaaeb3a90492256c2f300c2f04a6aad54c66d0` (12-11-2026 13:02 +07).
- Trước commit này: chỉ đọc mã, schema (tên trường, kiểu), cột `task_id`/`status`/`ts`; chạy trên dữ liệu giả `tests/fake.py`. Chưa đọc decision/artefact/kết quả suite thật của ô nào. (Lúc xem schema obs_lan01, một mục golden lọt ra màn hình: decision/artefact classify của 1 câu ở lần golden — không phải dữ liệu đổi/không đổi.)
- Khoá dữ liệu: `study/pipeline2/results/SHA256SUMS_N2N3.txt` (commit `7256ef9`, tag `data-freeze-md`).
- Venv: `requirements.txt` (Python 3.11.9). Seed bootstrap: 20261112…20261116, B = 2 000.
- Mọi sửa script sau mốc này = commit mới, ghi lý do ở đây (Việc 3).

## sha256 các file tại 4dbaaeb
```
fe6f750450e9662a20ccc8450d6c6458e40eb19a2f4e071f2af19dbf170c774d  study/analysis_v2/README.md
01ba4719c80b6fe911b091a7c05124b64eeece964e09c058ef8f9805daca546b  study/analysis_v2/av2/__init__.py
05374401929b96d8d039981c03541934c360f28677ef92704c78da39bcf3eb60  study/analysis_v2/av2/analysis.py
29b4667d367772ca1c0540e180b19a5d1dc5bab8def6868709673f72d132fc46  study/analysis_v2/av2/cells.py
f6f0bb9bfd5d0ddbe0375682ad13bec17c1c20161dab9266bac1e161cdd246b7  study/analysis_v2/av2/load.py
9a4912c09f933d8de1455fd99781726f0acfb25d7c9b81a70d56baabde68bfae  study/analysis_v2/av2/logit.py
8b5a016b1d3ef8e046586daa4e478fdb0bd498c3225803aaf268bf86983e090b  study/analysis_v2/av2/oracle_an.py
2e739bc207ad77d3135913260c4b89ff63921098c0ba6cd5d2ab8f2cf6cd8985  study/analysis_v2/av2/stats.py
52a421b535b84a72488b4df7407da16c03b82c18238993a73184a1cd0a06c634  study/analysis_v2/av2/v11.py
93014d82ecf9b81d6a5659a75043ccaef1ed2c81078abc4e38416cf753c35ce9  study/analysis_v2/requirements.txt
a1e9312e42139c34d30e209a6fc7854f538757ee5507627e9ae52fa08dc4992f  study/analysis_v2/run_analysis.py
345b955b2e2bacc068791482a58e42655bf64530c38a250dd7f58bc1809737f4  study/analysis_v2/tests/fake.py
fac4c733797e751cc762d68f3311861b1604cf22c0ef0a547b37cfd257a3f884  study/analysis_v2/tests/test_invariants.py
```

## Sửa sau mốc đóng băng

| Commit | Lúc | Sửa gì | Lý do | Ảnh hưởng số chính |
|---|---|---|---|---|
| `94ac317` | 12-11 ~13:20 | Thêm `av2/hau_kiem.py` + khoá `hau_kiem` trong `numbers_v2.json` + 1 test | **Viết SAU khi xem kết quả lần chạy thật đầu tiên** (sha256 lần 1 `66d5e6a7…74fe`): ô oracle qwen generate đỏ theo cụm ở các lần liền nhau; cần mô tả cơ chế cho "Where the matrix was wrong". Nhãn HẬU KIỂM, không dùng cho kết luận H | Không: mọi khoá khác của `numbers_v2.json` phải trùng lần 1 (kiểm bằng so khoá, ghi ở REPORT) |

## Tái lập (Việc 3, C7h)

- Lần chạy chính (venv dev, mã `94ac317`): `numbers_v2.json` sha256 `64ec02b72ec7d50e0aefd09d836402338be4ed78fe2607505b9fe0c8a6362fcb`.
- Venv mới tạo từ `requirements.txt` (`pip freeze` khớp từng dòng), chạy lại toàn bộ: sha256 **trùng** `64ec02b7…2fcb`; 9 CSV trùng byte. Không có nguồn bất định cần sửa.
- Lần chạy đầu (mã `ec90149`, trước hậu kiểm): `66d5e6a7…74fe`; mọi khoá trùng lần chính trừ khoá `hau_kiem` mới thêm.
