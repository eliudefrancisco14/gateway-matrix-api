-- Ficheiro SQL para PostgreSQL
-- Contém todas as instruções CREATE TABLE e seeds iniciais.

-- 1. Extensão para geração de UUIDs
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";

-- 2. Definição dos Tipos ENUM

-- Tabela sources
CREATE TYPE source_protocol AS ENUM ('srt', 'udp', 'rtsp', 'http_ts', 'hls', 'dash', 'youtube', 'file');
CREATE TYPE source_type AS ENUM ('direct_link', 'satellite_encoder', 'local_device', 'cloud_origin');
CREATE TYPE source_status AS ENUM ('online', 'offline', 'unstable', 'connecting', 'error');

-- Tabela channels
CREATE TYPE channel_status AS ENUM ('live', 'offline', 'scheduled', 'error', 'maintenance');
CREATE TYPE output_format AS ENUM ('hls', 'dash', 'both');

-- Tabela channel_events
CREATE TYPE event_type AS ENUM ('started', 'stopped', 'failover', 'error', 'recovered', 'reconnecting', 'source_changed');
CREATE TYPE triggered_by AS ENUM ('system', 'user', 'scheduler', 'failover_rule');

-- Tabela recordings
CREATE TYPE recording_status AS ENUM ('recording', 'completed', 'failed', 'processing');

-- Tabela media_segments
CREATE TYPE segment_type AS ENUM ('video', 'audio', 'both');
CREATE TYPE segment_status AS ENUM ('pending', 'processing', 'completed', 'failed');

-- Tabela ai_analyses
CREATE TYPE analysis_type AS ENUM ('transcription', 'summary', 'entities', 'emotions', 'themes', 'full');
CREATE TYPE analysis_status AS ENUM ('queued', 'processing', 'completed', 'failed');

-- Tabela ai_insights
CREATE TYPE insight_type AS ENUM ('alert', 'recommendation', 'anomaly', 'trend', 'summary');
CREATE TYPE severity AS ENUM ('info', 'warning', 'critical');

-- Tabela summaries
CREATE TYPE summary_type AS ENUM ('brief', 'detailed', 'bullets', 'executive');

-- Tabela users
CREATE TYPE user_role AS ENUM ('admin', 'operator', 'viewer');

-- Tabela alerts

CREATE TYPE alert_severity AS ENUM ('critical', 'error', 'warning', 'info');

-- 3. Criação das Tabelas

-- 3.1 Tabela users
CREATE TABLE users (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    email VARCHAR(255) UNIQUE NOT NULL,
    password_hash VARCHAR(255) NOT NULL, -- Hash da senha (bcrypt)
    name VARCHAR(255) NOT NULL,
    role user_role NOT NULL,
    avatar_url TEXT,
    is_active BOOLEAN DEFAULT TRUE,
    last_login_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP,
    preferences JSONB
);

-- 3.2 Tabela system_config
CREATE TABLE system_config (
    key VARCHAR(100) PRIMARY KEY,
    value JSONB,
    description TEXT,
    updated_at TIMESTAMP,
    updated_by UUID REFERENCES users(id)
);

-- 3.3 Tabela audit_logs
CREATE TABLE audit_logs (
    id BIGSERIAL PRIMARY KEY,
    user_id UUID REFERENCES users(id),
    action VARCHAR(100) NOT NULL,
    entity_type VARCHAR(50) NOT NULL,
    entity_id UUID,
    old_values JSONB,
    new_values JSONB,
    ip_address INET,
    user_agent TEXT,
    timestamp TIMESTAMP DEFAULT NOW()
);

-- 3.4 Tabela sources
CREATE TABLE sources (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    protocol source_protocol NOT NULL,
    source_type source_type NOT NULL,
    endpoint_url TEXT NOT NULL,
    backup_url TEXT,
    connection_params JSONB,
    status source_status NOT NULL,
    last_seen_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP,
    created_by UUID REFERENCES users(id),
    is_active BOOLEAN DEFAULT TRUE,
    meta_data JSONB
);

-- 3.5 Tabela source_metrics
CREATE TABLE source_metrics (
    id BIGSERIAL PRIMARY KEY,
    source_id UUID REFERENCES sources(id) ON DELETE CASCADE,
    timestamp TIMESTAMP NOT NULL,
    bitrate_kbps INTEGER,
    fps DECIMAL(5,2),
    latency_ms INTEGER,
    packet_loss_percent DECIMAL(5,2),
    jitter_ms INTEGER,
    buffer_health DECIMAL(3,2),
    video_codec VARCHAR(50),
    audio_codec VARCHAR(50),
    resolution VARCHAR(20),
    error_count INTEGER DEFAULT 0
);
-- Índice recomendado para consultas de séries temporais
CREATE INDEX idx_source_metrics_source_time ON source_metrics (source_id, timestamp DESC);

-- 3.6 Tabela channels
CREATE TABLE channels (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    name VARCHAR(255) NOT NULL,
    slug VARCHAR(100) UNIQUE NOT NULL,
    source_id UUID REFERENCES sources(id),
    fallback_source_id UUID REFERENCES sources(id),
    status channel_status NOT NULL,
    output_format output_format NOT NULL,
    thumbnail_url TEXT,
    thumbnail_updated_at TIMESTAMP,
    category VARCHAR(100),
    priority INTEGER DEFAULT 0,
    max_viewers INTEGER,
    created_at TIMESTAMP DEFAULT NOW(),
    updated_at TIMESTAMP,
    created_by UUID REFERENCES users(id),
    is_active BOOLEAN DEFAULT TRUE,
    transcoding_profile VARCHAR(100),
    recording_enabled BOOLEAN DEFAULT FALSE
);

