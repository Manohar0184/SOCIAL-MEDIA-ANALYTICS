"""FastAPI backend. Data source is swappable: replace MockDataService with X/Telegram services later."""
import os, datetime as dt, statistics as st
from collections import Counter, defaultdict
import networkx as nx
from fastapi import FastAPI, HTTPException, Query
from fastapi.middleware.cors import CORSMiddleware
from .mock_data import build, EMO

class MockDataService:
    def __init__(self): self.d = build()
    def posts(self): return self.d["posts"]
# Later: class XDataService / TelegramDataService with the same interface, read keys from env.
SRC = MockDataService(); D = SRC.d
app = FastAPI(title="AI Social Media Intelligence API")
app.add_middleware(CORSMiddleware, allow_origins=["*"], allow_methods=["*"], allow_headers=["*"])
NOW = D["now"]; TOPIC = {t["id"]: t for t in D["topics"]}

def filt(platform="All", days=30, start=None, end=None):
    if platform not in ("All","X","Telegram","Instagram","Facebook","Reddit","YouTube"):
        raise HTTPException(400, "Unknown platform")
    lo = dt.datetime.fromisoformat(start) if start else NOW - dt.timedelta(days=days)
    hi = dt.datetime.fromisoformat(end) if end else NOW + dt.timedelta(hours=1)
    return [p for p in SRC.posts() if (platform=="All" or p["platform"]==platform) and lo <= dt.datetime.fromisoformat(p["timestamp"]) <= hi]

def pct(c, n): return {k: round(100*v/max(n,1),1) for k,v in c.items()}
def sent_dist(ps): c = Counter(p["sentiment"] for p in ps); return pct({k:c.get(k,0) for k in ("positive","neutral","negative")}, len(ps))

def hourly(ps, hours):
    b = defaultdict(list)
    for p in ps:
        t = dt.datetime.fromisoformat(p["timestamp"]); b[t.replace(minute=0,second=0,microsecond=0)].append(p)
    keys = sorted(b); counts = [len(b[k]) for k in keys]
    mu, sd = (st.mean(counts), st.pstdev(counts)) if counts else (0,0)
    out = []
    for k in keys:
        ps_ = b[k]; z = (len(ps_)-mu)/sd if sd else 0
        out.append(dict(time=k.isoformat(), posts=len(ps_), positive=sum(p["sentiment"]=="positive" for p in ps_),
            negative=sum(p["sentiment"]=="negative" for p in ps_), spike=z>2.5, label="Rapid increase detected" if z>2.5 else None,
            zscore=round(z,2)))
    return out

def trend_rows(ps, days):
    half = NOW - dt.timedelta(days=days/2); rows = []
    for tid, t in TOPIC.items():
        tp = [p for p in ps if p["topic_id"]==tid]
        if not tp: continue
        new = sum(dt.datetime.fromisoformat(p["timestamp"]) >= half for p in tp); old = len(tp)-new
        g = round(100*(new-old)/max(old,1),1)
        s = Counter(p["sentiment"] for p in tp).most_common(1)[0][0]
        rows.append(dict(topic_id=tid, topic=t["name"], hashtag=tp[0]["hashtag"], keywords=t["keywords"], mentions=len(tp),
            growth_pct=g, sentiment=s, first_detected=min(p["timestamp"] for p in tp),
            status="Rising" if g>25 else "Declining" if g<-25 else "Stable",
            arrow="↑" if g>25 else "↓" if g<-25 else "→", share_pct=round(100*len(tp)/len(ps),1)))
    return sorted(rows, key=lambda r: -r["mentions"])

def graph():
    G = nx.Graph(); G.add_edges_from((e["source"], e["target"]) for e in D["edges"]); return G
G = graph(); PR = nx.pagerank(G); DC = nx.degree_centrality(G); BC = nx.betweenness_centrality(G, k=100, seed=1)
COMM = {n: i for i, c in enumerate(nx.community.greedy_modularity_communities(G)) for n in c}
UTOP = defaultdict(Counter)
for p in SRC.posts(): UTOP[p["user_id"]][TOPIC[p["topic_id"]]["name"]] += 1

