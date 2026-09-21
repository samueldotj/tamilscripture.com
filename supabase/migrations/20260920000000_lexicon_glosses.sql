-- Tamil glosses for the concordance's lexicon (docs/feature_concordance.md,
-- phase C5): readers suggest a Tamil meaning for a Strong's number, reviewers
-- accept it, and the export job writes overrides/lexicon.toml for the build.
-- The only change is a third target kind, `gloss:H0430G`, with a short limit.
create or replace function public.check_correction(p_target text, p_text text)
returns void
language plpgsql
immutable
as $$
begin
  if p_target is null or p_target !~ '^(name:[A-Z0-9]{2,12}:[^:]{1,80}|article:[a-z0-9]+/[a-z0-9]+(-[a-z0-9]+)*#p[0-9]+-[0-9a-f]{8}|gloss:[HG][0-9]{4}[A-Za-z]?)$' then
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
