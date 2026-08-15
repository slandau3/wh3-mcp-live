#!/usr/bin/env python3
"""Assemble a WH3 PFH5 mod pack from the mod/ directory tree.

Format (from RPFM write_pfh5):
  header: "PFH5" + u32 flags|file_type (Mod=3) + counts + timestamp
  dependency index (empty), file index (size, uncompressed flag, path),
  file data blobs.

Usage: make_pack.py [MOD_DIR] [OUT_PACK]
"""
import os
import struct
import sys
import tempfile
import time


def collect_files(root):
    if not os.path.isdir(root):
        raise SystemExit(f"MOD_DIR not found: {root}")
    files = []
    for dirpath, _, filenames in os.walk(root):
        for fn in filenames:
            full = os.path.join(dirpath, fn)
            if os.path.islink(full):
                raise SystemExit(f"Refusing symlink: {full}")
            rel = os.path.relpath(full, root).replace("/", "\\")
            with open(full, "rb") as f:
                data = f.read()
            files.append((rel, data))
    return files


def main():
    mod_dir = sys.argv[1] if len(sys.argv) > 1 else "mod"
    out_pack = sys.argv[2] if len(sys.argv) > 2 else "wh3_mcp.pack"

    files = collect_files(mod_dir)
    if not files:
        raise SystemExit(f"no files found under {mod_dir} — refusing empty pack")
    files.sort(key=lambda x: x[0].lower())

    index_entries = []
    for path, data in files:
        entry = struct.pack("<I", len(data))
        entry += b"\x00"
        entry += path.encode("utf-8") + b"\x00"
        index_entries.append(entry)

    header = b"PFH5"
    header += struct.pack("<I", 3)                 # Mod
    header += struct.pack("<I", 0)                 # dependencies count
    header += struct.pack("<I", 0)                 # dependencies index size
    header += struct.pack("<I", len(files))        # files count
    header += struct.pack("<I", sum(len(e) for e in index_entries))
    header += struct.pack("<I", int(time.time()))

    # Atomic write: temp file in same dir, then replace
    tmp_path = out_pack + ".tmp"
    with open(tmp_path, "wb") as f:
        f.write(header)
        for e in index_entries:
            f.write(e)
        for _, data in files:
            f.write(data)
        f.flush()
        os.fsync(f.fileno())
    os.replace(tmp_path, out_pack)

    print(f"Wrote {out_pack}: {len(files)} files, {os.path.getsize(out_pack)} bytes")
    for path, data in files:
        print(f"  {path} ({len(data)}B)")


if __name__ == "__main__":
    main()
