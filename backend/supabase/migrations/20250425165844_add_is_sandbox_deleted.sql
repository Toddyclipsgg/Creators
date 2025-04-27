ALTER TABLE public.projects
ADD COLUMN is_sandbox_deleted BOOLEAN NOT NULL DEFAULT FALSE;

DROP FUNCTION IF EXISTS get_oldest_free_tier_sandboxes();
CREATE OR REPLACE FUNCTION get_oldest_free_tier_sandboxes()
RETURNS TABLE(project_id UUID, sandbox JSONB) -- Specify the return type including project_id
SECURITY DEFINER -- Necessary if the calling role doesn't have direct access to all tables
LANGUAGE plpgsql
AS $$
BEGIN
    RETURN QUERY
    WITH free_tier_accounts AS (
        -- Select accounts that DO NOT have an 'active' subscription
        SELECT a.id
        FROM basejump.accounts a
        LEFT JOIN basejump.billing_subscriptions bs ON a.id = bs.account_id AND bs.status = 'active'
        WHERE bs.id IS NULL -- Filter out accounts that have an 'active' subscription
    )
    SELECT
        p.project_id as project_id, -- Return the project ID
        p.sandbox
    FROM
        public.projects p -- Use public schema prefix explicitly
    JOIN
        free_tier_accounts fta ON p.account_id = fta.id
    WHERE
        p.is_sandbox_deleted = FALSE
        AND p.created_at < NOW() - INTERVAL '24 hours' -- Only sandboxes older than 24 hours
    ORDER BY
        p.created_at ASC -- Oldest first
    LIMIT 10000; -- Limit the results
END;
$$;

-- Grant execute permission to the role your Python script will use (e.g., service_role)
GRANT EXECUTE ON FUNCTION get_oldest_free_tier_sandboxes() TO service_role;
-- Or grant to authenticated if appropriate
-- GRANT EXECUTE ON FUNCTION get_oldest_free_tier_sandboxes() TO authenticated;
