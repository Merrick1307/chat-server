from yoyo import step


steps = [
    step(
        """
        CREATE TABLE IF NOT EXISTS group_messages (
            message_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            group_id UUID REFERENCES groups(group_id) ON DELETE CASCADE,
            sender_id UUID REFERENCES users(id) ON DELETE CASCADE,
            content TEXT NOT NULL,
            message_type VARCHAR(20) DEFAULT 'text',
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
        """,
        """
        DROP TABLE IF EXISTS group_messages
        """
    ),
    step(
        """
        CREATE INDEX IF NOT EXISTS idx_group_messages_group ON group_messages(group_id, created_at DESC)
        """
    ),
    step(
        """
        CREATE INDEX IF NOT EXISTS idx_group_messages_sender ON group_messages(sender_id)
        """
    )
]
