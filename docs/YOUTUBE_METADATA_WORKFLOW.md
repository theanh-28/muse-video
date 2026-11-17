# YouTube metadata workflow

This repository uses four selected Codex skills from YouTube Agent Pro to prepare metadata drafts
for a completed animation. The local Studio exposes this as an optional post-export action after
the final MP4 passes QC. It does not sign in to YouTube, upload, schedule, or change a channel.

## Included skills

| Skill | Use |
|---|---|
| `$yt-package` | Create title options and title/thumbnail pairings from actual footage. |
| `$yt-thumbnail` | Write thumbnail concepts, short text, and image prompts; it does not generate an image. |
| `$yt-seo` | Draft a video-specific description, tags, and optional hashtags. |
| `$yt-chapters` | Draft chapters only when the finished video supports accurate boundaries. |

The channel profile is [`config/youtube/THEANHREVIEW_PROFILE.md`](../config/youtube/THEANHREVIEW_PROFILE.md).
The four skills and selective upstream dependencies are catalogued with their pinned revision and
license at [`THIRD_PARTY_SKILLS.md`](THIRD_PARTY_SKILLS.md).

## Required workflow

1. Read the channel profile and relevant project configuration, episode metadata, storyboard,
   continuity ledger, and approved script where available.
2. Inspect the final MP4 and use its observable content as the primary evidence. A filename or
   storyboard alone is not sufficient. Use subtitles only when supplied and aligned to that export.
3. Separate observed facts from script intent and unknowns. Do not infer dialogue, winner, official
   franchise/character names, genre, release date, or credits without evidence.
4. Create all requested drafts under the episode's `metadata/` directory. Keep prompts as text;
   do not generate a thumbnail image unless separately requested.
5. Check title and description character counts, title variety, factual support, title/thumbnail
   complementarity, tags/hashtags relevance, and chapter timing against the finished MP4.
6. Record the exact media path, duration, streams, frame inspection method, missing evidence, and
   validation results in `content-analysis.md` and `metadata-final.md`.

In the Studio, choose **YouTube SEO & Metadata** from an `EXPORTED` run. The app sends first,
middle and last still frames from the final MP4 plus the approved storyboard and observed continuity
ledger to the selected Codex/LLM backend. It does not send the full moving video or listen to audio.
Paste a timestamped SRT/VTT transcript to enable the chapter skill; the local helper must return
valid candidate boundaries, and final labels/timestamps still need review against the MP4. Without
that evidence, chapters are omitted. Each run writes a new timestamped draft directory and preserves
previous drafts.

## Helper limitations

The copied upstream helpers are small local Python utilities. `title.py` and `thumblint.py` use
English-oriented tokenization and structural heuristics; accented Vietnamese words are not fully
represented in their scoring. Their scores do not assess Vietnamese writing quality, search volume,
click-through rate, or predicted performance. `chapters.py` can help inspect supplied transcript
text, but any output labels and timestamps still require manual verification against the actual
MP4. Helpers never replace editorial review.

## Platform checks

Platform requirements and policy guidance checked on 2026-11-17 against official YouTube Help:

- A title is limited to 100 characters and a description to 5,000 characters: [Edit video settings](https://support.google.com/youtube/answer/57404?hl=en).
- Manual chapters start at `00:00`, include at least three ascending timestamps, and each chapter must be at least 10 seconds: [Video Chapters](https://support.google.com/youtube/answer/9884579).
- For a Short, custom thumbnails use the recommended 9:16 aspect ratio; availability depends on account verification and upload surface: [Add custom thumbnails](https://support.google.com/youtube/answer/72431).
- Tags usually have minimal discovery impact except for common misspellings; avoid stuffing them into the description: [Add tags to your YouTube videos](https://support.google.com/youtube/answer/146402).
- Titles and thumbnails must accurately represent the video; do not use misleading clickbait: [YouTube performance FAQ](https://support.google.com/youtube/answer/141805) and [Thumbnails policy](https://support.google.com/youtube/answer/9229980).

These checks establish format and policy constraints, not reach or performance forecasts. Recheck
official help if platform requirements become central to a future task.

## Example output layout

For episode `EP001`, create:

```text
projects/<project>/episodes/EP001/metadata/
└── draft-<timestamp>-<id>/
    ├── content-analysis.md
    ├── title-options.md
    ├── thumbnail-concepts.md
    ├── description.md
    ├── tags.txt
    ├── hashtags.txt
    ├── chapters.txt       # only when transcript boundaries validate
    ├── metadata-final.md
    └── thumbnail-prompts.md
```

Keep the source MP4 and other media out of this metadata deliverable. Do not claim an upload or
publishing action succeeded unless that separate action was explicitly requested and verified.
