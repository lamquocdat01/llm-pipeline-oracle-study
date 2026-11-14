"""Verify prereg/commit_proofs: every object re-hashes to its name; every file chain resolves. Standard library only.

    python prereg/verify_commit_proofs.py
"""
import hashlib
import json
import sys
from pathlib import Path

D = Path(__file__).resolve().parent / "commit_proofs"


def h(kind: str, raw: bytes) -> str:
    return hashlib.sha1(kind.encode() + b" " + str(len(raw)).encode() + b"\0" + raw).hexdigest()


def entries(raw: bytes):
    i = 0
    while i < len(raw):
        sp = raw.index(b" ", i)
        nul = raw.index(b"\0", sp)
        yield raw[sp + 1:nul].decode("utf-8"), raw[nul + 1:nul + 21].hex()
        i = nul + 21


def main() -> int:
    bad = 0
    for f in sorted(D.iterdir()):
        if f.suffix in (".commit", ".tree", ".blob") and h(f.suffix[1:], f.read_bytes()) != f.stem:
            print("HASH MISMATCH", f.name)
            bad += 1
    for c in json.loads((D / "INDEX.json").read_text(encoding="utf-8")):
        raw = (D / (c["commit"] + ".commit")).read_bytes()
        tree = raw.split(b"\n", 1)[0].split()[1].decode()
        if tree != c["tree"]:
            print("TREE MISMATCH", c["commit"])
            bad += 1
        for f in c["files"]:
            cur = tree
            for name in f["path"].split("/"):
                hit = dict(entries((D / (cur + ".tree")).read_bytes())).get(name)
                if hit is None:
                    print("PATH BREAK", c["commit"][:7], f["path"])
                    bad += 1
                    break
                cur = hit
            else:
                if cur != f["blob"]:
                    print("BLOB MISMATCH", c["commit"][:7], f["path"])
                    bad += 1
        print(c["commit"][:7], c["commit_time"], len(c["files"]), "files")
    print("OK" if bad == 0 else f"{bad} problems")
    return 1 if bad else 0


if __name__ == "__main__":
    sys.exit(main())
