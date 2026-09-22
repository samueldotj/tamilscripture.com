-- Votes on a presentation's closing slide (docs/feature_presentation.md §4):
-- the audience taps thumbs up or down, anonymously. Two counters live on the
-- row; only presentation_vote() can move them, the owner cannot edit them,
-- and a private presentation takes no votes, so its existence stays hidden.
-- One vote per browser is kept in the browser itself; a determined forger can
-- add noise, which is accepted, as for the site's analytics.

alter table public.presentations
  add column votes_up   integer not null default 0 check (votes_up >= 0),
  add column votes_down integer not null default 0 check (votes_down >= 0);

-- Owners keep editing everything except the counters.
revoke update on public.presentations from authenticated;
grant update (title, subtitle, version, visibility, slides) on public.presentations to authenticated;

create or replace function public.presentation_vote(p_slug text, p_up boolean, p_previous boolean default null)
returns jsonb
language plpgsql
security definer
set search_path = public
as $$
declare
  r record;
begin
  if p_up is null then raise exception 'vote required' using errcode = '22023'; end if;
  update public.presentations
     set votes_up   = greatest(0, votes_up   + (case when p_up then 1 else 0 end) - (case when p_previous is true  then 1 else 0 end)),
         votes_down = greatest(0, votes_down + (case when p_up then 0 else 1 end) - (case when p_previous is false then 1 else 0 end))
   where slug = p_slug and visibility = 'link'
   returning votes_up, votes_down into r;
  if not found then return null; end if;
  return jsonb_build_object('up', r.votes_up, 'down', r.votes_down);
end;
$$;
grant execute on function public.presentation_vote(text, boolean, boolean) to anon, authenticated;

-- The permalink carries the counts so the closing slide shows them at once.
create or replace function public.presentation_by_slug(p_slug text)
returns jsonb
language sql
stable
security definer
set search_path = public
as $$
  select jsonb_build_object(
    'id', id, 'slug', slug, 'title', title, 'subtitle', subtitle, 'version', version,
    'visibility', visibility, 'slides', slides, 'votes_up', votes_up, 'votes_down', votes_down,
    'created_at', created_at, 'updated_at', updated_at)
  from public.presentations
  where slug = p_slug and visibility = 'link';
$$;
