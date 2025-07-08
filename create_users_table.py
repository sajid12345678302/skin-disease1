import psycopg2

# Use your Supabase connection string (using full URI for reliability)
conn = psycopg2.connect(
    "postgresql://postgres:ahLYO11YY8KSqrGS@ttpfoltrgbbwiwnabway.db.supabase.co:5432/postgres"
)

cur = conn.cursor()
cur.execute("""
CREATE TABLE IF NOT EXISTS public.users (
    id uuid PRIMARY KEY DEFAULT gen_random_uuid(),
    email text UNIQUE NOT NULL,
    username text NOT NULL,
    password text NOT NULL
);
""")
conn.commit()
cur.close()
conn.close()
print("Table created successfully.")