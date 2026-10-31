#!/usr/bin/env python3
"""Validate the actual WG2600HP DTB embedded in an OpenWrt uImage."""
import struct
import sys
from pathlib import Path

MAGIC = b'\xd0\x0d\xfe\xed'
BEGIN_NODE, END_NODE, PROP, NOP, END = 1, 2, 3, 4, 9

def parse_dtb(buf):
    if len(buf) < 40:
        raise ValueError('short FDT header')
    fields = struct.unpack_from('>10I', buf)
    magic, size, off_struct, off_strings, off_reserved, version, last, _, size_strings, size_struct = fields
    if (magic != 0xD00DFEED or version not in (16, 17) or
            size > len(buf) or off_struct < 40 or
            off_struct + size_struct > size or
            off_strings + size_strings > size or
            off_reserved >= size):
        raise ValueError('invalid FDT bounds')
    buf = buf[:size]
    stack = []
    nodes = {}
    cursor = off_struct
    end = off_struct + size_struct
    while cursor + 4 <= end:
        token = struct.unpack_from('>I', buf, cursor)[0]
        cursor += 4
        if token == BEGIN_NODE:
            terminator = buf.find(b'\0', cursor, end)
            if terminator < 0:
                raise ValueError('unterminated FDT node')
            name = buf[cursor:terminator].decode('ascii')
            stack.append(name)
            cursor = (terminator + 4) & ~3
            nodes.setdefault('/'.join(stack), {})
        elif token == END_NODE:
            if not stack:
                raise ValueError('unbalanced FDT node')
            stack.pop()
        elif token == PROP:
            if cursor + 8 > end or not stack:
                raise ValueError('malformed FDT property')
            length, offset = struct.unpack_from('>II', buf, cursor)
            cursor += 8
            if cursor + length > end or offset >= size_strings:
                raise ValueError('FDT property out of bounds')
            value = buf[cursor:cursor+length]
            cursor = (cursor + length + 3) & ~3
            name_start = off_strings + offset
            name_end = buf.find(b'\0', name_start, off_strings + size_strings)
            if name_end < 0:
                raise ValueError('unterminated property name')
            name = buf[name_start:name_end].decode('ascii')
            nodes['/'.join(stack)][name] = value
        elif token == NOP:
            pass
        elif token == END:
            if stack:
                raise ValueError('FDT ended inside a node')
            return nodes
        else:
            raise ValueError('unknown FDT token %d' % token)
    raise ValueError('missing FDT END token')

def check(path):
    b = Path(path).read_bytes()
    start = 0
    candidates = []
    while True:
        i = b.find(MAGIC, start)
        if i < 0:
            break
        start = i + 4
        try:
            nodes = parse_dtb(b[i:])
            root = nodes.get('')
            if root is not None and b'nec,wg2600hp' in root.get('compatible', b'').split(b'\0'):
                candidates.append(nodes)
        except (ValueError, UnicodeError, struct.error):
            continue
    if len(candidates) != 1:
        raise ValueError('expected exactly one WG2600HP embedded DTB, found %d' % len(candidates))
    nodes = candidates[0]
    def count_compatible(comp):
        return sum(comp in v.get('compatible', b'').split(b'\0') for v in nodes.values())
    checks = {
        'WG2600HP NSS GMAC x2': count_compatible(b'qcom,nss-gmac') == 2,
        'NSS core x2': count_compatible(b'qcom,nss') == 2,
        'NSS common x1': count_compatible(b'qcom,nss-common') == 1,
        'TUNIPIP6 device-tree enable': any('qcom,tunipip6-enabled' in v for v in nodes.values() if b'qcom,nss' in v.get('compatible', b'').split(b'\0')),
        'firmware partition size 0x17a0000': any(v.get('reg') == struct.pack('>II', 0x860000, 0x17a0000) for name, v in nodes.items() if name.endswith('/firmware@860000')),
    }
    # The NSS image must retain the official 25.12.6 WG2600HP DSA topology.
    switches = [
        (name, props) for name, props in nodes.items()
        if b'qca,qca8337' in props.get('compatible', b'').split(b'\0')
    ]
    checks['QCA8337 DSA switch x1'] = len(switches) == 1
    expected_ports = {
        0: 'cpu', 1: 'wan', 2: 'lan1', 3: 'lan2',
        4: 'lan3', 5: 'lan4', 6: 'cpu',
    }
    for port, label in expected_ports.items():
        path = (switches[0][0] + '/ports/port@%d' % port) if len(switches) == 1 else ''
        checks['DSA port %d = %s' % (port, label)] = (
            nodes.get(path, {}).get('label') == (label.encode('ascii') + b'\0')
        )

    # Both DSA CPU conduits use fixed links.  PHY_MAX_ADDR (32) tells
    # qca-nss-gmac not to attach a non-existent MDIO PHY.
    gmacs = {}
    for name, props in nodes.items():
        if b'qcom,nss-gmac' not in props.get('compatible', b'').split(b'\0'):
            continue
        raw_id = props.get('qcom,id', b'')
        if len(raw_id) == 4:
            gmacs[struct.unpack('>I', raw_id)[0]] = (name, props)
    for mac_id in (1, 2):
        entry = gmacs.get(mac_id)
        checks['NSS GMAC%d fixed-link, no external PHY' % mac_id] = (
            entry is not None
            and entry[1].get('qcom,phy-mdio-addr') == struct.pack('>I', 32)
            and entry[1].get('qcom,poll-required') == struct.pack('>I', 0)
            and any(name.startswith(entry[0] + '/fixed-link') for name in nodes)
        )

    for name, ok in checks.items():
        print('%s %s' % ('PASS' if ok else 'FAIL', name))
    if not all(checks.values()):
        raise ValueError('compiled DTB validation failed')

if __name__ == '__main__':
    try:
        if len(sys.argv) != 2:
            raise ValueError('usage: script.py <WG2600HP-initramfs-uImage>')
        check(sys.argv[1])
    except (OSError, ValueError) as e:
        print('FAIL: %s' % e, file=sys.stderr)
        sys.exit(1)
