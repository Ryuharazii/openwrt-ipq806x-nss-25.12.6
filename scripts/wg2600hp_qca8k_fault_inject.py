#!/usr/bin/env python3
"""Host fault injection of four exact patched qca8k-common.c C functions.

Extract function bodies from the fully patched Linux 6.12.112 source and
compile them with stub register, VTU and DSA device functions. This is NOT
a full hardware driver test, does not emulate the hardware MDIO transport,
and cannot establish recovery from genuine hardware faults.
"""
from pathlib import Path
import re
import subprocess
import sys
import tempfile

FUNCTIONS = ("qca8k_port_set_pvid", "qca8k_commit_pvid",
             "qca8k_tag_8021q_vlan_snapshot", "qca8k_tag_8021q_vlan_add")

PREFIX = r"""
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <string.h>
typedef uint16_t u16;
typedef uint32_t u32;
#define EIO 5
#define BRIDGE_VLAN_INFO_UNTAGGED 1
#define BRIDGE_VLAN_INFO_PVID 2
#define QCA8K_VTU_FUNC0_VALID (1u<<31)
#define QCA8K_VTU_FUNC0_EG_MODE_PORT_MASK(p) (3u<<(2*(p)))
#define QCA8K_VTU_FUNC0_EG_MODE_PORT_NOT(p) (3u<<(2*(p)))
#define QCA8K_VTU_FUNC0_EG_MODE_PORT_UNTAG(p) (1u<<(2*(p)))
#define QCA8K_VLAN_READ 1
#define QCA8K_REG_VTU_FUNC0 300
#define QCA8K_EGRESS_VLAN(p) (100+(p))
#define QCA8K_REG_PORT_VLAN_CTRL0(p) (200+(p))
#define QCA8K_EGREES_VLAN_PORT_MASK(p) (0xfff)
#define QCA8K_EGREES_VLAN_PORT(p,v) (v)
#define QCA8K_PORT_VLAN_CVID(v) ((v)&0xfff)
#define QCA8K_PORT_VLAN_SVID(v) (((v)&0xfff)<<16)
#define mutex_lock(x) ((void)(x))
#define mutex_unlock(x) ((void)(x))
#define dev_err(...) ((void)0)
struct qca8k_priv {
    void *dev;
    int reg_mutex;
    u16 tag_8021q_pvid[8];
    u16 bridge_pvid[8];
};
struct dsa_switch { struct qca8k_priv *priv; };
struct dsa_port { int port; };
static struct dsa_port fake_port;
static u32 registers[512];
static int writes, fail_write;
static int fail_vtu_add, fail_undo;
static bool vlan_member, vlan_untagged;
static int assertions;
static void expect(int condition, const char *where) {
    assertions++;
    if (!condition) { fprintf(stderr, "FAULT_INJECT=FAIL %s\n",where); }
}
static int qca8k_read(struct qca8k_priv *p, int reg, u32 *out) {
    (void)p;
    if (reg == QCA8K_REG_VTU_FUNC0) {
        *out = vlan_member ? QCA8K_VTU_FUNC0_VALID |
                (vlan_untagged ? QCA8K_VTU_FUNC0_EG_MODE_PORT_UNTAG(1) : 0)
              : QCA8K_VTU_FUNC0_EG_MODE_PORT_NOT(1);
    } else *out = registers[reg];
    return 0;
}
static int qca8k_write(struct qca8k_priv *p, int reg, u32 val) {
    (void)p;
    writes++;
    if (fail_write == writes) return -EIO;
    registers[reg] = val;
    return 0;
}
static int qca8k_rmw(struct qca8k_priv *p, int reg, u32 mask, u32 val) {
    u32 old;
    int ret=qca8k_read(p,reg,&old);
    return ret ? ret : qca8k_write(p,reg,(old&~mask)|(val&mask));
}
static int qca8k_vlan_access(struct qca8k_priv *p, int mode, u16 vid) {
    (void)p;(void)mode;(void)vid;
    return 0;
}
static int qca8k_vlan_add(struct qca8k_priv *p, int port, u16 vid, bool untagged) {
    (void)p;(void)port;(void)vid;
    vlan_member=true;vlan_untagged=untagged;
    return fail_vtu_add ? -EIO : 0;
}
static int qca8k_vlan_del(struct qca8k_priv *p, int port, u16 vid) {
    (void)p;(void)port;(void)vid;
    if (fail_undo) return -EIO;
    vlan_member=false;
    return 0;
}
static struct dsa_port *dsa_to_port(struct dsa_switch *s,int port) {
    (void)s;(void)port;
    return &fake_port;
}
static bool dsa_port_is_vlan_filtering(struct dsa_port *p) {
    (void)p;
    return false;
}
"""

