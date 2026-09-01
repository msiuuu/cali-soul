import json
import numpy as np
from pathlib import Path

repo = Path(r"C:\Users\yuscr\cali-soul")
memories = json.loads((repo / "memories_v2.json").read_text(encoding="utf-8"))

ids = sorted(m["id"] for m in memories)
idx = {mid: i for i, mid in enumerate(ids)}
n = len(ids)
matrix = np.zeros((n, n), dtype=np.float32)

skipped_str = 0
orphan = 0
for m in memories:
    src = idx[m["id"]]
    for c in m.get("connections") or []:
        if not isinstance(c, dict):
            skipped_str += 1
            continue
        tgt_id = c.get("target_id")
        if tgt_id not in idx:
            orphan += 1
            continue
        tgt = idx[tgt_id]
        w = float(c.get("strength", 0))
        if w <= 0:
            continue
        matrix[src][tgt] = max(matrix[src][tgt], w)
        matrix[tgt][src] = max(matrix[tgt][src], w)

(repo / "connection_matrix_ids.json").write_text(json.dumps(ids), encoding="utf-8")
np.save(repo / "connection_matrix.npy", matrix)

nonzero = int(np.count_nonzero(np.triu(matrix, k=1)))
print(f"wrote {n} ids and {n}x{n} matrix ({nonzero} upper-tri edges, {skipped_str} string-conns skipped, {orphan} orphans)")
