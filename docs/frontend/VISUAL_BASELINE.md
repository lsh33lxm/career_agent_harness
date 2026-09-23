# Guangfu visual baseline — 2026-09-21

Phase A presentation slice, based on integration `dc67159`. Reference source is the
read-only main-checkout `docs/Agent_Career_Harness_Codex_Goal_Pack/04_FRONTEND_REFERENCE`.
All reference text/source files were read and the homepage and logo PNGs inspected.
The duplicate frontend-public reference logo has the same SHA-256 as the root logo.
Reference mock values, gradients and extra navigation entries were not imported.

## Shared presentation

`styles.css` owns a small CSS-variable palette: ink `#16353a`, green `#0a514d`,
deep green `#093f3d`, paper `#f5f0e5`, warm surface `#fbf8f1`, panel `#fffdf7`,
gold `#dea536`, gold-soft `#f7e0a7`, muted `#60706f`, border `#ded8ca`,
focus `#9a6a18`, danger `#963f37`. Soft green/gold/danger surfaces retain the
meaning of status chips. Body uses the existing system sans stack; section titles
use Songti/STSong/SimSun, and motto text uses Kaiti. Control/panel radii are 6/8 px;
spacing steps are 6/12/18/24 px; panel shadow is deliberately light.

Today, Capabilities and Inbox share these tokens. The eight existing routes remain;
collapsed navigation keeps accessible names and titles. Focus is a visible 3 px
ochre outline, not blue. Sidebar logo clips inside a padded 56 px frame (44 px in
the collapsed sidebar), with no added shadow. No glass or gradient was introduced.

## Six Today regions and authority

1. Hero: current local date and existing Core health state.
2. 今日焦点: the first item of the existing Core queue, explicitly labelled as such.
   No additional ordering, priority calculation, selection persistence or write.
3. 今日队列: the existing ordered items, source revisions, reasons and separately
   labelled suggested/user priorities. It is not renamed into an opportunity-only feed.
4. 需要你确认: only `review_request` entries already present in that same queue;
   it explicitly does not execute approvals and does not claim to be the full inbox.
5. 快速收集: disabled controls and explicit unavailable text until connected.
6. 本周回看: explicit unavailable text, with no numbers or invented completion state.

Loading/error remain unavailable in both summaries; an empty response is not used
as a fallback for failure. Capability truth, inbox commands, pinned graph query,
receipt/retry behavior, API and backend files are unchanged.

## Logo derivation and proof

The existing app PNG is a 256×256 RGBA asset, distinct from the 1254×1254 reference
PNG. It was retained as the derivative source, avoiding a replacement of the artwork.
Its alpha range is 93–255; corner alpha values (TL/TR/BL/BR) were 93/154/166/255,
all with RGB `(0,0,0)`. Reference corners are opaque black.

`tools/clean_brand_icon.py` visits four-connected pixels from every outer boundary
pixel and selects only `max(R,G,B) <= 24`. It changes **alpha only** to zero on
those selected pixels. It neither erases disconnected dark artwork nor thresholds
the image globally. Destination must not exist and cannot be the source.

- Selected and changed: **2,733 pixels**.
- All **62,803 non-selected RGBA pixels** are asserted byte-equivalent after PNG save/reload.
- Result alpha range: 0–255; all four corner RGBA values `(0,0,0,0)`.
- A second generation into a temporary new output was byte-identical.
- A synthetic image with an enclosed black center retained that center while
  clearing its connected outer black frame; source overwrite was rejected.

SHA-256:

| Asset | Hash |
| --- | --- |
| Existing app `brand-icon.png` (unchanged) | `079c7e22317bcae4aeb34ffb1167c1829b9fa7f4138f4c6329dde02b7ebbea56` |
| Both reference `brand-icon.png` files (unchanged) | `1afe65095e0b78e706e6c9b5f174dd5ae4c608c85222d8f8b5116d66fc2c261f` |
| New app `brand-icon-clean.png` | `8fe009d085d6b2000670cde29f9eb036ef2385585c0c2bf13ebd9f3e7afce43b` |
| Reference homepage PNG (unchanged) | `26528b14808565b8bcb920ab7655bd2a153f863d11dae941a6858e3d8e1dd0b3` |

To reproduce, run the script with existing Pillow and a **new output path**:

```powershell
& $pillowPython tools/clean_brand_icon.py apps/desktop/public/brand-icon.png $newOutput
```

This workstation used the bundled Python runtime under
`C:/Users/lxm33/.cache/codex-runtimes/codex-primary-runtime/dependencies/python/python.exe`;
the repository venv has no Pillow. No dependency installation or Tauri icon change.

## Verification

- Pre-edit Today tests: 4 passed.
- Full frontend: **40 passed / 9 files** with `npm test --workspace @ach/desktop`.
- `npm run build --workspace @ach/desktop`: TypeScript and Vite passed.
- Repository Ruff: `check` and `format --check tools/clean_brand_icon.py` passed.
- `git diff --check` passed.
- Playwright Chromium + Vite on 127.0.0.1:5191: **84 combinations passed**,
  covering Today / Capabilities / Inbox × populated / empty / loading / error ×
  1920×1200, 1440×900, 1280×900, 1024×900, 768×900, 390×900 and 320×900.
  Long synthetic IDs, Chinese titles and reasons wrap. At each combination the
  content scroller has no horizontal overflow, eight navigation links exist, the
  logo loads, and there are no uncaught page errors. Today retains five panels plus hero.
- Screenshot inspection: desktop contact sheet of all 12 page/state combinations,
  individual populated desktop and 320 px screenshots. No mock data enters the app.
- At 320 px, keyboard focus on navigation computes to `rgb(154,106,24) solid 3px`;
  all eight collapsed links retain the correct accessible names.

Local disposable verification script/results/screenshots are under
`%TEMP%/ach-visual-baseline.cjs` and `%TEMP%/ach-visual-baseline/`; these are synthetic
test artifacts and are not committed. API requests were intercepted in Playwright;
no production API, database, migration, real user record or network service was used.
This validates browser layout and presentation; native Tauri rendering and real-data
acceptance remain separate verification steps. Independent review and integration
are owned by the Lead.
