CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

CREATE TABLE meetings (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  title TEXT NOT NULL,
  meeting_date DATE NOT NULL,
  source TEXT NOT NULL,
  raw_transcript TEXT NOT NULL,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

CREATE TABLE notes (
  id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
  meeting_id UUID REFERENCES meetings(id) ON DELETE CASCADE,
  summary TEXT,
  action_items JSONB,
  key_takeaways JSONB,
  topics JSONB,
  next_steps JSONB,
  created_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
);

ALTER TABLE notes 
ADD COLUMN IF NOT EXISTS decisions JSONB,
ADD COLUMN IF NOT EXISTS next_steps JSONB,
ADD COLUMN IF NOT EXISTS llm_raw TEXT;