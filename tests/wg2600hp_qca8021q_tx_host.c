/* Isolated host-only harness of 760-10 qca_8021q_xmit VID selection.
 * It does not emulate DSA, switch hardware or NSS firmware.
 */
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>

typedef uint16_t u16;
typedef uint8_t u8;
#define ETH_P_8021Q 0x8100
#define VLAN_PRIO_SHIFT 13
struct net_device { bool vlan_aware; struct dsa_port *dp; };
struct dsa_bridge { struct net_device *dev; bool tx_fwd_offload; unsigned int num; };
struct dsa_port { struct dsa_bridge *bridge; };
struct sk_buff {
    bool offload_fwd_mark;
    bool upper_tagged;
    unsigned int queue;
    unsigned int tagged;
    unsigned int vid;
};
static struct dsa_port *dsa_user_to_port(struct net_device *d) { return d->dp; }
static u16 skb_get_queue_mapping(struct sk_buff *s) { return s->queue; }
static u8 netdev_txq_to_tc(struct net_device *d, u16 q) { (void)d; (void)q; return 0; }
static u16 dsa_tag_8021q_standalone_vid(struct dsa_port *dp) { (void)dp; return 0x110; }
static u16 dsa_tag_8021q_bridge_vid(unsigned int n) { return n ? 0x220 : 0; }
static unsigned int dsa_port_bridge_num_get(struct dsa_port *dp) { return dp->bridge ? dp->bridge->num : 0; }
static struct net_device *dsa_port_bridge_dev_get(struct dsa_port *dp) { return dp->bridge ? dp->bridge->dev : NULL; }
static bool br_vlan_enabled(struct net_device *dev) { return dev->vlan_aware; }
static bool qca_8021q_upper_tagged(struct sk_buff *skb, struct net_device *d) { (void)d; return skb->upper_tagged; }
static struct sk_buff *dsa_8021q_xmit(struct sk_buff *skb, struct net_device *d, unsigned tpid, unsigned tci) {
    (void)d; (void)tpid; skb->tagged=1; skb->vid=tci & 0xfff; return skb;
}

/* Isolated 760-10 result: direct transcription of the patched C function. */
static struct sk_buff *qca_8021q_xmit(struct sk_buff *skb,
                                      struct net_device *netdev)
{
    struct dsa_port *dp = dsa_user_to_port(netdev);
    u16 queue_mapping = skb_get_queue_mapping(skb);
    u16 tx_vid = dsa_tag_8021q_standalone_vid(dp);
    u8 pcp;

    struct net_device *br = dsa_port_bridge_dev_get(dp);

    /* An offloaded frame in a VLAN-aware bridge already carries the
     * bridge VLAN. Do not add a tag_8021q VLAN on top. */
    if (skb->offload_fwd_mark && br && br_vlan_enabled(br))
        return skb;

    /* dsa_tag_8021q_bridge_join() replaces the standalone VID with
     * a bridge VID. Routed IPv4 output has no offload_fwd_mark. */
    if (br && dp->bridge && dp->bridge->tx_fwd_offload &&
        !br_vlan_enabled(br))
        tx_vid = dsa_tag_8021q_bridge_vid(dsa_port_bridge_num_get(dp));

    if (qca_8021q_upper_tagged(skb, netdev))
        return skb;

    pcp = netdev_txq_to_tc(netdev, queue_mapping);
    return dsa_8021q_xmit(skb, netdev, ETH_P_8021Q,
                         ((pcp << VLAN_PRIO_SHIFT) | tx_vid));
}

struct testcase {
    const char *label;
    bool bridged, aware, offload, marked, upper_tagged;
    unsigned expected_tagged, expected_vid;
};
int main(void) {
    struct testcase t[] = {
        {"standalone routed", false,false,false,false,false,1,0x110},
        {"standalone forwarded", false,false,false,true,false,1,0x110},
        {"bridge without offload", true,false,false,false,false,1,0x110},
        {"bridge with routed L3", true,false,true,false,false,1,0x220},
        {"bridge with marked L2", true,false,true,true,false,1,0x220},
        {"VLAN-aware marked", true,true,true,true,false,0,0},
        {"VLAN-aware routed", true,true,true,false,false,1,0x110},
        {"user VLAN upper", true,false,true,false,true,0,0},
    };
    unsigned errors=0;
    for(unsigned i=0;i<sizeof(t)/sizeof(t[0]);i++) {
        struct dsa_port p={0};
        struct net_device br={.vlan_aware=t[i].aware};
        struct dsa_bridge bridge={.dev=&br, .tx_fwd_offload=t[i].offload, .num=1};
        struct net_device dev={.dp=&p};
        struct sk_buff skb={.offload_fwd_mark=t[i].marked, .upper_tagged=t[i].upper_tagged};
        p.bridge=t[i].bridged?&bridge:NULL;
        qca_8021q_xmit(&skb, &dev);
        bool ok=skb.tagged==t[i].expected_tagged && skb.vid==t[i].expected_vid;
        printf("%s %s tagged=%u vid=0x%x\n", ok?"PASS":"FAIL",t[i].label,skb.tagged,skb.vid);
        if(!ok)errors++;
    }
    printf("HOST_ONLY %zu cases, %u failed\n",sizeof(t)/sizeof(t[0]),errors);
    return errors?1:0;
}
