#!/usr/bin/env python3
"""Host-only guard: compare an actually reconstructed staged DSA xmit with its test model.

Neither patch application to a kernel tree nor NSS/DSA boot is tested here.
"""
from pathlib import Path
import re
import sys

ROOT = Path(__file__).resolve().parents[1]
TAGGER = ROOT / "target/linux/generic/pending-6.12/760-01-net-dsa-qca8k-8021q-tagger-stage.patch"
P10 = ROOT / "backports/staging/760-10-net-dsa-qca8021q-routed-cpu-bridge-vid-6.12-CANDIDATE.patch"
P11 = ROOT / "backports/staging/760-11-net-dsa-qca8021q-vlan-aware-vid-guard-6.12-CANDIDATE.patch"
MODEL = ROOT / "tests/wg2600hp_qca8021q_guard_host.c"

def extract_new_file(patch: str) -> list[str]:
    _, sep, rest = patch.partition("+++ b/net/dsa/tag_qca_8021q.c\n")
    if not sep:
        raise AssertionError("new qca8021q tagger missing")
    head, sep, body = rest.partition("\n")
    if not sep or not re.match(r"@@ -0,0 \+1,\d+ @@", head):
        raise AssertionError("unexpected base tagger hunk")
    lines = body.splitlines()
    if not all(row.startswith("+") for row in lines):
        raise AssertionError("new file hunk has unexpected trailing content")
    result = [row[1:] for row in lines]
    expected = int(re.search(r"\+1,(\d+)", head).group(1))
    if len(result) != expected:
        raise AssertionError(f"new file hunk line count {len(result)} != {expected}")
    return result

def apply_one_hunk(source: list[str], patch: str) -> list[str]:
    # Candidates 760-10/11 are intentionally exactly one-file, one-hunk diffs.
    if len(re.findall(r"(?m)^@@ ", patch)) != 1:
        raise AssertionError("expected exactly one hunk")
    files = re.findall(r"(?m)^\+\+\+ b/(.+)$", patch)
    if files != ["net/dsa/tag_qca_8021q.c"]:
        raise AssertionError("changed file outside isolated DSA tagger")
    match = re.search(r"(?m)^@@ -(\d+),(\d+) \+(\d+),(\d+) @@\n", patch)
    if not match:
        raise AssertionError("hunk lacks explicit line counts")
    old_line, old_count, new_line, new_count = map(int, match.groups())
    rows = patch[match.end():].splitlines()
    if not all(row and row[0] in " +-\\" for row in rows):
        raise AssertionError("invalid hunk body")
    before = [row[1:] for row in rows if row.startswith((" ", "-"))]
    after = [row[1:] for row in rows if row.startswith((" ", "+"))]
    start = old_line - 1
    if (len(before), len(after)) != (old_count, new_count):
        raise AssertionError("incorrect unified diff line counts")
    if new_line != old_line or source[start:start + old_count] != before:
        raise AssertionError("staged patch fails exact context or line number")
    return source[:start] + after + source[start + old_count:]

def extract_function(source: str) -> str:
    start = source.index("static struct sk_buff *qca_8021q_xmit(")
    opening = source.index("{", start)
    depth = 0
    for i in range(opening, len(source)):
        if source[i] == "{":
            depth += 1
        elif source[i] == "}":
            depth -= 1
            if depth == 0:
                return source[start:i + 1]
    raise AssertionError("qca_8021q_xmit function braces unmatched")

def normalize(src: str) -> str:
    src = re.sub(r"/\*.*?\*/", "", src, flags=re.S)
    src = re.sub(r"//[^\n]*", "", src)
    return re.sub(r"\s+", "", src)

def main() -> int:
    source = extract_new_file(TAGGER.read_text())
    if len(source) != 177:
        raise AssertionError(f"expected 177 lines in base tagger, got {len(source)}")
    source = apply_one_hunk(source, P10.read_text())
    if len(source) != 183:
        raise AssertionError("760-10 unexpected line count")
    source = apply_one_hunk(source, P11.read_text())
    if len(source) != 220:
        raise AssertionError("760-11 unexpected line count")

    actual = extract_function("\n".join(source))
    model = extract_function(MODEL.read_text())
    # These two substitutions are test-only type/constant substitutes.
    model = model.replace("skb->hwproto", "skb->vlan_proto")
    model = model.replace("tci & 0x0fff", "tci & VLAN_VID_MASK")
    if normalize(actual) != normalize(model):
        raise AssertionError("host model differs from patched kernel xmit function")
    print("PASS staged 760-01 + 760-10 + 760-11 apply exactly")
    print("PASS patched qca_8021q_xmit equals host model (whitespace/comments and 2 mock aliases ignored)")
    print("HOST_SOURCE_SYNC=PASS (kernel build and hardware NSS NOT tested)")
    return 0

if __name__ == "__main__":
    try:
        sys.exit(main())
    except (AssertionError, OSError, ValueError) as exc:
        print("HOST_SOURCE_SYNC=FAIL:", exc, file=sys.stderr)
        sys.exit(1)
