-- ParhLo schema (Neon Postgres + pgvector). Idempotent: safe to run on every deploy.
create extension if not exists vector;

create table if not exists users (
    id              uuid primary key default gen_random_uuid(),
    name            text not null,
    email           text,
    city            text not null default 'Lahore',
    lat             double precision not null default 31.5497,
    lon             double precision not null default 74.3436,
    reading_minutes int  not null default 10,
    region_mix      real not null default 0.5,          -- 0 = global only, 1 = Pakistan only
    created_at      timestamptz not null default now()
);

alter table users add column if not exists clerk_id text unique;
alter table users add column if not exists is_demo boolean not null default false;
alter table users add column if not exists onboarded boolean not null default false;
alter table users add column if not exists google_sub text unique;
-- Public sample readers on /demo: shared by every visitor, so read-only (guests are is_demo but not persona).
alter table users add column if not exists persona boolean not null default false;
create unique index if not exists users_email_unique on users (lower(email)) where email is not null;

-- One-time email codes (only a hash is stored).
create table if not exists otp_codes (
    id          bigserial primary key,
    email       text not null,
    code_hash   text not null,
    attempts    int not null default 0,
    used        boolean not null default false,
    expires_at  timestamptz not null,
    created_at  timestamptz not null default now()
);
create index if not exists otp_codes_email on otp_codes (lower(email), created_at desc);

-- Explicit, editable preferences. Topic weights are learned over time.
create table if not exists profiles (
    user_id          uuid primary key references users(id) on delete cascade,
    topics           jsonb not null default '{}',        -- {"ai": 0.9, "cricket": 0.6}
    entities         jsonb not null default '[]',        -- ["Babar Azam", "OpenAI"]
    about            text,
    source_affinity  jsonb not null default '{}',        -- {"Dawn": 0.2}
    updated_at       timestamptz not null default now()
);

-- Multi-interest memory: each anchor is something the reader cares about (or not).
-- An article's personal score is its best match against these anchors.
create table if not exists interest_anchors (
    id          bigserial primary key,
    user_id     uuid not null references users(id) on delete cascade,
    label       text not null,                           -- "Formula 1" / liked article title
    kind        text not null,                           -- onboarding | entity | liked | clicked | disliked
    weight      real not null,                           -- negative = avoid
    article_id  bigint,
    embedding   vector(1536) not null,
    created_at  timestamptz not null default now()
);
create index if not exists interest_anchors_user on interest_anchors(user_id);

-- Learning history for the "your paper is learning" panel.
create table if not exists profile_snapshots (
    id        bigserial primary key,
    user_id   uuid not null references users(id) on delete cascade,
    taken_at  timestamptz not null default now(),
    topics    jsonb not null,
    changes   jsonb not null default '[]'                -- [{"topic": "f1", "from": .3, "to": .6, "why": "..."}]
);

create table if not exists articles (
    id               bigserial primary key,
    url              text unique not null,
    source           text not null,
    source_region    text not null default 'global',     -- pakistan | global
    title            text not null,
    rss_summary      text,
    content          text,                               -- full text, extracted lazily when selected
    image_url        text,
    published_at     timestamptz,
    fetched_at       timestamptz not null default now(),
    topics           text[] not null default '{}',
    embedding        vector(1536),
    cluster_id       bigint,                             -- same story across outlets
    ai_summary       text,
    ai_points        jsonb,
    summary_verified boolean,
    summarized_at    timestamptz
);
create index if not exists articles_published on articles(published_at desc);
-- Jev decisions (null = not checked yet)
alter table articles add column if not exists importance real;        -- 0..1 (Jev Score, 5 levels)
alter table articles add column if not exists junk real;              -- 0..1 probability it is not real news
alter table articles add column if not exists topic_confidence real;  -- Jev Choice confidence for topics[1]
alter table articles add column if not exists jev_checked_at timestamptz;
create index if not exists articles_cluster on articles(cluster_id);
create index if not exists articles_embedding on articles using hnsw (embedding vector_cosine_ops);
-- SWS (Smart Web Search): where we found the article, and which country and language it belongs to.
alter table articles add column if not exists origin text not null default 'rss';  -- rss | gnews | gdelt | web
alter table articles add column if not exists country text;                        -- e.g. "Uganda" (null = unknown)
alter table articles add column if not exists language text;                       -- ISO 639-1 of the page, e.g. "en"

