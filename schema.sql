CREATE TABLE platforms (id SERIAL PRIMARY KEY, name TEXT UNIQUE NOT NULL);
CREATE TABLE users (id TEXT PRIMARY KEY, platform_id INT REFERENCES platforms(id), followers INT DEFAULT 0); -- anonymized IDs only
CREATE TABLE topics (id SERIAL PRIMARY KEY, name TEXT NOT NULL, keywords TEXT[]);
CREATE TABLE hashtags (id SERIAL PRIMARY KEY, tag TEXT UNIQUE NOT NULL, topic_id INT REFERENCES topics(id));
CREATE TABLE posts (id BIGSERIAL PRIMARY KEY, platform_id INT REFERENCES platforms(id), user_id TEXT REFERENCES users(id),
  text TEXT, "timestamp" TIMESTAMPTZ NOT NULL, likes INT DEFAULT 0, shares INT DEFAULT 0, comments INT DEFAULT 0,
  sentiment TEXT CHECK (sentiment IN ('positive','neutral','negative')), emotion TEXT, topic_id INT REFERENCES topics(id));
CREATE TABLE comments (id BIGSERIAL PRIMARY KEY, post_id BIGINT REFERENCES posts(id), user_id TEXT REFERENCES users(id), text TEXT, "timestamp" TIMESTAMPTZ NOT NULL);
CREATE TABLE interactions (id BIGSERIAL PRIMARY KEY, post_id BIGINT REFERENCES posts(id), user_id TEXT REFERENCES users(id), type TEXT, "timestamp" TIMESTAMPTZ NOT NULL);
CREATE TABLE sentiment_results (post_id BIGINT PRIMARY KEY REFERENCES posts(id), sentiment TEXT, emotion TEXT, confidence REAL, model TEXT);
CREATE TABLE demographics (id SERIAL PRIMARY KEY, category TEXT, label TEXT, percent REAL, is_estimated BOOLEAN DEFAULT TRUE); -- aggregate only
CREATE TABLE network_edges (id BIGSERIAL PRIMARY KEY, source TEXT REFERENCES users(id), target TEXT REFERENCES users(id), type TEXT, "timestamp" TIMESTAMPTZ);
CREATE INDEX idx_posts_ts ON posts("timestamp"); CREATE INDEX idx_posts_platform ON posts(platform_id, "timestamp");
CREATE INDEX idx_posts_topic ON posts(topic_id); CREATE INDEX idx_posts_sentiment ON posts(sentiment);
CREATE INDEX idx_edges_src ON network_edges(source); CREATE INDEX idx_edges_tgt ON network_edges(target);
