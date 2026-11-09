-- Verse presentations: highlighted words (docs/feature_presentation.md, P6).
-- A slide verse may carry `marks`, the words the author highlighted, per
-- version, since word positions differ between translations:
--   "marks": { "IRVTAM": ["16.3", "16.4"], "KJV": ["16.7"] }
-- Each entry is "<verse>.<word>", the verse number and the word's 0-based
-- position in it, with ":<colour>" for any colour but the default gold
-- (g green, b blue, p pink, r red; MARK_COLORS in src/lib/present/types.ts).
-- Still references only: no verse text is stored.
create or replace function public.check_slides(p jsonb)
returns boolean
language plpgsql
immutable
as $$
declare
  s jsonb;
  v jsonb;
  m text;
begin
  if p is null or jsonb_typeof(p) <> 'array' then return false; end if;
  if jsonb_array_length(p) > 200 then return false; end if;
  if length(p::text) > 400000 then return false; end if;
  for s in select * from jsonb_array_elements(p) loop
    if jsonb_typeof(s) <> 'object' then return false; end if;
    if exists (select 1 from jsonb_object_keys(s) k where k not in ('id', 'title', 'notes', 'verses')) then return false; end if;
    if jsonb_typeof(s->'id') <> 'string' or length(s->>'id') not between 1 and 32 then return false; end if;
    if s ? 'title' and (jsonb_typeof(s->'title') <> 'string' or length(s->>'title') > 200) then return false; end if;
    if jsonb_typeof(s->'notes') <> 'string' or length(s->>'notes') > 20000 then return false; end if;
    if jsonb_typeof(s->'verses') <> 'array' or jsonb_array_length(s->'verses') > 20 then return false; end if;
    for v in select * from jsonb_array_elements(s->'verses') loop
      if jsonb_typeof(v) <> 'object' then return false; end if;
      if exists (select 1 from jsonb_object_keys(v) k where k not in ('book', 'chapter', 'start', 'end', 'version', 'marks')) then return false; end if;
      if jsonb_typeof(v->'book') <> 'string' or (v->>'book') !~ '^[1-3A-Z]{3}$' then return false; end if;
      if jsonb_typeof(v->'chapter') <> 'number' or (v->>'chapter') !~ '^[0-9]{1,3}$' or (v->>'chapter')::int not between 1 and 150 then return false; end if;
      if jsonb_typeof(v->'start') <> 'number' or (v->>'start') !~ '^[0-9]{1,3}$' or (v->>'start')::int not between 1 and 176 then return false; end if;
      if jsonb_typeof(v->'end') <> 'number' or (v->>'end') !~ '^[0-9]{1,3}$' or (v->>'end')::int not between (v->>'start')::int and 176 then return false; end if;
      if v ? 'version' and (jsonb_typeof(v->'version') <> 'string' or (v->>'version') !~ '^[A-Z0-9]{2,12}$') then return false; end if;
      if v ? 'marks' then
        if jsonb_typeof(v->'marks') <> 'object' then return false; end if;
        if (select count(*) from jsonb_object_keys(v->'marks')) > 8 then return false; end if;
        for m in select * from jsonb_object_keys(v->'marks') loop
          if m !~ '^[A-Z0-9]{2,12}$' then return false; end if;
          if jsonb_typeof(v->'marks'->m) <> 'array' or jsonb_array_length(v->'marks'->m) > 300 then return false; end if;
          if exists (select 1 from jsonb_array_elements(v->'marks'->m) w
                     where jsonb_typeof(w) <> 'string' or (w #>> '{}') !~ '^[0-9]{1,3}\.[0-9]{1,4}(:[ygbpr])?$') then return false; end if;
        end loop;
      end if;
    end loop;
  end loop;
  return true;
end;
$$;
