"""Self-contained positive/negative tests of the WG2600HP Wi-Fi NSS ELF image gate."""
import importlib.util
import lzma
import struct
import sys
import tempfile
import unittest
import zipfile
import zlib
from pathlib import Path
from unittest.mock import patch

VERIFIER = Path(__file__).resolve().parent.parent / 'scripts/wg2600hp_verify_wifi_nss_binary.py'
spec = importlib.util.spec_from_file_location('wg2600hp_wifi_nss_binary', VERIFIER)
verifier = importlib.util.module_from_spec(spec)
spec.loader.exec_module(verifier)


def newc_entry(name, payload=b'', mode=0o100644):
    fields = (1, mode, 0, 0, 1, 0, len(payload), 0, 0, 0, 0,
              len(name.encode()) + 1, 0)
    header = b'070701' + b''.join(f'{number:08x}'.encode() for number in fields)
    data = header + name.encode() + b'\0'
    data += b'\0' * (-len(data) % 4)
    data += payload
    data += b'\0' * (-len(data) % 4)
    return data


def sample_image(omit=None):
    files = [(x, b'ELF-dummy') for x in verifier.MODULES]
    files += [(x, b'FW-dummy') for x in verifier.FW]
    files += [(f'etc/dummy{i}', b'x') for i in range(8)]
    root = newc_entry('bin', b'', 0o040755)
    for name, content in files:
        if name != omit:
            root += newc_entry(name, content)
    root += newc_entry('TRAILER!!!')
    payload = b'\0' * 20 + lzma.compress(root, format=lzma.FORMAT_XZ)
    image = bytearray(64)
    struct.pack_into('>I', image, 0, 0x27051956)
    struct.pack_into('>I', image, 12, len(payload))
    struct.pack_into('>I', image, 24, zlib.crc32(payload))
    return bytes(image) + payload


def fake_readelf(path, *args):
    name = Path(path).name
    if args == ('-h',):
        return 'Class: ELF32\nMachine: ARM\n'
    if args == ('-p', '.modinfo'):
        return ' [ 0] vermagic=6.12.112 SMP mod_unload ARMv7\n' + (
            ' [20] depends=cfg80211,qca-nss-drv,compat\n' if name == 'mac80211.ko' else '')
    if args == ('-Ws',) and name == 'mac80211.ko':
        return '\n'.join(f' {i}: 00000000 0 NOTYPE GLOBAL DEFAULT UND {s}'
                         for i, s in enumerate(verifier.REQUIRED))
    if args == ('-p', '__ksymtab_strings') and name == 'qca-nss-drv.ko':
        return '\n'.join(f' [ {i}] {s}' for i, s in enumerate(verifier.REQUIRED))
    raise RuntimeError('unexpected readelf request: ' + repr((name, args)))


class WifiNssImageGateTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.img = Path(self.tmp.name) / 'wg2600hp-initramfs-uImage'
        self.img.write_bytes(sample_image())

    def invoke(self, readelf=fake_readelf):
        with patch.object(verifier, 'readelf', side_effect=readelf):
            verifier.main(self.img)

    def test_valid_arm_nss_modules(self):
        self.invoke()

    def test_zip_selection(self):
        archive = Path(self.tmp.name) / 'image.zip'
        with zipfile.ZipFile(archive, 'w') as z:
            z.write(self.img, 'openwrt-nss-nec_wg2600hp-initramfs-uImage')
        self.assertEqual(verifier.image_bytes(archive), self.img.read_bytes())

    def test_missing_firmware(self):
        self.img.write_bytes(sample_image(omit=verifier.FW[0]))
        with self.assertRaisesRegex(ValueError, 'missing or empty initramfs'):
            self.invoke()

    def test_corrupted_crc(self):
        img = bytearray(self.img.read_bytes())
        img[-1] ^= 1
        self.img.write_bytes(img)
        with self.assertRaisesRegex(ValueError, 'CRC mismatch'):
            self.invoke()

    def test_wrong_architecture(self):
        def wrong_arm(path, *args):
            value = fake_readelf(path, *args)
            if args == ('-h',) and Path(path).name == 'ath10k_pci.ko':
                return value.replace('Machine: ARM', 'Machine: AArch64')
            return value
        with self.assertRaisesRegex(ValueError, 'wrong ARM ELF/kernel ABI'):
            self.invoke(wrong_arm)

    def test_wrong_kernel_vermagic(self):
        def wrong_abi(path, *args):
            value = fake_readelf(path, *args)
            if args == ('-p', '.modinfo') and Path(path).name == 'mac80211.ko':
                return value.replace('6.12.112', '6.12.111')
            return value
        with self.assertRaisesRegex(ValueError, 'wrong ARM ELF/kernel ABI'):
            self.invoke(wrong_abi)

    def test_missing_nss_export(self):
        def wrong_export(path, *args):
            value = fake_readelf(path, *args)
            if args == ('-p', '__ksymtab_strings'):
                return value.replace('nss_virt_if_tx_buf', 'other_name')
            return value
        with self.assertRaisesRegex(ValueError, 'symbol import/export mismatch'):
            self.invoke(wrong_export)

    def test_missing_nss_module_dependency(self):
        def wrong_dependency(path, *args):
            value = fake_readelf(path, *args)
            if args == ('-p', '.modinfo') and Path(path).name == 'mac80211.ko':
                return value.replace('qca-nss-drv', 'not-nss-driver')
            return value
        with self.assertRaisesRegex(ValueError, 'module dependency'):
            self.invoke(wrong_dependency)


if __name__ == '__main__':
    unittest.main(verbosity=2)