-- 3.7 Tabela channel_events
CREATE TABLE channel_events (
    id BIGSERIAL PRIMARY KEY,
    channel_id UUID REFERENCES channels(id) ON DELETE CASCADE,
    event_type event_type NOT NULL,
    timestamp TIMESTAMP NOT NULL,
    details JSONB,
    triggered_by triggered_by NOT NULL,
    user_id UUID REFERENCES users(id)
);

-- 3.8 Tabela recordings
CREATE TABLE recordings (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    channel_id UUID REFERENCES channels(id),
    started_at TIMESTAMP NOT NULL,
    ended_at TIMESTAMP,
    duration_seconds INTEGER,
    file_path TEXT,
    file_size_bytes BIGINT,
    format VARCHAR(20),
    status recording_status NOT NULL,
    meta_data JSONB
);

-- 3.9 Tabela media_segments
CREATE TABLE media_segments (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    channel_id UUID REFERENCES channels(id),
    recording_id UUID REFERENCES recordings(id),
    segment_type segment_type NOT NULL,
    start_time TIMESTAMP NOT NULL,
    end_time TIMESTAMP NOT NULL,
    duration_seconds INTEGER NOT NULL,
    file_path TEXT NOT NULL,
    file_size_bytes BIGINT,
    status segment_status NOT NULL,
    created_at TIMESTAMP DEFAULT NOW(),
    processed_at TIMESTAMP
);

-- 3.10 Tabela ai_analyses
CREATE TABLE ai_analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    segment_id UUID REFERENCES media_segments(id),
    channel_id UUID REFERENCES channels(id),
    analysis_type analysis_type NOT NULL,
    status analysis_status NOT NULL,
    started_at TIMESTAMP,
    completed_at TIMESTAMP,
    model_used VARCHAR(100),
    model_version VARCHAR(50),
    processing_time_ms INTEGER,
    error_message TEXT,
    created_at TIMESTAMP DEFAULT NOW(),
    created_by UUID REFERENCES users(id)
);

-- 3.11 Tabela transcriptions
CREATE TABLE transcriptions (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_id UUID UNIQUE REFERENCES ai_analyses(id),
    full_text TEXT,
    language VARCHAR(10),
    confidence DECIMAL(3,2),
    word_count INTEGER,
    segments JSONB
);

-- 3.12 Tabela content_analyses
CREATE TABLE content_analyses (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_id UUID UNIQUE REFERENCES ai_analyses(id),
    themes JSONB,
    entities JSONB,
    emotions JSONB,
    dominant_emotion VARCHAR(50),
    sentiment_score DECIMAL(3,2),
    keywords JSONB,
    categories JSONB
);

-- 3.13 Tabela summaries
CREATE TABLE summaries (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    analysis_id UUID UNIQUE REFERENCES ai_analyses(id),
    summary_type summary_type NOT NULL,
    content TEXT,
    bullet_points JSONB,
    key_moments JSONB,
    word_count INTEGER
);

-- 3.14 Tabela ai_insights
CREATE TABLE ai_insights (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    channel_id UUID REFERENCES channels(id),
    analysis_id UUID REFERENCES ai_analyses(id),
    insight_type insight_type NOT NULL,
    severity severity NOT NULL,
    title VARCHAR(255) NOT NULL,
    description TEXT NOT NULL,
    data JSONB,
    is_read BOOLEAN DEFAULT FALSE,
    is_actionable BOOLEAN NOT NULL,
    action_taken BOOLEAN DEFAULT FALSE,
    created_at TIMESTAMP DEFAULT NOW(),
    expires_at TIMESTAMP
);

-- 3.15 Tabela alerts 
CREATE TABLE alerts (
    id UUID PRIMARY KEY DEFAULT uuid_generate_v4(),
    severity alert_severity NOT NULL,
    message TEXT NOT NULL,
    source_id UUID REFERENCES sources(id),
    channel_id UUID REFERENCES channels(id),
    acknowledged BOOLEAN DEFAULT FALSE,
    acknowledged_by UUID REFERENCES users(id),
    acknowledged_at TIMESTAMP,
    created_at TIMESTAMP DEFAULT NOW()
);

-- Índices para otimização de consultas na tabela alerts
CREATE INDEX idx_alerts_severity ON alerts(severity);
CREATE INDEX idx_alerts_acknowledged ON alerts(acknowledged);
CREATE INDEX idx_alerts_created_at ON alerts(created_at DESC);

-- 4. Seeds Iniciais

-- 4.1 Criação do utilizador admin
-- Email: efrancisco@underall.com
-- Senha: under2025
-- Role: admin
-- Nota: O hash abaixo é um placeholder SHA-256 (738dfa036db1278dfde3d62d1804255e011a68adb3efc56a0aaa50121c79c06d)
-- O utilizador deve gerar um hash bcrypt real (custo 12) e substituí-lo.
INSERT INTO users (id, email, password_hash, name, role, is_active, created_at) VALUES
(
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11', -- UUID fixo para o admin
    'efrancisco@underall.com',
    '$2b$12$9BN02D1XXrIPJQ8R3UeIreKhHNogGSWfb3aYcqsechm3NnGJQeV1C', -- Placeholder: SHA-256 de 'under2025' com prefixo bcrypt
    'Admin Underall',
    'ADMIN',
    TRUE,
    NOW()
);

-- 4.2 Configuração inicial (exemplo)
INSERT INTO system_config (key, value, description, updated_at, updated_by) VALUES
(
    'max_channels',
    '{"limit": 100}',
    'Número máximo de canais permitidos no sistema.',
    NOW(),
    'a0eebc99-9c0b-4ef8-bb6d-6bb9bd380a11'
);

-- FIM DO SCRIPT SQL
