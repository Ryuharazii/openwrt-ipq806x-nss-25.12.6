/* WG2600HP isolated CPU TX guard model. No hardware or NSS emulation. */
#include <stdbool.h>
#include <stdint.h>
#include <stdio.h>
#include <stddef.h>
typedef uint16_t u16; typedef uint8_t u8;
#define ETH_P_8021Q 0x8100
#define ETH_P_8021AD 0x88a8
#define VLAN_PRIO_SHIFT 13
struct dsa_port;
struct net_device { bool vlan_aware; int pvid; int proto; struct dsa_port *dp; };
struct dsa_bridge { struct net_device *dev; bool tx_fwd_offload; unsigned num; };
struct dsa_port { struct dsa_bridge *bridge; };
struct sk_buff { bool offload_fwd_mark, upper_tagged, hwtag; u16 hwproto, hwvid, protocol, inline_vid; unsigned tagged, vid; };
static bool br_vlan_enabled(const struct net_device *d) { return d->vlan_aware; }
static int br_vlan_get_proto(const struct net_device *d,u16 *p) { *p=d->proto; return 0; }
static int br_vlan_get_pvid_rcu(const struct net_device *d,u16 *v) { *v=d->pvid; return 0; }
static void rcu_read_lock(void) {}
static void rcu_read_unlock(void) {}
static bool vid_is_dsa_8021q(u16 vid) { return vid>=0xc00; }
static bool skb_vlan_tag_present(struct sk_buff *s) { return s->hwtag; }
static u16 skb_vlan_tag_get_id(struct sk_buff *s) { return s->hwvid; }
static int __vlan_get_tag(struct sk_buff *s, u16 *tci) { if(s->protocol!=ETH_P_8021Q) return -1; *tci=s->inline_vid; return 0; }
static bool qca_8021q_upper_tagged(struct sk_buff *s,struct net_device *n) { (void)n; return s->upper_tagged; }
static struct sk_buff *dsa_8021q_xmit(struct sk_buff *s,struct net_device *n,unsigned proto,unsigned tci) { (void)n; (void)proto; s->tagged=true; s->vid=tci&0xfff; return s; }
static u16 dsa_tag_8021q_standalone_vid(struct dsa_port *d){(void)d;return 0x110;}
static u16 dsa_tag_8021q_bridge_vid(unsigned b){return b?0x220:0;}
static unsigned dsa_port_bridge_num_get(struct dsa_port *d){return d->bridge?d->bridge->num:0;}
static struct net_device *dsa_port_bridge_dev_get(struct dsa_port *d){return d->bridge?d->bridge->dev:NULL;}
static u8 netdev_txq_to_tc(struct net_device *n,u16 q){(void)n;(void)q;return 0;}
static struct dsa_port *dsa_user_to_port(struct net_device *n){return n->dp;}
static u16 skb_get_queue_mapping(struct sk_buff *s){(void)s;return 0;}
static u16 htons(u16 x){return x;}

/* Transcribed logic of combined 760-01 + 760-10 + 760-11 in isolated host model. */
static struct sk_buff *qca_8021q_xmit(struct sk_buff *skb, struct net_device *netdev)
{
    struct dsa_port *dp = dsa_user_to_port(netdev);
    u16 queue_mapping = skb_get_queue_mapping(skb);
    u16 tx_vid = dsa_tag_8021q_standalone_vid(dp);
    u8 pcp;

    struct net_device *br = dsa_port_bridge_dev_get(dp);

    if (br && br_vlan_enabled(br)) {
        u16 proto, vid = 0;
        int err;

        if (br_vlan_get_proto(br, &proto) || proto != ETH_P_8021Q)
            return NULL;

        if (skb_vlan_tag_present(skb)) {
            if (skb->hwproto != htons(ETH_P_8021Q) ||
                vid_is_dsa_8021q(skb_vlan_tag_get_id(skb)))
                return NULL;
            return skb;
        }
        if (skb->protocol == htons(ETH_P_8021Q)) {
            u16 tci;
            if (__vlan_get_tag(skb, &tci) || vid_is_dsa_8021q(tci & 0x0fff))
                return NULL;
            return skb;
        }
        if (skb->protocol == htons(ETH_P_8021AD))
            return NULL;

        if (skb->offload_fwd_mark)
            return NULL;

        rcu_read_lock();
        err = br_vlan_get_pvid_rcu(netdev, &vid);
        rcu_read_unlock();
        if (err || !vid || vid_is_dsa_8021q(vid))
            return NULL;

        pcp = netdev_txq_to_tc(netdev, queue_mapping);
        return dsa_8021q_xmit(skb, netdev, ETH_P_8021Q,
                              ((pcp << VLAN_PRIO_SHIFT) | vid));
    }

