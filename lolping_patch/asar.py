"""Read and rebuild ASAR archives without extracting application assets."""

import copy
import hashlib
import json
import struct


class ArchiveError(ValueError):
    pass


class AsarArchive:
    def __init__(self, raw):
        self.raw = raw
        try:
            size, header_size, payload_size, json_size = struct.unpack("<4I", raw[:16])
            if (size != 4 or header_size < 8 or header_size > 16 * 1024 * 1024
                    or payload_size != header_size - 4 or json_size > header_size - 8
                    or header_size % 4 or len(raw) < 8 + header_size):
                raise ArchiveError("Invalid ASAR header")
            self.tree = json.loads(raw[16:16 + json_size])
            self.base = 8 + header_size
            self.entries = dict(self._walk(self.tree))
            ranges = []
            for name, node in self.entries.items():
                if node.get("unpacked") or "link" in node:
                    continue
                offset, length = int(node["offset"]), node["size"]
                if (offset < 0 or type(length) is not int or length < 0
                        or self.base + offset + length > len(raw)):
                    raise ArchiveError("Invalid ASAR entry: " + name)
                if length:
                    ranges.append((offset, offset + length))
            ranges.sort()
            if any(a[1] > b[0] for a, b in zip(ranges, ranges[1:])):
                raise ArchiveError("Overlapping ASAR entries")
        except (KeyError, TypeError, UnicodeError, json.JSONDecodeError, struct.error,
                RecursionError, OverflowError) as exc:
            raise ArchiveError("Malformed ASAR archive") from exc
        except ValueError as exc:
            if isinstance(exc, ArchiveError):
                raise
            raise ArchiveError("Invalid ASAR offset") from exc

    def _walk(self, node, prefix=""):
        if not isinstance(node, dict) or not isinstance(node.get("files"), dict):
            raise ArchiveError("Invalid ASAR directory")
        for name, child in node["files"].items():
            if (not isinstance(name, str) or not name or "/" in name or name in (".", "..")
                    or not isinstance(child, dict)):
                raise ArchiveError("Invalid ASAR filename")
            full = prefix + name
            if "files" in child:
                yield from self._walk(child, full + "/")
            else:
                yield full, child

    def entry(self, name):
        try:
            return self.entries[name]
        except KeyError as exc:
            raise ArchiveError("Missing ASAR entry: " + name) from exc

    def read(self, name):
        node = self.entry(name)
        if node.get("unpacked") or "link" in node:
            raise ArchiveError("External ASAR entry is unsupported: " + name)
        start = self.base + int(node["offset"])
        return self.raw[start:start + node["size"]]

    def verify_integrity(self):
        for name, node in self.entries.items():
            if node.get("unpacked") or "link" in node or "integrity" not in node:
                continue
            content = self.read(name)
            integrity = node["integrity"]
            size = integrity.get("blockSize", 0)
            if integrity.get("algorithm") != "SHA256" or type(size) is not int or size <= 0:
                raise ArchiveError("Unsupported ASAR integrity: " + name)
            blocks = [hashlib.sha256(content[i:i + size]).hexdigest()
                      for i in range(0, len(content), size)]
            if (hashlib.sha256(content).hexdigest() != integrity.get("hash")
                    or blocks != integrity.get("blocks")):
                raise ArchiveError("ASAR integrity mismatch: " + name)

    def replace(self, name, content):
        self.read(name)
        tree = copy.deepcopy(self.tree)
        nodes = dict(self._walk(tree))
        packed = [(key, node) for key, node in nodes.items()
                  if not node.get("unpacked") and "link" not in node]
        packed.sort(key=lambda item: int(item[1]["offset"]))
        offset, chunks = 0, []
        for key, node in packed:
            data = content if key == name else self.read(key)
            node["offset"], node["size"] = str(offset), len(data)
            if key == name and "integrity" in node:
                integrity = node["integrity"]
                if integrity.get("algorithm") != "SHA256":
                    raise ArchiveError("Unsupported integrity algorithm")
                size = integrity["blockSize"]
                if type(size) is not int or size <= 0:
                    raise ArchiveError("Invalid integrity block size")
                integrity["hash"] = hashlib.sha256(data).hexdigest()
                integrity["blocks"] = [hashlib.sha256(data[i:i + size]).hexdigest()
                                       for i in range(0, len(data), size)]
            chunks.append(data)
            offset += len(data)
        encoded = json.dumps(tree, ensure_ascii=False, separators=(",", ":")).encode("utf-8")
        padding = b"\0" * (-len(encoded) % 4)
        header = struct.pack("<II", 4 + len(encoded) + len(padding), len(encoded)) + encoded + padding
        return struct.pack("<II", 4, len(header)) + header + b"".join(chunks)
