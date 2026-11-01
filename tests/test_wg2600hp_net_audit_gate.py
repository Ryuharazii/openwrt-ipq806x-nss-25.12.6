from pathlib import Path
import os
import subprocess
import tempfile
import unittest

SOURCE = Path(__file__).parent.parent / 'target/linux/ipq806x/base-files/usr/sbin/wg2600hp-net-audit'

class AuditGateTest(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.root = Path(self.tmp.name)
        (self.root / 'sys_class_net').mkdir()
        (self.root / 'bin').mkdir()
        (self.root / 'board_name').write_text('nec,wg2600hp\n')
        for dev in ['eth0', 'eth1', 'wan', 'lan1', 'lan2', 'lan3', 'lan4']:
            p = self.root / 'sys_class_net' / dev
            p.mkdir()
            (p / 'operstate').write_text('up\n')
        # Only for an isolated test: redirect kernel paths to fake fixtures.
        script = SOURCE.read_text().replace('/tmp/sysinfo/board_name', str(self.root / 'board_name'))
        script = script.replace('/sys/class/net/', str(self.root / 'sys_class_net') + '/')
        script = script.replace('/sys/kernel/debug/', str(self.root / 'sys_debug') + '/')
        self.script = self.root / 'script.sh'
        self.script.write_text(script)
        for name, body in {
            'ip': '#!/bin/sh\necho "IP_MOCK $*"\n',
            'dmesg': '#!/bin/sh\nprintf "%s\\n" "$AUDIT_DMESG"\n',
        }.items():
            p = self.root / 'bin' / name
            p.write_text(body)
            p.chmod(0o755)

    def run_script(self, *args, log=''):
        env = dict(os.environ, AUDIT_DMESG=log)
        env['PATH'] = str(self.root / 'bin') + os.pathsep + env['PATH']
        return subprocess.run(['sh', str(self.script), *args], capture_output=True,
                              text=True, env=env, check=False)

    def test_default_never_claims_nss_offload(self):
        r = self.run_script()
        self.assertEqual(r.returncode, 3, r.stdout + r.stderr)
        self.assertIn('RESULT=INCOMPLETE NSS_OFFLOAD=UNVERIFIED', r.stdout)
        self.assertIn('IP_MOCK -d link show dev wan', r.stdout)

    def test_inventory_only_success_does_not_claim_nss(self):
        r = self.run_script('--inventory-only')
        self.assertEqual(r.returncode, 0, r.stdout + r.stderr)
        self.assertIn('RESULT=INVENTORY_ONLY NSS_OFFLOAD=UNVERIFIED', r.stdout)

    def test_missing_net_device_fails(self):
        (self.root / 'sys_class_net' / 'lan4' / 'operstate').unlink()
        (self.root / 'sys_class_net' / 'lan4').rmdir()
        r = self.run_script()
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)
        self.assertIn('RESULT=INVENTORY_FAIL', r.stdout)

    def test_kernel_dsa_error_fails(self):
        r = self.run_script(log='DSA probe failed on qca8k')
        self.assertEqual(r.returncode, 1, r.stdout + r.stderr)

    def test_wrong_board_refused(self):
        (self.root / 'board_name').write_text('nec,wg2600hp3\n')
        r = self.run_script()
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

    def test_unknown_option_refused(self):
        r = self.run_script('--accept-false-pass')
        self.assertEqual(r.returncode, 2, r.stdout + r.stderr)

if __name__ == '__main__':
    unittest.main()