def influencers(n=10):
    top = sorted(PR, key=PR.get, reverse=True)[:n]
    return [dict(user=u, pagerank=round(PR[u],4), degree_centrality=round(DC[u],4), betweenness=round(BC[u],4),
                 connections=G.degree(u), community=COMM[u], topics=[t for t,_ in UTOP[u].most_common(2)]) for u in top]

@app.get("/api/health")
def health(): return {"status":"ok","mode":"mock"}

@app.get("/api/dashboard")
def dashboard(platform: str="All", days: int=Query(7, ge=1, le=90)):
    ps = filt(platform, days); sd = sent_dist(ps); tr = trend_rows(ps, days); tl = hourly(ps, days*24)
    first, last = (sd["positive"], sd["positive"])
    if len(ps) > 20:
        h = sorted(ps, key=lambda p: p["timestamp"]); m = len(h)//2
        first, last = sent_dist(h[:m])["positive"], sent_dist(h[m:])["positive"]
    fastest = max(tr, key=lambda r: r["growth_pct"]) if tr else None
    spikes = [x for x in tl if x["spike"]]
    insights = [  # each tagged: computed = derived directly from data
        dict(kind="computed", text=f"Positive sentiment moved from {first}% to {last}% between first and second half of the period."),
        *([dict(kind="computed", text=f"'{fastest['topic']}' is the fastest-growing topic ({fastest['growth_pct']:+}%).")] if fastest else []),
        *([dict(kind="computed", text=f"{len(spikes)} abnormal activity hour(s) detected; peak {max(s['posts'] for s in spikes)} posts/hour.")] if spikes else [])]
    return dict(kpis=dict(total_posts=len(ps), active_users=len({p["user_id"] for p in ps}), positive_pct=sd["positive"],
        negative_pct=sd["negative"], trending_topics=sum(r["status"]=="Rising" for r in tr), influential_users=len(influencers())),
        sentiment=sd, insights=insights, top_trends=tr[:5], timeline=tl[-72:])

@app.get("/api/posts")
def posts(platform="All", days: int=30, sentiment: str=None, topic_id: int=None, limit: int=Query(50, le=200), offset: int=0):
    ps = [p for p in filt(platform, days) if (not sentiment or p["sentiment"]==sentiment) and (not topic_id or p["topic_id"]==topic_id)]
    ps.sort(key=lambda p: p["timestamp"], reverse=True); return dict(total=len(ps), items=ps[offset:offset+limit])

@app.get("/api/sentiment")
def sentiment(platform="All", days: int=7):
    ps = filt(platform, days); eng = lambda p: p["likes"]+p["shares"]*2+p["comments"]
    by_pl = {pl: sent_dist([p for p in ps if p["platform"]==pl]) for pl in ("X","Telegram")}
    top = lambda s: sorted([p for p in ps if p["sentiment"]==s], key=eng, reverse=True)[:5]
    return dict(distribution=sent_dist(ps), by_platform=by_pl, timeline=hourly(ps, days*24), top_positive=top("positive"), top_negative=top("negative"))

@app.get("/api/emotions")
def emotions(platform="All", days: int=7):
    ps = filt(platform, days); c = Counter(p["emotion"] for p in ps)
    return dict(counts={e: c.get(e,0) for l in EMO.values() for e in l}, percent=pct(c, len(ps)))

@app.get("/api/demographics")
def demographics():
    return dict(label="Estimated / Aggregate", note="Demographic information shown by this prototype is aggregate and estimated from public/synthetic indicators.", **D["demographics"])

@app.get("/api/trends")
def trends(platform="All", days: int=7): return trend_rows(filt(platform, days), days)

