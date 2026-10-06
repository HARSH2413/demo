---
name: Calm Intelligence
colors:
  surface: '#faf8ff'
  surface-dim: '#d2d9f4'
  surface-bright: '#faf8ff'
  surface-container-lowest: '#ffffff'
  surface-container-low: '#f2f3ff'
  surface-container: '#eaedff'
  surface-container-high: '#e2e7ff'
  surface-container-highest: '#dae2fd'
  on-surface: '#131b2e'
  on-surface-variant: '#464555'
  inverse-surface: '#283044'
  inverse-on-surface: '#eef0ff'
  outline: '#777587'
  outline-variant: '#c7c4d8'
  surface-tint: '#4d44e3'
  primary: '#3525cd'
  on-primary: '#ffffff'
  primary-container: '#4f46e5'
  on-primary-container: '#dad7ff'
  inverse-primary: '#c3c0ff'
  secondary: '#4648d4'
  on-secondary: '#ffffff'
  secondary-container: '#6063ee'
  on-secondary-container: '#fffbff'
  tertiary: '#004d70'
  on-tertiary: '#ffffff'
  tertiary-container: '#006693'
  on-tertiary-container: '#b8e0ff'
  error: '#ba1a1a'
  on-error: '#ffffff'
  error-container: '#ffdad6'
  on-error-container: '#93000a'
  primary-fixed: '#e2dfff'
  primary-fixed-dim: '#c3c0ff'
  on-primary-fixed: '#0f0069'
  on-primary-fixed-variant: '#3323cc'
  secondary-fixed: '#e1e0ff'
  secondary-fixed-dim: '#c0c1ff'
  on-secondary-fixed: '#07006c'
  on-secondary-fixed-variant: '#2f2ebe'
  tertiary-fixed: '#c9e6ff'
  tertiary-fixed-dim: '#89ceff'
  on-tertiary-fixed: '#001e2f'
  on-tertiary-fixed-variant: '#004c6e'
  background: '#faf8ff'
  on-background: '#131b2e'
  surface-variant: '#dae2fd'
typography:
  display:
    fontFamily: Hanken Grotesk
    fontSize: 3rem
    fontWeight: '700'
    lineHeight: '1.15'
    letterSpacing: -0.03em
  headline-lg:
    fontFamily: Hanken Grotesk
    fontSize: 2.25rem
    fontWeight: '600'
    lineHeight: '1.2'
    letterSpacing: -0.025em
  headline-lg-mobile:
    fontFamily: Hanken Grotesk
    fontSize: 1.75rem
    fontWeight: '600'
    lineHeight: '1.25'
    letterSpacing: -0.02em
  headline-md:
    fontFamily: Hanken Grotesk
    fontSize: 1.5rem
    fontWeight: '600'
    lineHeight: '1.3'
    letterSpacing: -0.02em
  headline-sm:
    fontFamily: Hanken Grotesk
    fontSize: 1.125rem
    fontWeight: '600'
    lineHeight: '1.4'
    letterSpacing: -0.015em
  body-lg:
    fontFamily: Inter
    fontSize: 1rem
    fontWeight: '400'
    lineHeight: '1.6'
    letterSpacing: -0.01em
  body-md:
    fontFamily: Inter
    fontSize: 0.875rem
    fontWeight: '400'
    lineHeight: '1.55'
    letterSpacing: 0em
  body-sm:
    fontFamily: Inter
    fontSize: 0.75rem
    fontWeight: '400'
    lineHeight: '1.5'
    letterSpacing: 0.01em
  label-md:
    fontFamily: JetBrains Mono
    fontSize: 0.8125rem
    fontWeight: '500'
    lineHeight: '1.4'
    letterSpacing: -0.01em
  label-sm:
    fontFamily: JetBrains Mono
    fontSize: 0.6875rem
    fontWeight: '500'
    lineHeight: '1.35'
    letterSpacing: 0.02em
rounded:
  sm: 0.125rem
  DEFAULT: 0.25rem
  md: 0.375rem
  lg: 0.5rem
  xl: 0.75rem
  full: 9999px
spacing:
  gutter: 1.5rem
  gutter-sm: 1rem
  margin: 2rem
  margin-mobile: 1rem
  space-xs: 0.25rem
  space-sm: 0.5rem
  space-md: 1rem
  space-lg: 1.5rem
  space-xl: 2.5rem
---

## Brand & Style
The design system embodies precision, serene focus, and analytical clarity. Designed for knowledge workers, researchers, and enterprise teams managing dense document ecosystems, the UI recedes into the background to prioritize reading comprehension and cognitive ease.

The aesthetic leans on high-utility Modern Minimalism with subtle Swiss influence: generous white space, rigorous typographic scales, razor-thin structural dividers, and deliberate micro-interactions. The emotional response is one of supreme competence, quiet confidence, and zero cognitive friction.

## Colors
The color palette establishes an ultra-clean environment using tiered slate neutrals paired with restrained indigo-violet accents.

- **Primary Canvas & Surfaces**: `#FFFFFF` for elevated cards, active workspaces, and panels. `#F8FAFC` (Slate-50) serves as the primary canvas backdrop, with `#F1F5F9` (Slate-100) used for secondary structural wells, sidebar rails, and inactive states.
- **Typography & Hierarchical Neutral**: `#0F172A` (Slate-900) anchors all primary headers and core data points with high-contrast legibility. `#334155` (Slate-700) powers body prose and secondary descriptions. `#64748B` (Slate-500) supports captions, meta info, and empty states.
- **Accents & States**: `#4F46E5` serves as the authoritative primary action color (buttons, primary links, key focus triggers). `#6366F1` handles interactive hovers, active tab highlights, and soft badges. `#0EA5E9` provides secondary context for informational tags and sync indicators.
- **Borders & Dividers**: Kept razor-sharp and soft via `#E2E8F0` (Slate-200) for global container borders and `#CBD5E1` (Slate-300) for high-emphasis boundaries or form inputs.

