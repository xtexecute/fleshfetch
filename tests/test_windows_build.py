import os
import unittest
from unittest.mock import patch

import build_windows


class WindowsBuildTests(unittest.TestCase):
    def test_cpu_limits_apply_to_compilation_and_linking(self):
        class StopBeforeCompilation(Exception):
            pass

        with patch('sys.argv', ['build_windows.py', '--zig', 'zig.exe']), \
                patch.dict(os.environ, {'LDFLAGS': '-march=native'}), \
                patch('build_windows.subprocess.run', side_effect=StopBeforeCompilation) as run:
            with self.assertRaises(StopBeforeCompilation):
                build_windows.main()
        env = run.call_args.kwargs['env']
        self.assertEqual(env['CCFLAGS'], env['LDFLAGS'])
        self.assertIn('-target x86_64-windows-gnu', env['LDFLAGS'])
        self.assertIn('-march=x86_64', env['LDFLAGS'])
        self.assertIn('-mno-avx512f', env['LDFLAGS'])
        self.assertNotIn('native', env['LDFLAGS'])


if __name__ == '__main__':
    unittest.main()
