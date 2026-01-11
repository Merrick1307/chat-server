from yoyo import step


steps = [
    step(
        """
        CREATE TABLE IF NOT EXISTS group_message_reads (
            message_id UUID REFERENCES group_messages(message_id) ON DELETE CASCADE,
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            read_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (message_id, user_id)
        )
        """,
        """
        DROP TABLE IF EXISTS group_message_reads
        """
    ),
    step(
        """
        CREATE INDEX IF NOT EXISTS idx_group_message_reads_user ON group_message_reads(user_id)
        """
    ),
    step(
        """
        CREATE INDEX IF NOT EXISTS idx_group_message_reads_message ON group_message_reads(message_id)
        """
    )
]
