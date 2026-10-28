import hashlib
import json
import struct
import unittest

from lolping_patch.asar import AsarArchive, ArchiveError


def archive_fixture(files=None):
    files = files or {"package.json": b'{"name":"lolping","version":"0.6.0"}',
                      "out/main/index.js": b"original main", "keep.txt": b"unchanged"}
    tree = {"files": {}}
    data = bytearray()
    for name, content in files.items():
        node = tree
        parts = name.split("/")
        for part in parts[:-1]:
            node = node["files"].setdefault(part, {"files": {}})
        node["files"][parts[-1]] = {
            "offset": str(len(data)), "size": len(content),
            "integrity": {"algorithm": "SHA256", "hash": hashlib.sha256(content).hexdigest(),
                          "blockSize": 4, "blocks": [hashlib.sha256(content[i:i+4]).hexdigest()
                                                    for i in range(0, len(content), 4)]}}
        data.extend(content)
    encoded = json.dumps(tree, separators=(",", ":")).encode()
    pad = b"\0" * (-len(encoded) % 4)
    header = struct.pack("<II", 4 + len(encoded) + len(pad), len(encoded)) + encoded + pad
    return struct.pack("<II", 4, len(header)) + header + data


class AsarTests(unittest.TestCase):
    def test_replacement_preserves_other_entries_and_updates_integrity(self):
        before = AsarArchive(archive_fixture())
        after = AsarArchive(before.replace("out/main/index.js", b"new longer main module"))
        self.assertEqual(after.read("out/main/index.js"), b"new longer main module")
        self.assertEqual(after.read("keep.txt"), b"unchanged")
        self.assertEqual(after.read("package.json"), before.read("package.json"))
        self.assertEqual(after.entry("out/main/index.js")["integrity"]["hash"],
                         hashlib.sha256(b"new longer main module").hexdigest())
        after.verify_integrity()

    def test_truncated_archive_is_rejected_before_mutation(self):
        with self.assertRaises(ArchiveError):
            AsarArchive(archive_fixture()[:-4])

    def test_invalid_outer_pickle_is_rejected(self):
        raw = bytearray(archive_fixture())
        raw[:4] = struct.pack("<I", 100)
        with self.assertRaises(ArchiveError):
            AsarArchive(bytes(raw))

    def test_wrong_entry_integrity_is_detected(self):
        raw = archive_fixture()
        raw = raw[:-1] + bytes([raw[-1] ^ 1])
        with self.assertRaises(ArchiveError):
            AsarArchive(raw).verify_integrity()

    def test_missing_entry_is_reported(self):
        with self.assertRaises(ArchiveError):
            AsarArchive(archive_fixture()).read("missing")


if __name__ == "__main__":
    unittest.main()
