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
