#!/usr/bin/env python3
"""Run the fastfile reader's tests: the unit tests on synthetic files (always), the comparison with the Store
build's own loader on synthetic zones (when the Store exe is in $IW6_ORIGINALS), and on real zones (when
$IW6_FASTFILES names a folder of .ff files; none is ever committed). docs/fastfiles.md, section 12.

    python3 tests/fastfile/run.py [-v]
"""
import sys
import unittest
from pathlib import Path

HERE = Path(__file__).resolve().parent
sys.path.insert(0, str(HERE))

if __name__ == "__main__":
    suite = unittest.defaultTestLoader.loadTestsFromNames(["test_reader", "test_store", "test_xmodel", "test_material", "test_image"])
    result = unittest.TextTestRunner(verbosity=2 if "-v" in sys.argv else 1).run(suite)
    sys.exit(0 if result.wasSuccessful() else 1)
