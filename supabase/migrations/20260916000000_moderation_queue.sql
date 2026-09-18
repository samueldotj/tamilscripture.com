-- Moderation queue, design 8A: what the queue screen needs that the M7
-- functions do not give it — the counts for the tabs, the standing of the
-- contributor on each row, and the three numbers in the stats strip.
--
-- Additive only: nothing here changes a table, a policy or an existing
-- function's behaviour. `mod_queue` gains two columns, so it is dropped and
-- recreated rather than replaced (Postgres cannot change a function's return
-- type in place); the body is the same query with the author's record joined.

-- ---- the queue, with the contributor's standing ------------------------------------

drop function if exists public.mod_queue(text, int);

create function public.mod_queue(p_status text default 'open', p_limit int default 200)
returns table (
  id uuid, target text, current_text text, suggested_text text, reason text, status text,
  created_at timestamptz, decided_at timestamptz, decision_note text, final_text text,
  author text, decided_by_name text,
  -- How far to trust this suggestion at a glance: what the same contributor has
  -- had accepted and rejected before, this one excluded.
  author_accepted bigint, author_rejected bigint
)
language sql
stable
security definer
set search_path = public
as $$
  with standing as (
    select user_id,
           count(*) filter (where status = 'accepted') as accepted,
           count(*) filter (where status = 'rejected') as rejected
      from public.entity_suggestions
     group by user_id
  )
  select s.id, s.target, s.current_text, s.suggested_text, s.reason, s.status,
         s.created_at, s.decided_at, s.decision_note, s.final_text,
         coalesce(a.display_name, 'reader ' || left(s.user_id::text, 8)),
         coalesce(d.display_name, case when s.decided_by is null then null else 'reviewer ' || left(s.decided_by::text, 8) end),
         coalesce(t.accepted, 0), coalesce(t.rejected, 0)
    from public.entity_suggestions s
    left join public.profiles a on a.user_id = s.user_id
    left join public.profiles d on d.user_id = s.decided_by
    left join standing t on t.user_id = s.user_id
   where public.is_staff()
     and (p_status = 'all' or s.status = p_status)
   order by s.target, s.created_at
   limit greatest(1, least(p_limit, 1000));
$$;
revoke execute on function public.mod_queue(text, int) from public, anon;
grant execute on function public.mod_queue(text, int) to authenticated;

-- ---- the tab counts ----------------------------------------------------------------

create or replace function public.mod_counts()
returns table (open bigint, accepted bigint, rejected bigint)
language sql
stable
security definer
set search_path = public
as $$
  select count(*) filter (where status = 'open'),
         count(*) filter (where status = 'accepted'),
         count(*) filter (where status = 'rejected')
    from public.entity_suggestions
   where public.is_staff();
$$;
revoke execute on function public.mod_counts() from public, anon;
grant execute on function public.mod_counts() to authenticated;

-- ---- the stats strip ---------------------------------------------------------------

create or replace function public.mod_stats()
returns table (accepted_this_month bigint, avg_wait_hours numeric, contributors bigint)
language sql
stable
security definer
set search_path = public
as $$
  select
    (select count(*) from public.entity_suggestions
      where status = 'accepted' and decided_at >= date_trunc('month', now())),
    -- How long a decision has taken lately, over the last 100 decided, so one
    -- suggestion left sitting for a year does not stand for the whole queue.
    (select round(avg(extract(epoch from (decided_at - created_at)) / 3600.0)::numeric, 1)
       from (select created_at, decided_at
               from public.entity_suggestions
              where decided_at is not null
              order by decided_at desc
              limit 100) recent),
    (select count(distinct user_id) from public.entity_suggestions)
  where public.is_staff();
$$;
revoke execute on function public.mod_stats() from public, anon;
grant execute on function public.mod_stats() to authenticated;
