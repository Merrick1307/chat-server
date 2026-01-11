from yoyo import step


steps = [
    step(
        """
        CREATE TABLE IF NOT EXISTS groups (
            group_id UUID PRIMARY KEY DEFAULT gen_random_uuid(),
            group_name VARCHAR(100) NOT NULL,
            creator_id UUID REFERENCES users(id) ON DELETE SET NULL,
            created_at TIMESTAMPTZ DEFAULT NOW()
        )
        """,
        """
        DROP TABLE IF EXISTS groups
        """
    ),
    step(
        """
        CREATE INDEX IF NOT EXISTS idx_groups_creator ON groups(creator_id)
        """
    )
]