@app.get("/api/topics")
def topics(platform="All", days: int=7):
    ps = filt(platform, days); return [dict(r, name=r["topic"], posts=r["mentions"]) for r in trend_rows(ps, days)]

@app.get("/api/timeline")
def timeline(platform="All", days: int=7, topic_id: int=None, at: str=None):
    ps = filt(platform, days)
    if topic_id: ps = [p for p in ps if p["topic_id"]==topic_id]
    out = dict(points=hourly(ps, days*24))
    if at:  # click-through: posts/topics in that hour
        lo = dt.datetime.fromisoformat(at); hp = [p for p in ps if lo <= dt.datetime.fromisoformat(p["timestamp"]) < lo+dt.timedelta(hours=1)]
        out["posts"] = hp[:20]; out["topics"] = Counter(TOPIC[p["topic_id"]]["name"] for p in hp).most_common(5)
    return out

@app.get("/api/network")
def network(limit_nodes: int=Query(120, le=500)):
    keep = set(sorted(PR, key=PR.get, reverse=True)[:limit_nodes])
    return dict(nodes=[dict(id=n, pagerank=round(PR[n],4), community=COMM[n], degree=G.degree(n)) for n in keep],
                edges=[e for e in D["edges"] if e["source"] in keep and e["target"] in keep], communities=len(set(COMM.values())))

@app.get("/api/influencers")
def influencers_ep(limit: int=Query(10, le=50)): return influencers(limit)

@app.get("/api/diffusion/{topic_id}")
def diffusion(topic_id: int):
    if topic_id not in TOPIC: raise HTTPException(404, "Topic not found")
    tp = sorted([p for p in SRC.posts() if p["topic_id"]==topic_id], key=lambda p: p["timestamp"])
    seen, steps = set(), []
    for p in tp:
        c = COMM.get(p["user_id"])
        if c is not None and c not in seen:
            seen.add(c); steps.append(dict(community=f"Community {c}", first_user=p["user_id"], time=p["timestamp"]))
    return dict(topic=TOPIC[topic_id]["name"], origin=tp[0]["user_id"] if tp else None, first_detected=tp[0]["timestamp"] if tp else None,
        path=steps[:8], interactions=sum(p["likes"]+p["shares"]+p["comments"] for p in tp),
        sentiment_change=dict(early=sent_dist(tp[:len(tp)//2]), late=sent_dist(tp[len(tp)//2:])))

@app.get("/api/platforms")
def platforms(days: int=7):
    out = []
    for pl in ("X","Telegram"):
        ps = filt(pl, days); tr = trend_rows(ps, days); sd = sent_dist(ps); half = NOW - dt.timedelta(days=days/2)
        new = sum(dt.datetime.fromisoformat(p["timestamp"])>=half for p in ps)
        out.append(dict(platform=pl, posts=len(ps), engagement=sum(p["likes"]+p["shares"]+p["comments"] for p in ps),
            positive=sd["positive"], negative=sd["negative"], active_users=len({p["user_id"] for p in ps}),
            top_topic=tr[0]["topic"] if tr else None, growth_pct=round(100*(new-(len(ps)-new))/max(len(ps)-new,1),1)))
    return out

@app.get("/api/search")
def search(q: str=Query(..., min_length=1), days: int=30):
    ql = q.lower().lstrip("#"); ps = [p for p in filt("All", days) if ql in p["text"].lower() or ql==p["user_id"].lower()]
    tids = Counter(p["topic_id"] for p in ps); tr = {r["topic_id"]: r for r in trend_rows(filt("All", days), days)}
    users = Counter(p["user_id"] for p in ps)
    return dict(query=q, count=len(ps), sentiment=sent_dist(ps), posts=ps[:20],
        related_topics=[dict(tr[t], matches=n) for t, n in tids.most_common(5) if t in tr],
        influential_users=[dict(user=u, posts=n, pagerank=round(PR.get(u,0),4), connections=G.degree(u) if u in G else 0) for u,n in users.most_common(5)])
