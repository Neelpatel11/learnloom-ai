-- Development roles, created once when the Postgres container first starts.
-- learnloom_app serves the API and workers and is subject to row-level security.
-- learnloom_eval can only reach the eval schema, so evaluation code never sees student data.
-- In production, create these roles with strong passwords kept outside version control.
DO $$
BEGIN
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'learnloom_app') THEN
    CREATE ROLE learnloom_app LOGIN PASSWORD 'learnloom_app' NOSUPERUSER NOBYPASSRLS;
  END IF;
  IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = 'learnloom_eval') THEN
    CREATE ROLE learnloom_eval LOGIN PASSWORD 'learnloom_eval' NOSUPERUSER NOBYPASSRLS;
  END IF;
END
$$;
