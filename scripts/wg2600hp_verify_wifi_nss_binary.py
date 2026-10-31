#!/usr/bin/env python3
"""Verify compiled Wi-Fi NSS modules inside a WG2600HP initramfs uImage or build ZIP.

This checks ELF imports/exports and radio firmware presence, not runtime NSS acceleration.
Requires readelf. Does not write to the original firmware archive.
"""
import lzma
import re
import shutil
import struct
import subprocess
import sys
import zlib
import zipfile
from pathlib import Path
from tempfile import TemporaryDirectory

REQUIRED = ('nss_virt_if_create_sync', 'nss_virt_if_destroy_sync',
            'nss_virt_if_register', 'nss_virt_if_tx_buf')
MODULES = ('lib/modules/6.12.112/mac80211.ko',
           'lib/modules/6.12.112/qca-nss-drv.ko',
           'lib/modules/6.12.112/ath10k_core.ko',
           'lib/modules/6.12.112/ath10k_pci.ko')
FW = ('lib/firmware/ath10k/QCA99X0/hw2.0/firmware-5.bin',
      'lib/firmware/ath10k/QCA99X0/hw2.0/board-2.bin')


def image_bytes(path):
    if not zipfile.is_zipfile(path):
        return path.read_bytes()
    with zipfile.ZipFile(path) as archive:
        candidates = [name for name in archive.namelist()
                      if name.endswith('nec_wg2600hp-initramfs-uImage')]
        if len(candidates) != 1:
            raise ValueError('not exactly one WG2600HP initramfs uImage')
        return archive.read(candidates[0])


def decompress_kernel(image):
    if len(image) < 64 or image[:4] != b'\x27\x05\x19\x56':
        raise ValueError('not a U-Boot uImage')
    payload_size = struct.unpack_from('>I', image, 12)[0]
    if payload_size != len(image) - 64:
        raise ValueError('uImage payload size mismatch')
    payload = image[64:]
    if zlib.crc32(payload) != struct.unpack_from('>I', image, 24)[0]:
        raise ValueError('uImage payload CRC mismatch')
    magic = b'\xfd7zXZ\0'
    start = 0
    while (start := payload.find(magic, start)) >= 0:
        try:
            decomp = lzma.LZMADecompressor()
            data = decomp.decompress(payload[start:], max_length=128 * 1024 * 1024)
            if decomp.eof and b'070701' in data:
                return data
        except lzma.LZMAError:
            pass
        start += 1
    raise ValueError('could not locate XZ kernel with embedded newc initramfs')


def initramfs_files(kernel):
    # Skip cpio magic strings in kernel code; require newc header and 'bin' entry.
    start = -1
    while (start := kernel.find(b'070701', start + 1)) >= 0:
        try:
            hdr = kernel[start:start + 110]
            if len(hdr) != 110 or not re.fullmatch(b'070701[0-9a-fA-F]{104}', hdr):
                continue
            size = int(hdr[54:62], 16)
            namesize = int(hdr[94:102], 16)
            if size == 0 and kernel[start + 110:start + 110 + namesize] == b'bin\0':
                break
        except ValueError:
            continue
    if start < 0:
        raise ValueError('newc rootfs not found')
    found = {}
    pos = start
    count = 0
    while pos + 110 <= len(kernel):
        hdr = kernel[pos:pos + 110]
        if not re.fullmatch(b'07070[12][0-9a-fA-F]{104}', hdr):
            raise ValueError('invalid newc header')
        size = int(hdr[54:62], 16)
        namesize = int(hdr[94:102], 16)
        if not 1 <= namesize <= 1024:
            raise ValueError('invalid newc filename length')
        name = kernel[pos + 110:pos + 110 + namesize - 1].decode('utf-8')
        data_start = (pos + 110 + namesize + 3) & ~3
        if data_start + size > len(kernel):
            raise ValueError('truncated newc payload')
        if name == 'TRAILER!!!':
            if count < 10:
                raise ValueError('unexpectedly short initramfs')
            return found
        if name in (*MODULES, *FW):
            found[name] = kernel[data_start:data_start + size]
        pos = (data_start + size + 3) & ~3
        count += 1
    raise ValueError('missing newc trailer')


def readelf(path, *args):
    return subprocess.run(('readelf', *args, str(path)), check=True,
                          text=True, capture_output=True).stdout


def main(path):
    if not shutil.which('readelf'):
        raise RuntimeError('readelf not installed')
    files = initramfs_files(decompress_kernel(image_bytes(path)))
    for file in (*MODULES, *FW):
        if not files.get(file):
            raise ValueError('missing or empty initramfs file: ' + file)
        print('PASS bundled ' + file)
    with TemporaryDirectory(prefix='wg2600hp-wifi-nss-') as tmp:
        mac = Path(tmp) / 'mac80211.ko'
        nss = Path(tmp) / 'qca-nss-drv.ko'
        mac.write_bytes(files[MODULES[0]])
        nss.write_bytes(files[MODULES[1]])
        macsyms = readelf(mac, '-Ws')
        exports = readelf(nss, '-p', '__ksymtab_strings')
        for symbol in REQUIRED:
            imported = re.search(r'\bGLOBAL\s+DEFAULT\s+UND\s+' +
                                 re.escape(symbol) + r'\s*$', macsyms, re.M)
            exported = re.search(r'^\s*\[[^]]+\]\s+' +
                                 re.escape(symbol) + r'\s*$', exports, re.M)
            if not imported or not exported:
                raise ValueError('NSS symbol import/export mismatch: ' + symbol)
            print('PASS ELF imported + exported ' + symbol)
    print('PASS WG2600HP compiled Wi-Fi NSS binary presence (not acceleration)')


if __name__ == '__main__':
    try:
        if len(sys.argv) != 2:
            raise ValueError('usage: verify_wifi_nss_binary.py ZIP-or-initramfs-uImage')
        main(Path(sys.argv[1]))
    except (OSError, ValueError, RuntimeError, subprocess.CalledProcessError,
            zipfile.BadZipFile) as err:
        print('FAIL WG2600HP Wi-Fi NSS binary: ' + str(err), file=sys.stderr)
        sys.exit(1)
