-- M7: community review (feature_dictionary.md §6). Postgres is a moderation
-- workspace only: readers write suggestions, reviewers accept them (editing
-- first when needed) and a scheduled export writes the accepted text back into
-- the repository, which rebuilds. No page reads entity text from here.

-- ---- roles -----------------------------------------------------------------

alter table public.profiles
  add column role text not null default 'reader'
  check (role in ('reader', 'reviewer', 'moderator'));

-- A user edits their own profile through PostgREST but never the role column:
-- the "own profile" policy stays, the privilege is narrowed per column.
revoke update on public.profiles from anon, authenticated;
grant update (display_name, settings, share_aggregates, history_paused) on public.profiles to authenticated;

create or replace function public.my_role()
returns text
language sql
stable
security definer
set search_path = public
as $$
  select coalesce((select role from public.profiles where user_id = auth.uid()), 'reader');
$$;
revoke execute on function public.my_role() from public, anon;
grant execute on function public.my_role() to authenticated;

create or replace function public.is_staff()
returns boolean
language sql
stable
security definer
set search_path = public
as $$
  select public.my_role() in ('reviewer', 'moderator');
$$;
revoke execute on function public.is_staff() from public, anon;
grant execute on function public.is_staff() to authenticated;

-- ---- tables ----------------------------------------------------------------

create table public.entity_suggestions (
  id uuid primary key default gen_random_uuid(),
  user_id uuid not null references auth.users(id) on delete cascade,
  target text not null,                 -- 'name:IRVTAM:Damascus' or 'article:eastons/damascus#p3-4f2a9c1b'
  current_text text not null,           -- what the user saw, so a stale suggestion is detectable
  suggested_text text not null,
  reason text,
  status text not null default 'open' check (status in ('open', 'accepted', 'rejected')),
  created_at timestamptz not null default now(),
  decided_by uuid references auth.users(id) on delete set null,
  decided_at timestamptz,
  decision_note text,
  final_text text                       -- what the reviewer published; equals suggested_text when accepted unchanged
);
create index entity_suggestions_status on public.entity_suggestions (status, created_at);
create index entity_suggestions_user on public.entity_suggestions (user_id, created_at desc);
create index entity_suggestions_target on public.entity_suggestions (target);

create table public.entity_accepted (   -- current accepted text per target; history lives in the log
  target text primary key,
  text text not null,
  suggestion_id uuid references public.entity_suggestions(id) on delete set null,
  accepted_by uuid references auth.users(id) on delete set null,
  accepted_at timestamptz not null default now(),
  exported_at timestamptz               -- set by the export job
);

create table public.moderation_log (
  id bigserial primary key,
  actor uuid not null,
  action text not null,                 -- accept, reject, correct, set_role, publish
  target text,
  detail jsonb,
  at timestamptz not null default now()
);
create index moderation_log_at on public.moderation_log (at desc);

-- Nobody writes these tables directly through the API; the functions below do.
revoke all on public.entity_suggestions, public.entity_accepted, public.moderation_log from anon, authenticated;
grant select on public.entity_suggestions, public.entity_accepted, public.moderation_log to authenticated;

alter table public.entity_suggestions enable row level security;
alter table public.entity_accepted enable row level security;
alter table public.moderation_log enable row level security;

create policy "own or staff read" on public.entity_suggestions
  for select to authenticated using (user_id = auth.uid() or public.is_staff());
create policy "staff read" on public.entity_accepted
  for select to authenticated using (public.is_staff());
create policy "staff read" on public.moderation_log
  for select to authenticated using (public.is_staff());

-- ---- validation --------------------------------------------------------------

-- Targets are constrained so the export job can map them to files; text must
-- be Tamil, plain and bounded.
create or replace function public.check_correction(p_target text, p_text text)
returns void
language plpgsql
immutable
as $$
begin
  if p_target is null or p_target !~ '^(name:[A-Z0-9]{2,12}:[^:]{1,80}|article:[a-z0-9]+/[a-z0-9]+(-[a-z0-9]+)*#p[0-9]+-[0-9a-f]{8})$' then
    raise exception 'invalid target' using errcode = '22023';
  end if;
  if p_text is null or length(btrim(p_text)) = 0 or length(p_text) > 4000 then
    raise exception 'text must be between 1 and 4000 characters' using errcode = '22023';
  end if;
  if p_text !~ '[஀-௿]' then
    raise exception 'text must contain Tamil script' using errcode = '22023';
  end if;
  if p_text ~ '<[A-Za-z/]' then
    raise exception 'text must not contain HTML' using errcode = '22023';
  end if;
end;
$$;

-- ---- readers -----------------------------------------------------------------

create or replace function public.suggest_correction(p_target text, p_current text, p_suggested text, p_reason text default null)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_id uuid;
  v_open int;
