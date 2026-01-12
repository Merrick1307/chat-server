"""
Remove role column from users table.

The role field was never used for authorization decisions and was only
being stored and echoed back in JWT tokens. Group-level roles (on
group_members table) remain and are actively used for group permissions.
"""
from yoyo import step

steps = [
    step(
        "ALTER TABLE users DROP COLUMN IF EXISTS role",
        "ALTER TABLE users ADD COLUMN role VARCHAR(20) DEFAULT 'user'"
    )
]
