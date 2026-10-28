import unittest
from lolping_patch.transform import patch_main, PatchError, MARKER


class TransformTests(unittest.TestCase):
    def test_unknown_main_is_rejected(self):
        with self.assertRaises(PatchError):
            patch_main('unrelated application code')

    def test_already_patched_module_is_rejected(self):
        with self.assertRaisesRegex(PatchError, 'already patched'):
            patch_main('any code\n' + MARKER)