begin
  if auth.uid() is null then
    raise exception 'sign in to suggest a correction' using errcode = '42501';
  end if;
  perform public.check_correction(p_target, p_suggested);
  if p_reason is not null and length(p_reason) > 500 then
    raise exception 'reason is limited to 500 characters' using errcode = '22023';
  end if;
  select count(*) into v_open from public.entity_suggestions where user_id = auth.uid() and status = 'open';
  if v_open >= 20 then
    raise exception 'you already have 20 suggestions waiting for review' using errcode = '54000';
  end if;
  insert into public.entity_suggestions (user_id, target, current_text, suggested_text, reason)
  values (auth.uid(), p_target, coalesce(p_current, ''), btrim(p_suggested), nullif(btrim(coalesce(p_reason, '')), ''))
  returning id into v_id;
  return v_id;
end;
$$;
revoke execute on function public.suggest_correction(text, text, text, text) from public, anon;
grant execute on function public.suggest_correction(text, text, text, text) to authenticated;

-- ---- reviewers and moderators ---------------------------------------------------

create or replace function public.require_staff()
returns void
language plpgsql
stable
security definer
set search_path = public
as $$
begin
  if not public.is_staff() then
    raise exception 'reviewers and moderators only' using errcode = '42501';
  end if;
end;
$$;
revoke execute on function public.require_staff() from public, anon, authenticated;

create or replace function public.require_moderator()
returns void
language plpgsql
stable
security definer
set search_path = public
as $$
begin
  if public.my_role() <> 'moderator' then
    raise exception 'moderators only' using errcode = '42501';
  end if;
end;
$$;
revoke execute on function public.require_moderator() from public, anon, authenticated;

-- Accept with the reviewer's final wording. final_text is required so the
-- published text is always an explicit decision, edited or not.
create or replace function public.accept_suggestion(p_id uuid, p_final text)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  s public.entity_suggestions%rowtype;
begin
  perform public.require_staff();
  select * into s from public.entity_suggestions where id = p_id for update;
  if not found then
    raise exception 'unknown suggestion' using errcode = '22023';
  end if;
  if s.status <> 'open' then
    raise exception 'suggestion already decided' using errcode = '22023';
  end if;
  perform public.check_correction(s.target, p_final);
  update public.entity_suggestions
     set status = 'accepted', decided_by = auth.uid(), decided_at = now(), final_text = btrim(p_final)
   where id = p_id;
  insert into public.entity_accepted (target, text, suggestion_id, accepted_by, accepted_at, exported_at)
  values (s.target, btrim(p_final), p_id, auth.uid(), now(), null)
  on conflict (target) do update
    set text = excluded.text, suggestion_id = excluded.suggestion_id,
        accepted_by = excluded.accepted_by, accepted_at = now(), exported_at = null;
  insert into public.moderation_log (actor, action, target, detail)
  values (auth.uid(), 'accept', s.target,
          jsonb_build_object('suggestion', p_id, 'author', s.user_id, 'edited', btrim(p_final) <> s.suggested_text));
end;
$$;
revoke execute on function public.accept_suggestion(uuid, text) from public, anon;
grant execute on function public.accept_suggestion(uuid, text) to authenticated;

create or replace function public.reject_suggestion(p_id uuid, p_note text default null)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  s public.entity_suggestions%rowtype;
begin
  perform public.require_staff();
  select * into s from public.entity_suggestions where id = p_id for update;
  if not found then
    raise exception 'unknown suggestion' using errcode = '22023';
  end if;
  if s.status <> 'open' then
    raise exception 'suggestion already decided' using errcode = '22023';
  end if;
  update public.entity_suggestions
     set status = 'rejected', decided_by = auth.uid(), decided_at = now(), decision_note = nullif(btrim(coalesce(p_note, '')), '')
   where id = p_id;
  insert into public.moderation_log (actor, action, target, detail)
  values (auth.uid(), 'reject', s.target, jsonb_build_object('suggestion', p_id, 'author', s.user_id, 'note', p_note));
end;
$$;
revoke execute on function public.reject_suggestion(uuid, text) from public, anon;
grant execute on function public.reject_suggestion(uuid, text) to authenticated;

-- A direct correction is a suggestion authored and accepted by the same person
-- in one step, so it shows in the same history and export.
create or replace function public.correct_directly(p_target text, p_current text, p_text text)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_id uuid;
begin
  perform public.require_staff();
  perform public.check_correction(p_target, p_text);
  insert into public.entity_suggestions (user_id, target, current_text, suggested_text, status, decided_by, decided_at, final_text)
  values (auth.uid(), p_target, coalesce(p_current, ''), btrim(p_text), 'accepted', auth.uid(), now(), btrim(p_text))
  returning id into v_id;
  insert into public.entity_accepted (target, text, suggestion_id, accepted_by, accepted_at, exported_at)
  values (p_target, btrim(p_text), v_id, auth.uid(), now(), null)
  on conflict (target) do update
    set text = excluded.text, suggestion_id = excluded.suggestion_id,
        accepted_by = excluded.accepted_by, accepted_at = now(), exported_at = null;
  insert into public.moderation_log (actor, action, target, detail)
  values (auth.uid(), 'correct', p_target, jsonb_build_object('suggestion', v_id));
  return v_id;
