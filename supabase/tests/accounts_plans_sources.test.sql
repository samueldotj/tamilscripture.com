-- Accounts, reading plans and traffic sources on /mod/traffic
-- (docs/feature_analytics.md A8): staff read counts only, others get null,
-- and referrers are grouped into sources. `supabase test db` (pgTAP).
begin;
create extension if not exists pgtap with schema extensions;
select plan(17);

insert into auth.users (id, instance_id, aud, role, email, raw_user_meta_data, created_at, updated_at, last_sign_in_at)
values
  ('00000000-0000-0000-0000-0000000000d1', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'd-reader@test.local',   '{"name":"D Reader"}',   now(), now(), now()),
  ('00000000-0000-0000-0000-0000000000d2', '00000000-0000-0000-0000-000000000000', 'authenticated', 'authenticated', 'd-reviewer@test.local', '{"name":"D Reviewer"}', now() - interval '10 days', now(), now() - interval '10 days');
update public.profiles set role = 'reviewer' where user_id = '00000000-0000-0000-0000-0000000000d2';
insert into public.plan_progress (user_id, plan, start_date, done)
values
  ('00000000-0000-0000-0000-0000000000d1', 'bible-1y', current_date, '{0-0,0-1}'),
  ('00000000-0000-0000-0000-0000000000d1', 'nt-6m', current_date, '{}'),
  ('00000000-0000-0000-0000-0000000000d2', 'bible-1y', current_date, '{}');

-- ---- sources ----
select is(public.analytics_source('google.com'), 'google', 'google.com is Google');
select is(public.analytics_source('google.co.in'), 'google', 'and so is google.co.in');
select is(public.analytics_source('com.whatsapp'), 'whatsapp', 'the WhatsApp Android app is WhatsApp');
select is(public.analytics_source('utm:whatsapp'), 'whatsapp', 'and so is a utm_source tag');
select is(public.analytics_source('l.facebook.com'), 'facebook', 'l.facebook.com is Facebook');
select is(public.analytics_source('mail.google.com'), 'email', 'Gmail on the web is email, not Google');
select is(public.analytics_source('(direct)'), 'direct', 'no referrer is direct');
select is(public.analytics_source('example.org'), 'other', 'anything else is other');

-- ---- nobody but staff reads ----
select set_config('request.jwt.claims', json_build_object('sub', '00000000-0000-0000-0000-0000000000d1', 'role', 'authenticated')::text, true);
select set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-0000000000d1', true);
select set_config('role', 'authenticated', true);
select is(public.analytics_accounts(public.analytics_today() - 29, public.analytics_today()), null, 'a reader gets no account counts');
select is(public.analytics_plans(public.analytics_today() - 29, public.analytics_today()), null, 'or plan counts');

select set_config('request.jwt.claims', json_build_object('sub', '00000000-0000-0000-0000-0000000000d2', 'role', 'authenticated')::text, true);
select set_config('request.jwt.claim.sub', '00000000-0000-0000-0000-0000000000d2', true);
select is((public.analytics_accounts(public.analytics_today() - 29, public.analytics_today()) -> 'signups' ->> 'day')::int >= 1, true, 'a reviewer sees today''s sign-up');
select is((public.analytics_accounts(public.analytics_today() - 29, public.analytics_today()) -> 'signins' ->> 'month')::int >= 2, true, 'and both sign-ins this month');
select is((public.analytics_accounts(public.analytics_today() - 29, public.analytics_today()) ->> 'range')::int >= 2, true, 'and both sign-ups in the range');
select is(public.analytics_accounts(public.analytics_today(), public.analytics_today()) ? 'peak_signups', true, 'and a peak sign-up day');
select is((public.analytics_plans(public.analytics_today() - 29, public.analytics_today()) -> 'plans' -> 0 ->> 'key'), 'bible-1y', 'the most-followed plan comes first');
select is((public.analytics_plans(public.analytics_today() - 29, public.analytics_today()) -> 'plans' -> 0 ->> 'readers')::int, 2, 'with its two readers');
select is((public.analytics_plans(public.analytics_today() - 29, public.analytics_today()) ->> 'active')::int, 1, 'one reader ticked a passage this week');

select * from finish();
rollback;