SUFFIX = r"""
static struct qca8k_priv priv;
static struct dsa_switch sw = { .priv=&priv };
static void reset(void) {
    memset(&priv,0,sizeof(priv));
    memset(registers,0,sizeof(registers));
    registers[QCA8K_EGRESS_VLAN(1)]=0x888;
    registers[QCA8K_REG_PORT_VLAN_CTRL0(1)]=0x999;
    priv.tag_8021q_pvid[1]=11;
    writes=0;fail_write=0;
    fail_vtu_add=0;fail_undo=0;
    vlan_member=false;vlan_untagged=false;
}
int main(void) {
    int ret;
    reset();
    ret=qca8k_port_set_pvid(&priv,1,123);
    expect(ret==0,"PVID success return");
    expect(registers[QCA8K_REG_PORT_VLAN_CTRL0(1)]!=0x999,"PVID success update");
    printf("FAULT_INJECT_CASE=PASS PVID_SUCCESS\n");

    reset();
    fail_write=1;
    ret=qca8k_port_set_pvid(&priv,1,123);
    expect(ret==-EIO && registers[QCA8K_EGRESS_VLAN(1)]==0x888 &&
        registers[QCA8K_REG_PORT_VLAN_CTRL0(1)]==0x999,"PVID first-write failure restores");
    printf("FAULT_INJECT_CASE=PASS PVID_FIRST_WRITE_FAILURE\n");

    reset();
    fail_write=2;
    ret=qca8k_port_set_pvid(&priv,1,123);
    expect(ret==-EIO && registers[QCA8K_EGRESS_VLAN(1)]==0x888 &&
        registers[QCA8K_REG_PORT_VLAN_CTRL0(1)]==0x999,"PVID second-write failure restores");
    printf("FAULT_INJECT_CASE=PASS PVID_SECOND_WRITE_FAILURE\n");

    reset();
    ret=qca8k_tag_8021q_vlan_add(&sw,1,33,BRIDGE_VLAN_INFO_PVID);
    expect(ret==0 && vlan_member && priv.tag_8021q_pvid[1]==33,
        "tag VLAN PVID successful registration");
    printf("FAULT_INJECT_CASE=PASS VLAN_ADD_SUCCESS\n");

    reset();
    fail_write=2;
    ret=qca8k_tag_8021q_vlan_add(&sw,1,33,BRIDGE_VLAN_INFO_PVID);
    expect(ret==-EIO && !vlan_member && priv.tag_8021q_pvid[1]==11 &&
        registers[QCA8K_EGRESS_VLAN(1)]==0x888 &&
        registers[QCA8K_REG_PORT_VLAN_CTRL0(1)]==0x999,
        "new VLAN membership cleaned after PVID failure");
    printf("FAULT_INJECT_CASE=PASS NEW_VLAN_PVID_FAILURE\n");

    reset();
    vlan_member=true;vlan_untagged=true;
    fail_write=2;
    ret=qca8k_tag_8021q_vlan_add(&sw,1,33,BRIDGE_VLAN_INFO_PVID);
    expect(ret==-EIO && vlan_member && vlan_untagged &&
        priv.tag_8021q_pvid[1]==11, "existing VLAN egress mode restored");
    printf("FAULT_INJECT_CASE=PASS EXISTING_VLAN_PVID_FAILURE\n");

    reset();
    fail_vtu_add=1;
    ret=qca8k_tag_8021q_vlan_add(&sw,1,33,0);
    expect(ret==-EIO && !vlan_member && priv.tag_8021q_pvid[1]==11,
        "partial VLAN add failure cleaned");
    printf("FAULT_INJECT_CASE=PASS VTU_ADD_FAILURE\n");

    reset();
    fail_write=2;fail_undo=1;
    ret=qca8k_tag_8021q_vlan_add(&sw,1,33,BRIDGE_VLAN_INFO_PVID);
    expect(ret==-EIO && vlan_member,
        "rollback failure must remain visibly incomplete");
    printf("FAULT_INJECT_CASE=PASS ROLLBACK_FAILURE_DETECTED_AS_UNSAFE\n");

    if (assertions != 9) {
        /* Assert count is intentional, catches incomplete test execution. */
        fprintf(stderr, "FAULT_INJECT=FAIL wrong count %d\n",assertions);
        return 3;
    }
    printf("FAULT_INJECT=PASS 8 modeled failure/success cases; limitations: no real MDIO, lock, traffic or ARM execution\n");
    return 0;
}
"""
def get_function(source, name):
    m = re.search(r"(?m)^(?:static )?int\s+"+re.escape(name)+r"\(",source)
    if not m:
        raise ValueError("missing exact patched C implementation "+name)
    start=m.start()
    brace=source.find("{",m.end())
    if brace<0:
        raise ValueError("missing opening brace for "+name)
    depth=0
    for i in range(brace,len(source)):
        if source[i]=="{":depth+=1
        if source[i]=="}":
            depth-=1
            if depth==0:
                return source[start:i+1]+"\n"
    raise ValueError("unbalanced braces "+name)

def main():
    if len(sys.argv)!=2:
        raise ValueError("Usage: sourcepath")
    linux=Path(sys.argv[1])
    source=(linux/"drivers/net/dsa/qca/qca8k-common.c").read_text()
    pieces=[get_function(source,n) for n in FUNCTIONS]
    with tempfile.TemporaryDirectory(prefix="wg2600hp-qca-fi-") as temp:
        c=Path(temp)/"fault_inject.c"
        exe=Path(temp)/"fault_inject"
        c.write_text(PREFIX+"\n".join(pieces)+SUFFIX)
        comp=subprocess.run(["gcc","-std=gnu11","-O0","-Wall","-Wextra",
                             "-Werror","-Wno-unused-parameter",
                             str(c),"-o",str(exe)], stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,text=True,check=False)
        if comp.returncode:
            print("FAULT_INJECT_COMPILE=FAIL\n"+comp.stdout[-6000:],flush=True)
            return 2
        print("FAULT_INJECT_COMPILE=PASS compiled exact patched C functions under mocks",flush=True)
        test=subprocess.run([str(exe)],stdout=subprocess.PIPE,
                            stderr=subprocess.STDOUT,text=True,check=False)
        print(test.stdout,flush=True)
        return test.returncode

if __name__=="__main__":
    sys.exit(main())
