from yoyo import step


steps = [
    step(
        """
        CREATE TABLE IF NOT EXISTS refresh_tokens (
            token_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            token_hash VARCHAR(255) NOT NULL,
            device_info VARCHAR(255),
            expires_at TIMESTAMPTZ NOT NULL,
            created_at TIMESTAMPTZ DEFAULT NOW(),
            revoked BOOLEAN DEFAULT false
        )
        """,
        """
        DROP TABLE IF EXISTS refresh_tokens
        """
    ),
    step(
        """
        CREATE INDEX IF NOT EXISTS idx_refresh_tokens_user ON refresh_tokens(user_id)
        """
    ),
    step(
        """
        CREATE INDEX IF NOT EXISTS idx_refresh_tokens_hash ON refresh_tokens(token_hash)
        """
    )
]
