-- A version in any language can be added by config (R-3.6): verse_search
-- accepted only 'ta' and 'en'. Any BCP 47 primary language code is allowed
-- now; search_verses already treats every language but English with the
-- Tamil tokeniser, which leaves other scripts' words whole.
alter table public.verse_search drop constraint if exists verse_search_lang_check;
alter table public.verse_search add constraint verse_search_lang_check check (lang ~ '^[a-z]{2,3}$');
