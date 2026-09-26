-- One Tamil name per English name, used for every Tamil version
-- (docs/feature_dictionary_translation.md §3). Name targets lose their
-- version: `name:IRVTAM:Damascus` becomes `name:Damascus`.

-- Accepted names: keep one per English name, the most recently accepted
-- (the IRV's on a tie), then drop the version from the target.
delete from public.entity_accepted a
using public.entity_accepted b
where a.target ~ '^name:[A-Z0-9]{2,12}:'
  and b.target ~ '^name:[A-Z0-9]{2,12}:'
  and a.target <> b.target
  and regexp_replace(a.target, '^name:[A-Z0-9]{2,12}:', '') = regexp_replace(b.target, '^name:[A-Z0-9]{2,12}:', '')
  and (b.accepted_at, b.target like 'name:IRVTAM:%') > (a.accepted_at, a.target like 'name:IRVTAM:%');

update public.entity_accepted
set target = regexp_replace(target, '^name:[A-Z0-9]{2,12}:', 'name:'),
    exported_at = null
where target ~ '^name:[A-Z0-9]{2,12}:';

update public.entity_suggestions
set target = regexp_replace(target, '^name:[A-Z0-9]{2,12}:', 'name:')
where target ~ '^name:[A-Z0-9]{2,12}:';

update public.moderation_log
set target = regexp_replace(target, '^name:[A-Z0-9]{2,12}:', 'name:')
where target ~ '^name:[A-Z0-9]{2,12}:';

create or replace function public.check_correction(p_target text, p_text text)
returns void
language plpgsql
immutable
as $$
begin
  if p_target is null or p_target !~ '^(name:[^:]{1,80}|article:[a-z0-9]+/[a-z0-9]+(-[a-z0-9]+)*#p[0-9]+-[0-9a-f]{8}|gloss:[HG][0-9]{4}[A-Za-z]?)$' then
    raise exception 'invalid target' using errcode = '22023';
  end if;
  if p_text is null or length(btrim(p_text)) = 0 or length(p_text) > 4000 then
    raise exception 'text must be between 1 and 4000 characters' using errcode = '22023';
  end if;
  -- A gloss is a word or a short phrase, not a paragraph.
  if p_target like 'gloss:%' and length(btrim(p_text)) > 200 then
    raise exception 'a gloss must be at most 200 characters' using errcode = '22023';
  end if;
  if p_text !~ '[஀-௿]' then
    raise exception 'text must contain Tamil script' using errcode = '22023';
  end if;
  if p_text ~ '<[A-Za-z/]' then
    raise exception 'text must not contain HTML' using errcode = '22023';
  end if;
end;
$$;
