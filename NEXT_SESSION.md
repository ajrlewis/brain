# Next Session

## Objective

Build Brain's initial read-only Next.js web console with a reusable component system and
runtime company theming through validated semantic design tokens.

The console is a human interface over Brain's existing public HTTP API. It must not duplicate
authorization or domain rules from the backend.

## Scope

### 1. Web application foundation

- Add `apps/web` using the current stable Next.js App Router, React, TypeScript, and Tailwind
  CSS conventions.
- Integrate the application into the repository's package workflow, canonical checks, Docker
  build, and Compose stack without coupling the Python API to Next.js or Vercel.
- Use Server Components by default and Client Components only where browser state or
  interaction requires them.
- Add typed environment configuration for the internal Brain API URL and local development
  authentication boundary. Do not expose bearer tokens to browser JavaScript.

### 2. Company theme contract

- Define semantic design tokens for primary, accent, surface, text, muted text, borders,
  focus, success, warning, and danger states. Components must consume semantic tokens rather
  than company-specific colour names or dynamically constructed Tailwind class names.
- Implement runtime theme selection with CSS custom properties so changing company palettes
  does not require rebuilding component markup or generating arbitrary CSS.
- Include a neutral Brain theme and a wholly synthetic Northstar theme as checked-in web
  configuration. Validate token completeness and safe CSS colour values.
- Keep the theme source behind a small typed interface that can later consume governed
  Organization branding from the API. Do not add database branding fields in this slice.
- Preserve accessible contrast, visible focus states, reduced-motion preferences, and usable
  light/dark behavior where supported.

### 3. Reusable components and first vertical slice

- Build the minimum reusable primitives needed for the console: application shell, header,
  sidebar, breadcrumbs, buttons, cards, tables/lists, badges, and loading, empty, error, and
  not-found states.
- Add safe Markdown rendering shared by Page and Skill views. Do not permit raw untrusted HTML
  or styling to escape the application theme boundary.
- Implement a responsive read-only knowledge flow against the real Brain HTTP API:
  folder-tree navigation, authorized Page inventory, and Page detail with rendered current
  Markdown and visible provenance.
- Use the checked-in Northstar corpus for the local demonstration and provider-neutral dummy
  fixtures for focused component and transport tests.

### 4. Verification and documentation

- Add focused tests for theme validation and switching, semantic component rendering,
  responsive navigation states, Markdown sanitization, API success/deny/missing/failure
  behavior, and prevention of client-side token exposure.
- Add one browser smoke flow covering the Northstar Page inventory and Page detail.
- Run lint, formatting, type checking, unit/component tests, production Next.js build, existing
  Python checks, Compose startup/health, and Docker builds.
- Update `README.md`, `.agents/ARCHITECTURE.md`, `.agents/COMMANDS.md`, environment examples,
  and relevant web documentation with the implemented boundary and verified commands.

## Definition of Done

- `apps/web` builds and runs locally and in Compose using documented commands.
- Neutral Brain and Northstar palettes can theme the same component tree at runtime through
  validated semantic tokens, without arbitrary CSS or company-specific component branches.
- A signed-in local user can browse authorized folders and Pages, open a Page, read sanitized
  Markdown, and inspect visible provenance; deny, missing, empty, loading, and backend-failure
  states are intentional and tested.
- Browser-delivered code and responses do not contain the backend bearer token, and the web
  application does not reimplement Brain authorization decisions.
- Accessibility checks, focused browser smoke coverage, quality checks, production builds,
  and Compose health checks pass.

## Explicitly Deferred

- Editable organization branding, logo or asset upload, arbitrary customer CSS, and database
  schema changes for theme storage;
- Page or Skill editing, version publication, access-policy administration, search UI, and
  MCP diagnostics;
- production identity-provider integration, deployment, analytics, and visual page builders;
- binary Northstar PDFs or brand assets until their generation, licensing, storage, and
  delivery contract is specified.