## Typography
The system uses a tri-font structure to balance character, reading comfort, and analytical precision.

- **Headlines (Hanken Grotesk)**: Provides architectural stability and crisp modern geometry across dashboard summaries, document titles, and modular widget headers.
- **Body Text (Inter)**: Delivers neutral, frictionless readability for complex document extracts, metadata strings, and user input fields.
- **Labels & Data Tags (JetBrains Mono)**: Injected selectively for document identifiers, timestamps, extraction confidence percentages, keyboard shortcuts, and code-adjacent properties.

## Layout & Spacing
Layouts operate on a fluid 12-column foundation anchored by fixed horizontal sidebars (64px collapsed, 240px expanded). The structural rhythm enforces generous whitespace around high-density data zones.

- **Breakpoints**:
  - `Desktop (>= 1280px)`: 12 columns, 24px (`1.5rem`) gutters, 32px (`2rem`) margins. Multi-pane side-by-side view (document list, source viewer, intelligence panel).
  - `Tablet (768px - 1279px)`: 8 columns, 16px (`1rem`) gutters, 24px (`1.5rem`) margins. Third-pane intelligence drawer transitions into an overlay sheet.
  - `Mobile (< 768px)`: 4 columns, 16px (`1rem`) gutters, 16px (`1rem`) margins. Stacked single-pane workflows with sticky bottom actions.
- **Rhythm Rules**: Cards and nested modules favor large interior breathing room (`space-lg`) paired with compact intra-field spacing (`space-sm`) to enforce structural grouping.

## Elevation & Depth
Depth is constructed through subtle surface-color stepping and micro-borders rather than aggressive drop shadows.

- **Layering Principle**: Flat or ultra-subtle ambient lift. The baseline app shell sits on `#F8FAFC`. Interactive panels and primary cards step up to `#FFFFFF` bound by a 1px border of `#E2E8F0`.
- **Shadow Scale**:
  - *Resting Cards / Inputs*: Border-only (`#E2E8F0`). No shadow.
  - *Dropdowns / Popovers / Tooltips*: `0px 4px 16px -2px rgba(15, 23, 42, 0.06), 0px 1px 2px 0px rgba(15, 23, 42, 0.04)`.
  - *Modals & Command Palettes*: `0px 20px 32px -8px rgba(15, 23, 42, 0.08), 0px 4px 8px -2px rgba(15, 23, 42, 0.03)` with a soft `#0F172A` backdrop blur at 20% opacity.
- **Glass Accents**: Used exclusively for sticky top toolbars and navigation caps using `rgba(255, 255, 255, 0.85)` with `backdrop-filter: blur(8px)`.

## Shapes
The shape language uses subtle softness (`roundedness: 1` — base 4px / `0.25rem`) to maintain an authoritative, technical atmosphere without sharp or abrasive edges.

- **Micro Elements**: Badges, tags, tooltips, and checkboxes utilize `rounded` (4px).
- **Interactive Controls**: Standard buttons, text inputs, and table row selections carry `rounded-lg` (8px / `0.5rem`).
- **Containers**: Content cards, modal frames, and floating drawers leverage `rounded-xl` (12px / `0.75rem`).
- **Pills**: Reserved exclusively for live document status badges (e.g., "Indexing", "Verified") and user avatars.

## Components

- **Buttons**:
  - *Primary*: Background `#4F46E5`, text `#FFFFFF`, subtle inner glow. Hover triggers `#4338CA`. Height: 36px (compact) or 42px (default).
  - *Secondary*: Background `#FFFFFF`, border 1px solid `#E2E8F0`, text `#334155`. Hover triggers `#F8FAFC` with border `#CBD5E1`.
  - *Ghost / Minimal*: Borderless, text `#64748B`, background transparent. Hover triggers `#F1F5F9` and text `#0F172A`.

- **Input Fields**:
  - Crisp `#FFFFFF` surface with a 1px border in `#CBD5E1`. Placeholder in `#94A3B8`.
  - Active focus transitions the border to `#4F46E5` accompanied by a 3px outer ring: `rgba(99, 102, 241, 0.15)`.

- **Cards & Data Modules**:
  - White background (`#FFFFFF`), hairline perimeter border (`#E2E8F0`), padding of `1.5rem`.
  - Section headers within cards utilize `headline-sm` with a light border-b separating card headers from table or document payloads.

- **Chips & Document Badges**:
  - High utility, using `label-sm` font. Light tint backgrounds (`#EEF2FF` for indigo accents, `#F1F5F9` for neutral meta tags) with matching soft borders (`#E0E7FF`).

- **Checkboxes & Radios**:
  - Square with 4px border-radius. Border 1.5px solid `#CBD5E1`. On check: solid `#4F46E5` fill with a sharp white checkmark.

- **Lists & Tables**:
  - Horizontal separator lines only (`1px solid #F1F5F9`). No vertical column dividers.
  - Row hover background: `#F8FAFC` with a smooth 150ms ease transition.

- **Specialized UI: Document Intelligence Nodes**:
  - Entity recognition tags inside document views use subtle highlighter styling (`rgba(99, 102, 241, 0.1)` tint, dotted indigo underline), expanding into mini popovers displaying extraction confidence scores formatted in `JetBrains Mono`.