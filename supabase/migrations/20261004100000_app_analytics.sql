-- Android app analytics (tamilscripture.app requirements §5, design §12).
--
-- The app records events on the phone and sends them in batches to /api/t/app,
-- which adds Vercel's location headers and calls track_app_batch() below. Same
-- privacy rules as the website's track(): no IP, install id or user id is stored,
-- only hashes with the day's salt, which is deleted the next day.
--
--   kind  view        a chapter opened (path /app/{version}/{BOOK}/{chapter})
--         read        a verse at least 60% visible for 2 s (amount = ms visible)
--         verse       a verse selected; action = what was done with it
--         audio       as on the website: play, next, jump, end, time
--         search      a search ran; also written to search_log for common searches
--         commentary  a commentary opened; action = the commentary source
--         plan        a reading-plan passage ticked; action = plan and day-track key
--         download    a pack installed; action = install, route keeps the pack id
--
-- Existing reports filter on kind, so the new kinds do not change website figures;
-- app visitors are counted as visitors, with source = 'android' to tell them apart.

alter table public.analytics_events
  add column source text not null default 'web' check (source in ('web', 'android')),
  add column event_id uuid,
  add column app_version text,
  add column window_class text,
  add column offline boolean;

create unique index analytics_events_event_id on public.analytics_events (event_id) where event_id is not null;

alter table public.analytics_events drop constraint analytics_events_kind_check;
alter table public.analytics_events add constraint analytics_events_kind_check
  check (kind in ('view', 'verse', 'audio', 'read', 'search', 'commentary', 'plan', 'download'));

create or replace function public.track_app_batch(
  p jsonb,
  p_country text default null,
  p_region text default null,
  p_city text default null
)
returns int
language plpgsql
security definer
set search_path = public
as $$
declare
  v_day date := public.analytics_today();
  v_salt bytea := public.analytics_salt_for(v_day);
  v_install text := p ->> 'install';
  v_visitor text;
  v_count int;
  v_stored int := 0;
  e jsonb;
  v_kind text;
  v_at timestamptz;
  v_book text;
  v_chapter int;
  v_version text;
  v_action text;
  v_lang text := case when p ->> 'lang' in ('ta', 'en') then p ->> 'lang' end;
  v_device text := case p ->> 'device' when 'phone' then 'mobile' when 'tablet' then 'tablet' when 'desktop' then 'desktop' end;
  clip constant int := 200;
begin
  if v_install is null or v_install !~ '^[0-9a-f-]{36}$' or jsonb_typeof(p -> 'events') <> 'array' then
    return 0;
  end if;
  -- The install id is random and never stored: like the website's address hash it
  -- only makes a visitor countable for one day.
  v_visitor := left(encode(sha256(v_salt || convert_to('app|' || v_install, 'UTF8')), 'hex'), 16);
  select count(*) into v_count from public.analytics_events where visitor = v_visitor and day = v_day;

  for e in select * from jsonb_array_elements(p -> 'events') limit 500 loop
    -- A runaway install stops counting after 5,000 events a day (reads are frequent).
    exit when v_count >= 5000;
    v_kind := e ->> 'kind';
    continue when v_kind is null or v_kind not in ('view', 'verse', 'audio', 'read', 'search', 'commentary', 'plan', 'download');
    begin
      v_at := (e ->> 'at')::timestamptz;
    exception when others then
      continue;
    end;
    continue when v_at < now() - interval '30 days' or v_at > now() + interval '1 day';
    v_action := left(e ->> 'action', 60);
    continue when v_kind = 'audio' and (v_action is null or v_action not in ('play', 'next', 'jump', 'end', 'time'));
    v_book := case when e ->> 'book' ~ '^[1-3A-Z]{3}$' then e ->> 'book' else split_part(e ->> 'verse', '.', 1) end;
    v_book := case when v_book ~ '^[1-3A-Z]{3}$' then v_book end;
    v_chapter := case when (e ->> 'chapter') ~ '^[0-9]{1,3}$' then (e ->> 'chapter')::int
                      when e ->> 'verse' ~ '^[1-3A-Z]{3}\.[0-9]{1,3}\.' then split_part(e ->> 'verse', '.', 2)::int end;
    v_version := case when e ->> 'version' ~ '^[A-Z]{2,12}$' then e ->> 'version' end;

    if v_kind = 'search' and e ->> 'query' is not null and v_lang is not null then
      perform public.log_search(e ->> 'query', v_lang, case when (e ->> 'amount') ~ '^[0-9]{1,9}$' then (e ->> 'amount')::int else 0 end);
    end if;

    insert into public.analytics_events
      (at, day, kind, path, route, verse, book, chapter, visitor, country, region, city, device, os, lang,
       action, version, amount, source, event_id, app_version, window_class, offline)
    values (
      least(v_at, now()), v_day, v_kind,
      left(case when v_book is not null and v_chapter is not null
                then '/app/' || lower(coalesce(v_version, 'irvtam')) || '/' || v_book || '/' || v_chapter
                else '/app' end, clip),
      left('app:' || v_kind || coalesce(':' || (e ->> 'source'), ''), clip),
      case when e ->> 'verse' ~ '^[1-3A-Z]{3}\.[0-9]{1,3}\.[0-9]{1,3}$' then e ->> 'verse' end,
      v_book,
      case when v_chapter between 1 and 150 then v_chapter end,
      v_visitor,
      left(upper(p_country), 2), left(p_region, 60), left(p_city, 80),
      v_device, left(p ->> 'os', 30), v_lang,
      v_action, v_version,
      case when (e ->> 'amount') ~ '^[0-9]{1,9}$' then least((e ->> 'amount')::bigint, 2000000000)::int end,
      'android',
      case when e ->> 'id' ~ '^[0-9a-f-]{36}$' then (e ->> 'id')::uuid end,
      left(p ->> 'app', 30), left(p ->> 'window', 12),
      case when e ->> 'offline' in ('true', 'false') then (e ->> 'offline')::boolean end
    )
    on conflict (event_id) where event_id is not null do nothing;
    if found then
      v_stored := v_stored + 1;
      v_count := v_count + 1;
    end if;
  end loop;
  return v_stored;
end;
$$;

-- Callable like track(): the collector route passes location from Vercel's edge.
revoke all on function public.track_app_batch(jsonb, text, text, text) from public;
grant execute on function public.track_app_batch(jsonb, text, text, text) to anon, authenticated;
