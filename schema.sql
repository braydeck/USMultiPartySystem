CREATE TABLE IF NOT EXISTS quiz_response (
  id            TEXT PRIMARY KEY,
  created_at    TEXT NOT NULL,
  result_party  TEXT NOT NULL,
  answers       TEXT NOT NULL,
  scores        TEXT NOT NULL,
  vibe          TEXT,
  referrer      TEXT,
  country       TEXT,
  quiz_version  TEXT NOT NULL
);
CREATE INDEX IF NOT EXISTS idx_quiz_response_party ON quiz_response (result_party);
CREATE INDEX IF NOT EXISTS idx_quiz_response_created ON quiz_response (created_at);