-- SWS runs (every ~15 minutes): one row per run, with what it read and kept. Also the run lock:
-- only one 'running' row can exist; a run stuck for 10+ minutes is marked failed by the next one.
create table if not exists sws_runs (
    id           bigserial primary key,
    started_at   timestamptz not null default now(),
    finished_at  timestamptz,
    status       text not null default 'running',            -- running | done | failed
    gdelt_slots  text[] not null default '{}',               -- GDELT 15-minute windows read, e.g. 20261019081500
    feeds        int not null default 0,                     -- Google News feeds read
    report       jsonb not null default '{}',
    error        text
);
create unique index if not exists sws_runs_one_running on sws_runs ((true)) where status = 'running';
create index if not exists sws_runs_started on sws_runs (started_at desc);
-- Stories the SWS gate rejected (blocked or matching no reader): skipped for 3 days instead of being
-- downloaded and embedded again every 15 minutes. (Items cut only by the per-run cap are not listed.)
create table if not exists sws_rejected (
    url          text primary key,
    rejected_at  timestamptz not null default now()
);
-- SWS on-demand searches (a reader follows something new, or asks Ask to search the web): daily limit per
-- reader and the Tavily monthly budget are counted from here.
create table if not exists sws_instant (
    id          bigserial primary key,
    user_id     uuid references users(id) on delete cascade,
    kind        text not null,                     -- follow | ask
    query       text not null,
    tavily      boolean not null default false,    -- used a Tavily credit
    found       int not null default 0,
    added       int not null default 0,
    created_at  timestamptz not null default now()
);
create index if not exists sws_instant_user on sws_instant (user_id, created_at desc);
-- SWS query planner: every search SWS runs, each on its own schedule. Searches that keep finding new stories
-- run more often (down to 15 min); quiet ones back off (up to hours). See app/parhlo/sws/planner.py.
create table if not exists sws_queries (
    id            bigserial primary key,
    kind          text not null,                    -- edition | country | follow | breaking
    query         text not null,                    -- edition code (UG), country name, followed name, keywords
    priority      real not null default 1,
    interval_min  int not null default 60,
    next_run_at   timestamptz not null default now(),
    last_run_at   timestamptz,
    last_new      int not null default 0,           -- new stories found on the last run
    hits          int not null default 0,           -- runs that found something new
    misses        int not null default 0,
    created_at    timestamptz not null default now(),
    unique (kind, query)
);
create index if not exists sws_queries_due on sws_queries (next_run_at);
-- Which followed name / "About you" phrase a story was found by searching for (lower-case). Ranking treats
-- these as certain matches for readers who follow that term — a phrase and a headline are often far apart
-- in embedding space ("car accident news" vs "1 killed in crash on Hwy 210": cosine 0.31).
create table if not exists article_terms (
    article_id  bigint not null references articles(id) on delete cascade,
    term        text not null,
    primary key (article_id, term)
);
create index if not exists article_terms_term on article_terms (term);

-- A frozen daily paper: web view and PDF render from the same JSON.
create table if not exists editions (
    id            bigserial primary key,
    user_id       uuid not null references users(id) on delete cascade,
    edition_date  date not null,
    number        int not null,
    data          jsonb not null,
    pdf_key       text,
    audio_key     text,
    created_at    timestamptz not null default now(),
    unique (user_id, edition_date)
);

create table if not exists events (
    id          bigserial primary key,
    user_id     uuid not null references users(id) on delete cascade,
    edition_id  bigint references editions(id) on delete set null,
    article_id  bigint references articles(id) on delete set null,
    type        text not null,                           -- open | dwell | like | dislike | skip | save | quiz
    value       real,
    created_at  timestamptz not null default now()
);
create index if not exists events_user on events(user_id, created_at desc);

-- Current like/dislike/save per story (events keep the full history for learning).
create table if not exists article_state (
    user_id     uuid not null references users(id) on delete cascade,
    article_id  bigint not null references articles(id) on delete cascade,
    reaction    text,                                    -- like | dislike | null
    saved       boolean not null default false,
    updated_at  timestamptz not null default now(),
    primary key (user_id, article_id)
);
create index if not exists article_state_saved on article_state(user_id, updated_at desc) where saved;

-- Friends: a personal invite link; one switch lets friends' likes shape each other's papers.
alter table users add column if not exists invite_code text unique;
alter table users add column if not exists learn_from_friends boolean not null default false;

create table if not exists friendships (
    user_id     uuid not null references users(id) on delete cascade,
    friend_id   uuid not null references users(id) on delete cascade,
    created_at  timestamptz not null default now(),
    primary key (user_id, friend_id)                     -- stored in both directions
);

create table if not exists notifications (
    id          bigserial primary key,
    user_id     uuid not null references users(id) on delete cascade,
    kind        text not null,                           -- invite_accepted | friend_added | paper_ready | friends_learning
    actor_id    uuid references users(id) on delete cascade,
    data        jsonb not null default '{}',
    read_at     timestamptz,
    created_at  timestamptz not null default now()
);
create index if not exists notifications_user on notifications(user_id, created_at desc);

-- One paper build at a time per reader and date (a second request waits for the first).
create table if not exists edition_jobs (
    user_id       uuid not null references users(id) on delete cascade,
    edition_date  date not null,
    started_at    timestamptz not null default now(),
    primary key (user_id, edition_date)
);

-- Morning email: an outbox queue in Postgres (one job per reader per paper; workers claim with SKIP LOCKED).
alter table users add column if not exists email_morning boolean not null default true;
create table if not exists email_jobs (
    id          bigserial primary key,
    user_id     uuid not null references users(id) on delete cascade,
    edition_id  bigint not null references editions(id) on delete cascade,
    kind        text not null default 'morning',         -- morning | manual
    status      text not null default 'queued',          -- queued | sending | sent | failed | skipped
    attempts    int not null default 0,
    last_error  text,
    run_after   timestamptz not null default now(),
    claimed_at  timestamptz,
    sent_at     timestamptz,
    created_at  timestamptz not null default now()
);
create unique index if not exists email_jobs_once on email_jobs(user_id, edition_id) where kind = 'morning';
create index if not exists email_jobs_due on email_jobs(run_after) where status = 'queued';

-- Interest changes reprint today's paper (debounced by the n8n workflow; see app/parhlo/refresh.py).
alter table users add column if not exists interests_changed_at timestamptz;

-- Help & contact messages (also emailed to the team).
create table if not exists support_messages (
    id          bigserial primary key,
    user_id     uuid references users(id) on delete set null,
    name        text not null,
    email       text not null,
    topic       text not null,
    message     text not null,
    page        text,
    status      text not null default 'new',
    created_at  timestamptz not null default now()
);
create index if not exists support_messages_email on support_messages(lower(email), created_at desc);