end;
$$;
revoke execute on function public.correct_directly(text, text, text) from public, anon;
grant execute on function public.correct_directly(text, text, text) to authenticated;

-- The review queue with the author's display name (profiles stay private).
create or replace function public.mod_queue(p_status text default 'open', p_limit int default 200)
returns table (
  id uuid, target text, current_text text, suggested_text text, reason text, status text,
  created_at timestamptz, decided_at timestamptz, decision_note text, final_text text,
  author text, decided_by_name text
)
language sql
stable
security definer
set search_path = public
as $$
  select s.id, s.target, s.current_text, s.suggested_text, s.reason, s.status,
         s.created_at, s.decided_at, s.decision_note, s.final_text,
         coalesce(a.display_name, 'reader ' || left(s.user_id::text, 8)),
         coalesce(d.display_name, case when s.decided_by is null then null else 'reviewer ' || left(s.decided_by::text, 8) end)
    from public.entity_suggestions s
    left join public.profiles a on a.user_id = s.user_id
    left join public.profiles d on d.user_id = s.decided_by
   where public.is_staff()
     and (p_status = 'all' or s.status = p_status)
   order by s.target, s.created_at
   limit greatest(1, least(p_limit, 1000));
$$;
revoke execute on function public.mod_queue(text, int) from public, anon;
grant execute on function public.mod_queue(text, int) to authenticated;

create or replace function public.export_status()
returns table (accepted bigint, pending_export bigint, last_export timestamptz, last_publish timestamptz)
language sql
stable
security definer
set search_path = public
as $$
  select (select count(*) from public.entity_accepted),
         (select count(*) from public.entity_accepted where exported_at is null),
         (select max(exported_at) from public.entity_accepted),
         (select max(at) from public.moderation_log where action = 'publish')
   where public.is_staff();
$$;
revoke execute on function public.export_status() from public, anon;
grant execute on function public.export_status() to authenticated;

-- ---- roles (moderators) -----------------------------------------------------------

-- Moderators appoint and remove reviewers. They cannot create moderators or
-- change their own role; the owner sets moderators in the database.
create or replace function public.set_role(p_user uuid, p_role text)
returns void
language plpgsql
security definer
set search_path = public
as $$
declare
  v_current text;
begin
  perform public.require_moderator();
  if p_role not in ('reader', 'reviewer') then
    raise exception 'moderators can set reader or reviewer only' using errcode = '42501';
  end if;
  if p_user = auth.uid() then
    raise exception 'you cannot change your own role' using errcode = '42501';
  end if;
  select role into v_current from public.profiles where user_id = p_user for update;
  if not found then
    raise exception 'no such user' using errcode = '22023';
  end if;
  if v_current = 'moderator' then
    raise exception 'a moderator''s role is set by the owner' using errcode = '42501';
  end if;
  update public.profiles set role = p_role where user_id = p_user;
  insert into public.moderation_log (actor, action, target, detail)
  values (auth.uid(), 'set_role', p_user::text, jsonb_build_object('from', v_current, 'to', p_role));
end;
$$;
revoke execute on function public.set_role(uuid, text) from public, anon;
grant execute on function public.set_role(uuid, text) to authenticated;

create or replace function public.set_role_by_email(p_email text, p_role text)
returns uuid
language plpgsql
security definer
set search_path = public
as $$
declare
  v_user uuid;
begin
  perform public.require_moderator();
  select id into v_user from auth.users where lower(email) = lower(btrim(p_email)) limit 1;
  if v_user is null then
    raise exception 'no account with that email' using errcode = '22023';
  end if;
  perform public.set_role(v_user, p_role);
  return v_user;
end;
$$;
revoke execute on function public.set_role_by_email(text, text) from public, anon;
grant execute on function public.set_role_by_email(text, text) to authenticated;

create or replace function public.list_staff()
returns table (user_id uuid, display_name text, email text, role text)
language sql
stable
security definer
set search_path = public
as $$
  select p.user_id, p.display_name, u.email::text, p.role
    from public.profiles p
    join auth.users u on u.id = p.user_id
   where public.my_role() = 'moderator' and p.role <> 'reader'
   order by p.role, u.email;
$$;
revoke execute on function public.list_staff() from public, anon;
grant execute on function public.list_staff() to authenticated;

-- "Publish now" is dispatched by the site's server route after it verified the
-- moderator session; the route records it here with the same session.
create or replace function public.log_publish()
returns void
language plpgsql
security definer
set search_path = public
as $$
begin
  perform public.require_moderator();
  insert into public.moderation_log (actor, action) values (auth.uid(), 'publish');
end;
$$;
revoke execute on function public.log_publish() from public, anon;
grant execute on function public.log_publish() to authenticated;