    if (br && dp->bridge && dp->bridge->tx_fwd_offload &&
        !br_vlan_enabled(br))
        tx_vid = dsa_tag_8021q_bridge_vid(dsa_port_bridge_num_get(dp));

    if (qca_8021q_upper_tagged(skb, netdev))
        return skb;

    pcp = netdev_txq_to_tc(netdev, queue_mapping);
    return dsa_8021q_xmit(skb, netdev, ETH_P_8021Q,
                          ((pcp << VLAN_PRIO_SHIFT) | tx_vid));
}

struct testcase { const char *name; bool bridged,aware,offload,marked,hwtag,upper;int pvid,proto,skbproto;int hwproto,hwvid,inlinevid; bool should_pass;unsigned want_tag, want_vid; };
int main(void){
    const struct testcase cases[]={
        {"standalone IPv4",0,0,0,0,0,0,0,0x8100,0x0800,0,0,0,1,1,0x110},
        {"LAN routed no VLAN filtering",1,0,1,0,0,0,0,0x8100,0x0800,0,0,0,1,1,0x220},
        {"LAN L2 marked",1,0,1,1,0,0,0,0x8100,0x0800,0,0,0,1,1,0x220},
        {"VLAN aware local PVID",1,1,1,0,0,0,0x22,0x8100,0x0800,0,0,0,1,1,0x22},
        {"VLAN aware PVID zero",1,1,1,0,0,0,0,0x8100,0x0800,0,0,0,0,0,0},
        {"VLAN aware marked no tag",1,1,1,1,0,0,0x22,0x8100,0x0800,0,0,0,0,0,0},
        {"VLAN aware VLAN hwtag",1,1,1,1,1,0,0x22,0x8100,0x0800,0x8100,0x22,0,1,0,0},
        {"VLAN aware reserved hwtag",1,1,1,1,1,0,0x22,0x8100,0x0800,0x8100,0xc10,0,0,0,0},
        {"VLAN aware 8021ad hwtag",1,1,1,1,1,0,0x22,0x8100,0x0800,0x88a8,0x22,0,0,0,0},
        {"VLAN aware inline reserved",1,1,1,1,0,0,0x22,0x8100,0x8100,0,0,0xc10,0,0,0},
        {"VLAN aware inline 8021Q",1,1,1,1,0,0,0x22,0x8100,0x8100,0,0,0,1,0,0},
        {"VLAN aware non-8021Q bridge",1,1,1,0,0,0,0x22,0x88a8,0x0800,0,0,0,0,0,0},
    };
    int errors=0;
    for(size_t i=0;i<sizeof(cases)/sizeof(cases[0]);i++){
        const struct testcase *t=&cases[i];
        struct dsa_port port={0};
        struct net_device bridge={.vlan_aware=t->aware,.proto=t->proto};
        struct dsa_bridge b={.dev=&bridge,.tx_fwd_offload=t->offload,.num=1};
        struct net_device user={.dp=&port,.pvid=t->pvid,.proto=t->proto};
        struct sk_buff skb={.offload_fwd_mark=t->marked,.hwtag=t->hwtag,.hwproto=t->hwproto,.hwvid=t->hwvid,.inline_vid=t->inlinevid,.protocol=t->skbproto,.upper_tagged=t->upper};
        port.bridge=t->bridged?&b:NULL;
        struct sk_buff *out=qca_8021q_xmit(&skb,&user);
        bool accepted=out!=NULL;
        bool ok=accepted==t->should_pass && (!accepted||(skb.tagged==t->want_tag&&skb.vid==t->want_vid));
        printf("%s %s (accept=%d tagged=%u vid=0x%x)\n",ok?"PASS":"FAIL",t->name,accepted,skb.tagged,skb.vid);
        if(!ok)errors++;
    }
    printf("CASES=%zu PASS=%zu FAIL=%d\n",sizeof(cases)/sizeof(cases[0]),sizeof(cases)/sizeof(cases[0])-errors,errors);
    return errors?1:0;
}
