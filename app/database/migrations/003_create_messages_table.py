from yoyo import step


steps = [
    step(
        """
        CREATE TABLE IF NOT EXISTS messages (
            message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            sender_id UUID REFERENCES users(id) ON DELETE CASCADE,
            recipient_id UUID REFERENCES users(id) ON DELETE CASCADE,
            content TEXT NOT NULL,
            message_type VARCHAR(20) DEFAULT 'text',
            created_at TIMESTAMPTZ DEFAULT NOW(),
            delivered_at TIMESTAMPTZ,
            read_at TIMESTAMPTZ
        )
        """,
        """
        DROP TABLE IF EXISTS messages
        """
    ),
    step(
        """
        CREATE INDEX IF NOT EXISTS idx_messages_recipient ON messages(recipient_id, created_at DESC)
        """
    ),
    step(
        """
        CREATE INDEX IF NOT EXISTS idx_messages_sender ON messages(sender_id, created_at DESC)
        """
    ),
    step(
        """
        CREATE INDEX IF NOT EXISTS idx_messages_conversation ON messages(
            LEAST(sender_id, recipient_id),
            GREATEST(sender_id, recipient_id),
            created_at DESC
        )
        """
    )
]
