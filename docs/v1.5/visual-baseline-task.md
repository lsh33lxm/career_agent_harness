# Scoped Phase A: Guangfu visual baseline

Base: current integration scope commit. Branch codex/v15-visual-baseline; sibling visual-baseline.
User requests restoration, not a redesign. Read all text/source files in main repository
`docs/Agent_Career_Harness_Codex_Goal_Pack/04_FRONTEND_REFERENCE` (read-only) and view its PNGs.
Read current Today/Capabilities/Inbox/AppShell/styles/tests. Read AGENTS and current PRD principles.

Owned: apps/desktop/src/styles.css; apps/desktop/src/app/AppShell.tsx;
apps/desktop/src/pages/CapabilityInboxPage.css; apps/desktop/src/pages/TodayPage.tsx (presentation
or accurate unavailable controls only); matching affected tests; apps/desktop/public/brand-icon-clean.png
(new only); tools/clean_brand_icon.py (new deterministic script); docs/frontend/VISUAL_BASELINE.md.
No API/domain/business ranking, real data, migration, shared contracts, dependencies or Tauri icons.
Original brand-icon.png and references must stay byte-identical.

Inspect PNG alpha/corners/background and hash current vs reference. Create cleaned derivative only
by flood-fill removing dark background connected to outer boundary (no internal disconnected dark
artwork). Document exact threshold/pixel count/hash and prove all non-selected RGBA pixels unchanged.
Use existing Pillow runtime if available, no image generation. Sidebar rounded clipping/overflow,
reasonable padding, no heavy shadow. Keep 8 current primary navigation items.

Small CSS custom properties for ink/deep green/paper/warm white/gold/text/muted/border/focus/danger,
type/spacing/radius/shadow/surfaces/sidebar/buttons/chips/panels/states; replace drift within owned
styles, not giant framework or whole-repo formatting. Today is visual anchor. Capabilities and Inbox
must feel same product. No blue focus neon, glass/gradient/huge-radius UI. Preserve accessibility.
Retain Today 6 regions and actual Core data; no mock fallback or fabricated weekly numbers.

Verify 1920x1200,1440,1280,1024,768,390/320 with existing Playwright + Vite; long labels, populated,
empty/loading/error states, sidebar/logo/type/overflow. Synthetic fixtures are not real data.
Use root .venv and existing integration node_modules via junctions if required; no huge new setup.
Run frontend full tests/build, diff check. Document precise verification, no claims before checks.
Explicit stage coherent commit; no merge/push. Return SHA/files/results/limits. Request scope
change if other production file is needed. Independent review before Lead merges.
