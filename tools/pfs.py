"""Artemis pf8/pf6 archive reader/writer.

pf8 layout:
  magic  b"pf8"
  uint32 index_size          (bytes following this field that form the index)
  index:
    uint32 file_count
    per file: uint32 name_len, name (utf-8, '\\' separated), uint32 reserved(0),
              uint32 offset, uint32 size
    ... (offset table follows in official archives, included in index_size)
  file data (pf8: XOR-encrypted with SHA1 of the raw index bytes)
"""
import hashlib
import io
import os
import struct
import sys


class Entry:
    __slots__ = ("name", "offset", "size")

    def __init__(self, name, offset, size):
        self.name = name
        self.offset = offset
        self.size = size


class PfsArchive:
    def __init__(self, path):
        self.path = path
        self.f = open(path, "rb")
        magic = self.f.read(2)
        if magic != b"pf":
            raise ValueError(f"{path}: not a pfs archive")
        self.version = int(self.f.read(1))
        (index_size,) = struct.unpack("<I", self.f.read(4))
        index_start = self.f.tell()
        index = self.f.read(index_size)
        self.xor_key = hashlib.sha1(index).digest() if self.version == 8 else None
        r = io.BytesIO(index)
        (count,) = struct.unpack("<I", r.read(4))
        self.entries = []
        for _ in range(count):
            (nlen,) = struct.unpack("<I", r.read(4))
            name = r.read(nlen).decode("utf-8")
            r.read(4)  # reserved
            offset, size = struct.unpack("<II", r.read(8))
            self.entries.append(Entry(name, offset, size))

    def read(self, entry):
        if isinstance(entry, str):
            entry = next(e for e in self.entries if e.name == entry)
        self.f.seek(entry.offset)
        data = bytearray(self.f.read(entry.size))
        if self.xor_key:
            key = self.xor_key
            klen = len(key)
            for i in range(len(data)):
                data[i] ^= key[i % klen]
        return bytes(data)

    def names(self):
        return [e.name for e in self.entries]

    def close(self):
        self.f.close()


def write_pf8(out_path, files):
    """files: list of (archive_name, data_bytes). Writes a pf8 archive."""
    # Build index with placeholder offsets first to learn its size.
    def build_index(offsets):
        buf = io.BytesIO()
        buf.write(struct.pack("<I", len(files)))
        for (name, data), off in zip(files, offsets):
            nb = name.encode("utf-8")
            buf.write(struct.pack("<I", len(nb)))
            buf.write(nb)
            buf.write(struct.pack("<III", 0, off, len(data)))
        # offset-table tail: count+1 entries of (u32 pos, u32 zero) pointing at
        # each entry's offset field within the index, then filecount pos, then
        # a u32 pointing at the table start. Artemis tolerates its absence but
        # official archives include it; we reproduce it for safety.
        positions = []
        pos = 4
        for name, data in files:
            nb = name.encode("utf-8")
            pos += 4 + len(nb) + 4  # name_len + name + reserved
            positions.append(pos)
            pos += 8  # offset + size
        tail = io.BytesIO()
        tail.write(struct.pack("<I", len(files) + 1))
        for p in positions:
            tail.write(struct.pack("<II", p - 4, 0))
        tail.write(struct.pack("<II", 0, 0))
        body = buf.getvalue()
        table_pos = len(body) + 4 + (len(files) + 1) * 8
        return body + tail.getvalue() + struct.pack("<I", len(body))

    index_len = len(build_index([0] * len(files)))
    data_start = 3 + 4 + index_len
    offsets = []
    off = data_start
    for name, data in files:
        offsets.append(off)
        off += len(data)
    index = build_index(offsets)
    assert len(index) == index_len
    key = hashlib.sha1(index).digest()
    with open(out_path, "wb") as f:
        f.write(b"pf8")
        f.write(struct.pack("<I", len(index)))
        f.write(index)
        for _, data in files:
            enc = bytearray(data)
            for i in range(len(enc)):
                enc[i] ^= key[i % 20]
            f.write(enc)


if __name__ == "__main__":
    cmd = sys.argv[1]
    if cmd == "list":
        a = PfsArchive(sys.argv[2])
        print(f"# version pf{a.version}, {len(a.entries)} files")
        for e in a.entries:
            print(f"{e.size:>12} {e.name}")
    elif cmd == "extract":
        a = PfsArchive(sys.argv[2])
        outdir = sys.argv[3]
        patterns = sys.argv[4:]
        for e in a.entries:
            if patterns and not any(p.lower() in e.name.lower() for p in patterns):
                continue
            dest = os.path.join(outdir, e.name.replace("\\", os.sep))
            os.makedirs(os.path.dirname(dest), exist_ok=True)
            with open(dest, "wb") as f:
                f.write(a.read(e))
        print("done")
