-- Schema Canônico do Picorte (AD-2: 10 tabelas de domínio, zero workspace_id)
-- Compatível com PostgreSQL 16 e SQLite 3 (desenvolvimento local / testes)

CREATE TABLE IF NOT EXISTS publisher_policies (
    id TEXT PRIMARY KEY,
    publisher TEXT NOT NULL,
    game_slug TEXT NOT NULL UNIQUE,
    release_date TEXT,
    spoiler_window_days INTEGER NOT NULL DEFAULT 14,
    forbidden_content_rules TEXT NOT NULL DEFAULT '[]',
    has_licensed_radio_music INTEGER NOT NULL DEFAULT 0,
    violence_check_strict INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS sources (
    id TEXT PRIMARY KEY,
    name TEXT NOT NULL,
    platform TEXT NOT NULL,
    channel_handle TEXT NOT NULL,
    permission_status TEXT NOT NULL DEFAULT 'desconhecida',
    permission_evidence_url TEXT DEFAULT '',
    permission_basis TEXT NOT NULL DEFAULT 'explicita',
    credit_template TEXT DEFAULT 'Créditos: @{handle}',
    default_game_slug TEXT DEFAULT '',
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS campaigns (
    id TEXT PRIMARY KEY,
    source_id TEXT NOT NULL REFERENCES sources(id),
    game_slug TEXT NOT NULL DEFAULT '',
    cpm_brl REAL NOT NULL DEFAULT 0.0,
    required_tags TEXT NOT NULL DEFAULT '[]',
    starts_at TEXT NOT NULL,
    expires_at TEXT,
    is_active INTEGER NOT NULL DEFAULT 1,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS videos (
    id TEXT PRIMARY KEY,
    source_id TEXT REFERENCES sources(id),
    origin_type TEXT NOT NULL DEFAULT 'vod',
    source_url TEXT NOT NULL,
    game_slug TEXT NOT NULL DEFAULT '',
    duration_seconds REAL NOT NULL DEFAULT 0.0,
    workdir_path TEXT NOT NULL DEFAULT '',
    status TEXT NOT NULL DEFAULT 'queued',
    archived_at TEXT,
    created_at TEXT NOT NULL,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS clips (
    id TEXT PRIMARY KEY,
    video_id TEXT NOT NULL REFERENCES videos(id),
    parent_long_clip_id TEXT REFERENCES clips(id),
    format_type TEXT NOT NULL DEFAULT 'short_9_16',
    ab_variant INTEGER NOT NULL DEFAULT 1,
    start_sec REAL NOT NULL,
    end_sec REAL NOT NULL,
    score_chat REAL,
    score_audio REAL,
    score_visual REAL,
    score_text REAL,
    score_overall REAL NOT NULL DEFAULT 0.0,
    ypp_transform_score INTEGER,
    phash_signature TEXT NOT NULL DEFAULT '',
    llm_mode_used TEXT NOT NULL DEFAULT 'heuristic',
    risk_status TEXT NOT NULL DEFAULT 'pending',
    mp4_path TEXT NOT NULL DEFAULT '',
    thumbnail_path TEXT NOT NULL DEFAULT '',
    proposed_title TEXT NOT NULL DEFAULT '',
    context_banner_2s TEXT NOT NULL DEFAULT '',
    pinned_comment_debate TEXT NOT NULL DEFAULT '',
    archived_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS social_accounts (
    id TEXT PRIMARY KEY,
    platform TEXT NOT NULL,
    account_handle TEXT NOT NULL,
    encrypted_tokens_b64 TEXT NOT NULL DEFAULT '',
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS publications (
    id TEXT PRIMARY KEY,
    clip_id TEXT NOT NULL REFERENCES clips(id),
    social_account_id TEXT REFERENCES social_accounts(id),
    platform TEXT NOT NULL,
    publish_mode TEXT NOT NULL DEFAULT 'assisted_manual',
    status TEXT NOT NULL DEFAULT 'fila',
    external_post_id TEXT NOT NULL DEFAULT '',
    external_url TEXT NOT NULL DEFAULT '',
    related_video_external_id TEXT NOT NULL DEFAULT '',
    scheduled_for TEXT,
    published_at TEXT,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS metrics_snapshots (
    id TEXT PRIMARY KEY,
    publication_id TEXT NOT NULL REFERENCES publications(id),
    window_label TEXT NOT NULL,
    views INTEGER NOT NULL DEFAULT 0,
    likes INTEGER NOT NULL DEFAULT 0,
    comments INTEGER NOT NULL DEFAULT 0,
    shares INTEGER NOT NULL DEFAULT 0,
    avg_view_pct REAL NOT NULL DEFAULT 0.0,
    stayed_to_watch_3s_pct REAL NOT NULL DEFAULT 0.0,
    computed_reward REAL NOT NULL DEFAULT 0.0,
    captured_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS claims_events (
    id TEXT PRIMARY KEY,
    publication_id TEXT REFERENCES publications(id),
    source_id TEXT NOT NULL REFERENCES sources(id),
    claim_type TEXT NOT NULL,
    details TEXT NOT NULL DEFAULT '',
    triggered_global_pause INTEGER NOT NULL DEFAULT 1,
    detected_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS bandit_state (
    factor_key TEXT PRIMARY KEY,
    mu REAL NOT NULL DEFAULT 1.0,
    sigma_sq REAL NOT NULL DEFAULT 1.0,
    observations_count INTEGER NOT NULL DEFAULT 0,
    updated_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS dataset_samples (
    id TEXT PRIMARY KEY,
    clip_id TEXT NOT NULL REFERENCES clips(id),
    label INTEGER NOT NULL,
    reward_value REAL NOT NULL,
    bundle_dir_path TEXT NOT NULL,
    created_at TEXT NOT NULL
);

-- História 6.6 (B10): decisões da Revisão por corte. 👍/👎 é opcional (C3) e separado do descarte.
CREATE TABLE IF NOT EXISTS revisao_cortes (
    clip_id TEXT PRIMARY KEY,
    rotulo INTEGER,
    motivo TEXT NOT NULL DEFAULT '',
    descartado INTEGER NOT NULL DEFAULT 0,
    exemplo_ouro INTEGER NOT NULL DEFAULT 0,
    atualizado_em TEXT NOT NULL
);
