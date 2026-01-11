from yoyo import step


steps = [
    step(
        """
        CREATE TABLE IF NOT EXISTS group_members (
            group_id UUID REFERENCES groups(group_id) ON DELETE CASCADE,
            user_id UUID REFERENCES users(id) ON DELETE CASCADE,
            role VARCHAR(20) DEFAULT 'member',
            joined_at TIMESTAMPTZ DEFAULT NOW(),
            PRIMARY KEY (group_id, user_id)
        )
        """,
        """
        DROP TABLE IF EXISTS group_members
        """
    ),
    step(
        """
        CREATE INDEX IF NOT EXISTS idx_group_members_user ON group_members(user_id)
        """
    ),
    step(
        """
        CREATE INDEX IF NOT EXISTS idx_group_members_group ON group_members(group_id)
        """
    )
]
