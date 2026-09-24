-- Sub-verse highlights and notes (R-10.15, task 5.10): a word range within a
-- verse, or from part-way through one verse to part-way through another.
-- Offsets are Unicode code points into the verse text of one version
-- (`version`): char_start into verse_start, char_end (exclusive) into
-- verse_end. All three are null for a whole-verse row, as before. Other
-- versions show a partial row on its whole verses. `quote` keeps the marked
-- words for the notes and highlights pages.
alter table public.highlights
  add column version    text,
  add column char_start int,
  add column char_end   int,
  add column quote      text check (length(quote) <= 1000);
alter table public.notes
  add column version    text,
  add column char_start int,
  add column char_end   int,
  add column quote      text check (length(quote) <= 1000);

alter table public.highlights add constraint highlights_partial check (
  (version is null and char_start is null and char_end is null)
  or (version is not null and char_start >= 0 and char_end >= 0
      and (verse_end > verse_start or char_end > char_start))
);
alter table public.notes add constraint notes_partial check (
  (version is null and char_start is null and char_end is null)
  or (version is not null and char_start >= 0 and char_end >= 0
      and (verse_end > verse_start or char_end > char_start))
);
