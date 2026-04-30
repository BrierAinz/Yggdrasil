-- User Profiles DB for Cortana v2.2+
PRAGMA foreign_keys = ON;

CREATE TABLE IF NOT EXISTS user_profiles (
    user_id TEXT PRIMARY KEY,
    name TEXT,
    preferred_tone TEXT CHECK(preferred_tone IN ('formal', 'casual', 'technical')) DEFAULT 'casual',
    favorite_tools TEXT, -- JSON array: ["CodeAnalyzer", "ImageProcessor"]
    avg_session_duration INTEGER DEFAULT 0,
    success_rate REAL DEFAULT 0.0,
    total_interactions INTEGER DEFAULT 0,
    last_interaction DATETIME,
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS user_preferences (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id TEXT,
    key TEXT,
    value TEXT,
    updated_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
);

CREATE TABLE IF NOT EXISTS session_context (
    session_id TEXT PRIMARY KEY,
    user_id TEXT,
    active_files TEXT, -- JSON ["file1.py", "file2.py"]
    working_directory TEXT,
    recent_urls TEXT, -- JSON ["https://github.com/..."]
    pending_tasks TEXT, -- JSON ["fix bug in auth", "write tests"]
    created_at DATETIME DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (user_id) REFERENCES user_profiles(user_id)
);

-- Índices para performance
CREATE INDEX idx_user_last_interaction ON user_profiles(last_interaction);
CREATE INDEX idx_session_user ON session_context(user_id);
CREATE INDEX idx_prefs_user_key ON user_preferences(user_id, key);

-- Insert demo user for testing
INSERT OR IGNORE INTO user_profiles (user_id, name, preferred_tone, favorite_tools) VALUES
('demo_user', 'Developer', 'casual', '["CodeAnalyzer", "ImageProcessor"]');
