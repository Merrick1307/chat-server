import os
import sys
import subprocess
from pathlib import Path
from dotenv import load_dotenv

project_root = Path(__file__).parent
sys.path.insert(0, str(project_root))

load_dotenv()

db_user = os.getenv('DATABASE_USER')
db_password = os.getenv('DATABASE_PASSWORD')
db_connection_url = os.getenv('DB_CONNECTION_URL')

if not all([db_user, db_password, db_connection_url]):
    sys.exit(1)

db_url = f"postgresql://{db_user}:{db_password}@{db_connection_url}"

migrations_path = project_root / 'migrations'

if not migrations_path.exists():
    print(f"ERROR: Migrations directory not found: {migrations_path}")
    sys.exit(1)

print("\nMigration Status:")
subprocess.run([
    'yoyo',
    'list',
    '--database', db_url,
    str(migrations_path)
], env={**os.environ, 'PYTHONPATH': str(project_root)})

print("Applying migrations...")

result = subprocess.run([
    'yoyo',
    'apply',
    '--batch',
    '--database', db_url,
    str(migrations_path)
], env={**os.environ, 'PYTHONPATH': str(project_root)})

if result.returncode == 0:
    print("\nMigrations completed!")
else:
    print(f"\nMigrations failed with exit code {result.returncode}")

sys.exit(result.returncode)