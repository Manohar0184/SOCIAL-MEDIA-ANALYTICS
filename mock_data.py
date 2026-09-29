"""Synthetic dataset generator (500 users, 2000 posts, 1000 interactions, 20 topics, 10 hashtags)."""
import random, datetime as dt
R = random.Random(42)
PLATFORMS = ["X", "Telegram"]
TOPICS = [(n, k) for n, k in [
 ("Chennai Metro Expansion","metro chennai transport phase2"),("AI in Education","ai students education learning"),
 ("Monsoon Preparedness","rain flood drainage alert"),("EV Adoption","ev charging battery subsidy"),
 ("Startup Funding","startup funding vc founders"),("Cricket League","cricket match team ipl"),
 ("Healthcare Access","hospital doctors vaccine clinic"),("Film Releases","movie trailer cinema review"),
 ("Fuel Prices","fuel petrol price tax"),("Tech Layoffs","layoffs jobs hiring it"),
 ("Smart Cities","smartcity iot urban data"),("Online Exams","exam results neet portal"),
 ("Water Supply","water tank supply shortage"),("Air Quality","aqi pollution smog health"),
 ("Digital Payments","upi payments fintech bank"),("Local Elections","election voting candidates booth"),
 ("Music Festival","concert music festival tickets"),("Farm Policy","farmers msp crop policy"),
 ("Cybersecurity","phishing scam breach security"),("Space Missions","isro launch rocket satellite")]]
TOPICS = [dict(id=i+1, name=n, keywords=k.split()) for i,(n,k) in enumerate(TOPICS)]
HASHTAGS = ["#ChennaiMetro","#AIEdu","#MonsoonAlert","#EVIndia","#StartupTN","#IPL","#HealthFirst","#Kollywood","#FuelPrice","#TechJobs"]
EMO = {"positive":["Supportive","Excitement"],"negative":["Against","Anxiety","Anger","Sadness","Sarcasm"],"neutral":["Neutral"]}
DEMO = {
 "age":{"18-24":28,"25-34":37,"35-44":22,"45+":13},
 "region":{"Tamil Nadu":46,"Karnataka":17,"Kerala":12,"Andhra Pradesh":11,"Other":14},
 "language":{"Tamil":38,"English":31,"Hindi":11,"Telugu":9,"Malayalam":6,"Other":5},
 "interest":{"Technology":27,"Education":19,"Business":16,"Sports":14,"Entertainment":15,"Healthcare":9}}

def build(now=None):
    now = now or dt.datetime.utcnow().replace(minute=0, second=0, microsecond=0)
    users = [dict(id=f"User_{i:03d}", platform=R.choice(PLATFORMS), followers=int(R.paretovariate(1.2)*50)) for i in range(1,501)]
    spike_topic = 1
    posts = []
    for i in range(1, 2001):
        # 30-day span; ~35% of posts squeezed into a 3h burst 5h ago (spike)
        if R.random() < 0.35: ts = now - dt.timedelta(hours=5, minutes=R.randint(0,180))
        else: ts = now - dt.timedelta(minutes=R.randint(0, 30*24*60))
        burst = ts > now - dt.timedelta(hours=9) and ts < now - dt.timedelta(hours=1)
        t = TOPICS[spike_topic-1] if burst and R.random()<.7 else R.choice(TOPICS)
        s = R.choices(["positive","neutral","negative"], [52,30,18] if not burst else [60,25,15])[0]
        kw = R.sample(t["keywords"], 2)
        u = R.choice(users)
        posts.append(dict(id=i, platform=u["platform"], user_id=u["id"], timestamp=ts.isoformat(),
            text=f"{t['name']}: thoughts on {kw[0]} and {kw[1]} {HASHTAGS[t['id']%10-1]}",
            likes=int(R.expovariate(1/40)), shares=int(R.expovariate(1/8)), comments=int(R.expovariate(1/5)),
            sentiment=s, emotion=R.choice(EMO[s]), topic_id=t["id"], hashtag=HASHTAGS[t["id"]%10-1]))
    edges = []
    hubs = R.sample(users, 15)
    for _ in range(1000):
        a = R.choice(users)["id"]; b = R.choice(hubs)["id"] if R.random()<.5 else R.choice(users)["id"]
        if a != b: edges.append(dict(source=a, target=b, type=R.choice(["reply","mention","share"]),
                                     timestamp=(now - dt.timedelta(minutes=R.randint(0,7*24*60))).isoformat()))
    return dict(now=now, users=users, posts=posts, edges=edges, topics=TOPICS, hashtags=HASHTAGS, demographics=DEMO)
