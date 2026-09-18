-- mod_counts returned one row of zeros to readers: an aggregate without GROUP
-- BY always yields a row, so the WHERE on is_staff() emptied the counts but not
-- the result. HAVING drops the row itself, so a non-staff caller gets nothing,
-- the same as mod_queue and mod_stats. No data was exposed; the counts were
-- zero. The body is otherwise unchanged from 20260916000000.

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
   where public.is_staff()
  having public.is_staff();
$$;
revoke execute on function public.mod_counts() from public, anon;
grant execute on function public.mod_counts() to authenticated;
