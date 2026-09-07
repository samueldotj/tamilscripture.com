-- Temporary diagnostic: tamil_norm() returns a blank for Tamil input when
-- called through the API role but not during migrations. Expose each step and
-- the session settings so the difference can be seen from outside.
create or replace function public.search_debug(t text)
returns jsonb
language sql
stable
as $$
  select jsonb_build_object(
    'input', t,
    'input_len', length(t),
    'input_codepoints', (select array_agg(to_hex(ascii(c))) from regexp_split_to_table(t, '') as c),
    'normalized', normalize(t, NFC),
    'lowered', lower(normalize(t, NFC)),
    'step_punct', regexp_replace(lower(normalize(t, NFC)), '[^[:alnum:]அஆஇஉஎஒகஙசஞடணதநனபமயரறலளழவஷஸஹாிீுூெேைொோௌ்]+', ' ', 'g'),
    'step_punct_only', regexp_replace(lower(normalize(t, NFC)), '[[:punct:][:space:]]+', ' ', 'g'),
    'alnum_test', regexp_replace('a1அ', '[[:alnum:]]', 'X', 'g'),
    'tamil_norm', public.tamil_norm(t),
    'current_user', current_user,
    'server_encoding', current_setting('server_encoding'),
    'client_encoding', current_setting('client_encoding'),
    'lc_ctype', current_setting('lc_ctype'),
    'lc_collate', current_setting('lc_collate'),
    'standard_conforming_strings', current_setting('standard_conforming_strings'),
    'db_collation', (select datcollate from pg_database where datname = current_database()),
    'db_ctype', (select datctype from pg_database where datname = current_database()),
    'db_locprovider', (select datlocprovider::text from pg_database where datname = current_database()),
    'server_version', current_setting('server_version')
  );
$$;
grant execute on function public.search_debug(text) to anon, authenticated;
