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
