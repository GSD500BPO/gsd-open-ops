# Recruiting data schema

## ATS (Zoho Recruit)
- **Candidate_Status:** `New` → `Qualified` (passed) / `Unqualified` (failed test or speaking).
- **Tags** (added by the bot): `Speaking 80+` · `Speaking 60-79` · `Speaking under 60` · `Test passed` / `Test failed` · `On website` · optional `Rate N`.
- **Notes** (one per event): video score card + transcript, test result, CV analysis, roleplay result, consent ("Candidate replied YES on WhatsApp at <time>").
- **Attachments:** intro video (Others), CV (Resume).
- **Task** for the recruiter when someone passes: "Interview: <name> (<role>)", priority High, due today.

## Pipeline state (`state.json`, one entry per normalized phone)
`name, phone, email, source (meta | wa_ad | site), stage, recruit_id, video_path, speech{...}, speech_status (pending|done|error), composite, english, sales, wpm, tier, rp{...}, consent, mp_id, wa_count{day: n}, quiet, fu1/fu2/fu_test`

Stages: `new → welcomed → reminded → video_in → test_passed_no_video → passed | failed | screened_out_english | stopped`

## Supabase (public talent page)

```sql
create table talent_profiles (
  id uuid primary key default gen_random_uuid(),
  display_name text, title text, bio text, email text,           -- email is admin-only (RLS)
  video_url text, photo_url text, hourly_rate numeric,
  english_score int, sales_score int, typing_wpm int, composite_score int,
  languages text[], skills text[], vetting_tier int, category_id text,
  status text default 'pending' check (status in ('pending','approved','rejected')),
  available_now boolean default true, last_qualified_at timestamptz, created_at timestamptz default now()
);
alter table talent_profiles enable row level security;
create policy "public sees approved" on talent_profiles for select using (status = 'approved');
-- writes only with the service key (the pipeline) or your admin role

create table talent_hire_requests (
  id uuid primary key default gen_random_uuid(),
  talent_profile_id uuid references talent_profiles(id),
  client_name text, client_email text, client_phone text,
  job_description text, offer_amount numeric, request_type text, metadata jsonb,
  created_at timestamptz default now()
);
alter table talent_hire_requests enable row level security;
create policy "anyone can request" on talent_hire_requests for insert with check (true);
-- no public select: hire_alert.py reads with the service key
```

Buckets: `agent-videos` (**private**), `talent-video-reels` and `agent-photos` (public, consented content only, salted file names).
Expose the public view without `email` (a view or column privileges), and lock any upload bucket for applications so it can't be listed publicly.
