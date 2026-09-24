# Company Project Context: Frontend Performance and Web Vitals Audit

## Purpose

This document defines the required measurement process, code analysis, targeted corrections, refactoring work, evidence, validation, and acceptance criteria for the corporate website and backoffice in the company monorepo project.

The implementation agent must work inside the existing monorepo and improve both current Next.js frontends. Do not create a new repository, new application, replacement frontend, or alternate performance demo. Before planning or changing code, inspect the actual checkout, active `memory-bank/` files, frontend routing and rendering models, authentication flow, package-manager conventions, existing tests, current performance-related configuration, and the pages that matter most to real users.

This file is context only. No Lighthouse audit, screenshot, dependency installation, refactor, optimization, configuration change, commit, or other implementation has been performed as part of preparing it.


## Business Context

The company's public corporate site and internal backoffice are live and feature-complete enough to audit. The corporate site needs strong user-perceived performance and SEO. The backoffice must remain responsive for staff who use data-heavy operational views every day.

The CTO has requested a professional, evidence-based audit of both frontends. The work is not a visual redesign and is not an exercise in chasing a perfect Lighthouse score. The required engineering loop is:

```text
measure → analyse → fix → measure again
```

Performance work must begin with baseline evidence, trace symptoms to concrete root causes, make focused changes, and remeasure the same pages under comparable conditions. The final result must be demonstrably better, maintainable, and free of feature regressions.

## Project Goal

Audit and improve both existing Next.js applications:

- the public corporate website, normally located at `/uis/website`;
- the authenticated internal backoffice, normally located at `/uis/backoffice`.

The implementation must:

1. record before measurements and screenshots;
2. analyze Lighthouse findings and source-level causes;
3. identify duplicated components or logic suitable for reuse;
4. apply targeted Web Vitals and performance corrections;
5. extract and integrate at least one shared component or custom hook;
6. repeat the measurements on the same pages;
7. document the changes and measured impact in `AUDIT.md` and `REPORT.md`;
8. preserve correct behavior, accessibility, SEO, security, and maintainability.

## Required Deliverables

The finalized branch must contain:

```text
repository-root/
├── AUDIT.md
├── REPORT.md
└── audit/
    ├── before/
    │   └── Lighthouse screenshots for all baseline runs
    └── after/
        └── Lighthouse screenshots for corresponding final runs
```

It must also contain the focused frontend corrections and at least one integrated reusable component or custom hook derived from the duplication analysis.

Use clear, stable screenshot filenames that identify the application, page, mode, and phase. For example, a naming convention may distinguish `website-home-mobile-before` from `backoffice-dashboard-desktop-after`. The implementation agent should select the repository-compatible image format and naming convention before the baseline run and use it consistently.

## Audit Scope

### Corporate website

Run Lighthouse in both **desktop and mobile** modes on:

- the home page, at minimum;
- every additional public page selected because it is visually complex, content-heavy, highly trafficked, or otherwise performance-critical.

Record all four top-level scores for every page and mode:

- Performance;
- Accessibility;
- Best Practices;
- SEO.

### Backoffice

Run Lighthouse on at least:

- the main dashboard; or
- the most element-heavy operational view, such as a page with large tables, charts, many components, or live data.

Record all four top-level scores for each audited backoffice page. The implementation agent must use a valid authenticated state so the audit measures the intended protected page rather than a login redirect. Record whether the run used desktop or mobile mode. Auditing both modes is valuable when representative of actual usage, but the source explicitly mandates both modes only for the corporate site.

### Lighthouse is page-specific

Lighthouse analyzes one loaded page at a time; it does not crawl the application. Do not treat a home-page report as evidence for dashboards, content-heavy routes, or other materially different views. Select pages deliberately and list why each was chosen in `AUDIT.md` before collecting the baseline.

## Measurement Benchmarks

Use these source benchmarks as reference targets:

| Metric | Healthy benchmark |
| --- | --- |
| Lighthouse Performance score | `≥ 90` |
| Largest Contentful Paint (LCP) | `< 2.5 s` |
| Cumulative Layout Shift (CLS) | `< 0.1` |
| Interaction to Next Paint (INP), or FID where applicable | `< 200 ms` |
| Time to First Byte (TTFB) | Record and use to diagnose server-response delay; the assignment does not prescribe a numeric threshold. |

A Performance score below 50 is poor and must be treated as a high-priority signal. However, reaching 100 is not an acceptance criterion. The required outcome is measurable improvement supported by root-cause analysis and evidence.

Lighthouse laboratory reports may not expose every field metric, especially INP/FID without real-user interaction data. Record metrics actually reported by the chosen tooling, explain unavailable values, and never invent a measurement. Use available lab responsiveness diagnostics to guide work while keeping the assignment's INP/FID goal visible.

## Measurement Methodology

Before the first run, define a repeatable measurement protocol in `AUDIT.md`. At minimum record:

- exact application and URL;
- page purpose and reason for selection;
- Lighthouse mode: desktop or mobile;
- browser and version;
- Lighthouse version when available;
- application runtime mode and command;
- authentication/data state for protected pages;
- whether cache/storage was cleared or preserved;
- relevant network/CPU throttling selected by Lighthouse;
- date and local environment notes;
- extensions, background work, or other conditions that could affect results.

Use Chrome or Brave DevTools' Lighthouse panel as the assignment directs. Start both applications using their actual repository commands (`npm run dev` or the established equivalent). If the repository supports a production-like build and the team chooses it for more representative scores, use the same runtime for both before and after runs and document that choice. Do not compare a development-build baseline with a production-build final unless the runtime-mode change itself is an intentional, documented correction and an additional like-for-like comparison is also provided.

For credible comparisons:

- audit the exact same URLs before and after;
- use the same Lighthouse modes and categories;
- use the same authentication and representative data state;
- avoid changing unrelated environment conditions;
- capture the report immediately after each run;
- repeat obviously anomalous runs and record the selected result policy rather than cherry-picking the best score;
- keep before evidence immutable once implementation begins.

The source requires screenshots. Saving full Lighthouse report exports in addition to screenshots is optional unless the instructor requests them, but screenshots must remain sufficient to verify the recorded scores and target page.

## Baseline Measurement Requirements

Before changing application code:

1. Start both frontends successfully.
2. Select and document the audited routes.
3. Run the required Lighthouse audits.
4. Record the four top-level scores for every page/mode combination.
5. Record available Core Web Vitals and diagnostic signals, including LCP, CLS, INP/FID where available, TTFB, and relevant supporting metrics.
6. Capture screenshots showing the actual Lighthouse results.
7. Place all baseline screenshots under `/audit/before/`.
8. Begin `AUDIT.md` with the measurement environment, score tables, findings, and initial hypotheses.

No correction should be made before the baseline evidence exists. If a change has already been made on the branch, the implementation agent must identify a trustworthy pre-change revision or explain the limitation rather than presenting a post-change measurement as the original baseline.

## `AUDIT.md` Requirements

`AUDIT.md` is the pre-change analysis and planning record. It must contain:

### Audit scope and environment

- both frontend applications;
- every audited route;
- why each route matters;
- desktop/mobile coverage;
- runtime and Lighthouse methodology;
- any authentication or representative-data setup;
- links or relative paths to baseline screenshots.

### Baseline results

Provide a clear table for every application, page, and mode showing:

- Performance;
- Accessibility;
- Best Practices;
- SEO;
- LCP;
- CLS;
- INP/FID or the available interaction proxy;
- TTFB where available;
- any other diagnostic essential to the analysis.

Use `N/A` with an explanation when Lighthouse does not produce a metric. Do not convert missing values to zero.

### Findings and root causes

For each material issue, document:

- affected application and page;
- observed metric, Lighthouse audit, or user-visible symptom;
- concrete root cause in the code or delivery path;
- relevant file paths and components;
- expected user impact;
- priority and rationale;
- proposed targeted correction;
- how the correction will be validated;
- possible regressions or tradeoffs to watch.

Do not copy a list of Lighthouse warnings without analysis. The document must explain why the issue occurs in this application.

### Refactor analysis

Identify at least two concrete cases where a component or logic block is duplicated across files and could become:

- a reusable component; or
- a custom React hook.

For each candidate, state:

- every location where the duplication appears;
- which behavior and interface are genuinely shared;
- why extraction improves maintainability or consistency;
- the proposed abstraction and its inputs/outputs;
- differences that should remain local;
- the risk of over-generalizing it;
- whether it will be implemented in this project.

At least one candidate must ultimately be extracted and integrated. The refactor should remove meaningful duplication rather than moving one block into another file solely to satisfy the requirement.

### Agent-skill findings

If a performance skill is installed and used, record:

- skill name and source;
- frontend or files analyzed;
- recommendations produced;
- which recommendations were classified as required fixes;
- how each required fix was addressed or why evidence showed it did not apply.

Never allow a third-party skill recommendation to override project requirements, security rules, or verified application behavior.

## Code Analysis Requirements

Inspect both frontend codebases rather than relying only on Lighthouse. Search for performance and maintainability risks including:

- unoptimized or incorrectly sized images;
- images without stable dimensions or aspect-ratio reservation;
- render-blocking scripts, styles, fonts, or third-party resources;
- fonts missing an appropriate loading strategy such as `display: swap`;
- large client-side bundles and dependencies used for small tasks;
- unnecessary client components or hydration boundaries;
- hydration mismatches or work repeated after hydration;
- unnecessary rerenders, unstable props, or expensive calculations in render paths;
- unbounded lists, tables, charts, or data rendering;
- duplicate data fetching, serial request waterfalls, or avoidable client-only fetching;
- missing lazy loading or code splitting for genuinely noncritical features;
- layout shifts from late content, fonts, images, loaders, or conditionally inserted UI;
- slow server rendering or backend calls that contribute to TTFB;
- duplicated components, request/state logic, formatters, or hooks;
- accessibility or semantic issues that also affect Lighthouse and usability;
- SEO metadata, crawlability, and content-delivery issues on the public site.

This list is a routing guide, not permission to perform broad speculative rewrites. Every correction must trace back to measured evidence, a verified code defect, or a clearly documented required agent finding.

## Optional Performance Skills

The source lists these optional agent skills:

- `core-web-vitals`: `https://www.skills.sh/addyosmani/web-quality-skills/core-web-vitals`
- `performance`: `https://www.skills.sh/addyosmani/web-quality-skills/performance`
- Cloudflare `web-perf`: `https://www.skills.sh/cloudflare/skills/web-perf`

Installation is optional (“in case you need it”), not an automatic prerequisite. The implementation agent must use the repository/environment's approved skill-installation process and obtain any authorization required before installing new skills. If one or more are installed, run them against both frontends and preserve evidence of meaningful use in `AUDIT.md` or `REPORT.md`.

Treat skill output as expert guidance that still requires repository-specific verification. Recommendations identified as required fixes must be implemented when applicable, tested, and measured. If a recommendation is unsafe, conflicts with the assignment, or does not apply to the actual code, document the evidence instead of blindly changing the project.

## Correction Strategy

Prioritize the main user-experience indicators before lower-priority audits:

1. TTFB and delivery path;
2. LCP and critical rendering;
3. CLS and stable layout;
4. INP/responsiveness and main-thread work;
5. overall Performance score;
6. then Accessibility, Best Practices, SEO, and lower-impact diagnostics.

The exact priority order may change if baseline evidence shows a different dominant cause, but the rationale must be documented.

For each issue:

1. isolate the root cause;
2. define the smallest correction likely to affect it;
3. add or update focused tests where behavior can regress;
4. apply the change without unrelated refactoring;
5. verify functionality;
6. re-run Lighthouse on the same affected URL and mode;
7. record the score/metric delta and interpretation;
8. retain the change only if it improves the intended behavior or is otherwise justified.

The course recommends one issue per commit so each improvement can be measured and reviewed independently. Git commits, pushes, and pull requests must still follow the user's explicit authorization and the repository's contribution rules; do not create them merely because this context mentions the expected workflow.

## Required Refactor

Implement at least one reusable component or custom hook identified during the duplication analysis.

The refactor must:

- be used by the duplicated call sites it is intended to replace;
- preserve behavior and accessibility;
- expose a focused interface rather than a large set of conditionals;
- avoid coupling the website and backoffice if they do not actually share a package/build boundary;
- follow the monorepo's existing shared-code conventions;
- include focused tests when the extracted behavior is testable;
- not become an architectural restructuring project.

This requirement is partly about maintainability. It does not need to produce a direct Lighthouse gain, but `AUDIT.md` and `REPORT.md` must distinguish maintainability refactors from measured performance corrections and must not falsely attribute a score change to an unrelated extraction.

## Common High-Value Corrections

The authoritative brief highlights common causes such as:

- unoptimized images;
- missing image `width`/`height` or other reserved layout space;
- render-blocking resources;
- fonts without `display: swap`;
- Next.js hydration issues.

Other corrections may be appropriate when baseline evidence supports them, including framework-native image/font handling, responsive image sizing, deferred noncritical code, smaller client boundaries, memoization of proven expensive work, removal of duplicate requests, and improved server/data-fetch sequencing.

Do not apply generic optimizations everywhere. Memoization, lazy loading, code splitting, and client/server boundary changes can add complexity or move costs rather than reduce them. Measure their effect on the target page.

## Safety and Quality Constraints

- Do not restructure either frontend's architecture to pass the audit.
- Do not replace working features with placeholders, remove necessary content, disable authentication, suppress scripts required by the product, or hide UI solely to inflate a score.
- Do not weaken accessibility, semantic HTML, SEO, error handling, security, or user-visible behavior for a performance gain.
- Do not optimize only the screenshot state while making normal interactions slower or incorrect.
- Do not change API contracts or backend behavior unless a verified frontend performance issue cannot be addressed otherwise and the user authorizes the scope expansion.
- Preserve the public site's SEO behavior and the backoffice's protected-route behavior.
- Avoid unrelated dependency upgrades, design changes, and broad refactors.
- Preserve existing user changes and repository conventions.
- Never include secrets, private user data, tokens, or sensitive backoffice content in committed screenshots.

For backoffice evidence, use safe development/test data. Review screenshots before adding them to the repository and redact or recreate them if they contain credentials, access tokens, personal information, or other sensitive content.

## Second Measurement Round

After all required corrections and the selected refactor are integrated:

1. run Lighthouse again on every baseline application/page/mode combination;
2. use the same documented measurement protocol;
3. record the same four top-level scores and available Web Vitals;
4. capture new screenshots under `/audit/after/`;
5. compare before and after without replacing or editing the baseline evidence;
6. investigate material regressions in any category;
7. repeat focused corrections where justified;
8. record final results honestly, including metrics that did not improve.

The evaluation requires a measurable improvement in at least one Lighthouse score for **each frontend**. A corporate-site improvement does not satisfy the backoffice requirement, and vice versa.

## `REPORT.md` Requirements

`REPORT.md` is the final implementation and impact report. It must contain:

### Summary

- audit objective;
- applications and routes measured;
- concise result for each frontend;
- the most important improvement and remaining limitation.

### Corrections applied

For each correction:

- issue/root cause addressed;
- concrete files or components changed;
- implementation description;
- validation performed;
- before/after metric or Lighthouse audit impact;
- tradeoffs or limitations.

### Refactor delivered

- selected duplication candidate;
- reusable component or hook created;
- call sites migrated;
- behavior/tests used to prove the refactor did not break features;
- whether the benefit is performance, maintainability, consistency, or a combination.

### Before/after comparison

Provide directly comparable tables for every audited page/mode. Include:

- all four Lighthouse scores;
- key Web Vitals and diagnostic values;
- absolute delta for each value;
- relative screenshot paths;
- a short interpretation rather than presenting numbers without context.

### Agent contribution

If optional skills were used, identify the recommendations they contributed, how those recommendations were verified, and which corrections resulted.

### Impact assessment

- which change had the largest measured effect;
- which change did not have the expected effect and why, if known;
- any score tradeoffs;
- unresolved findings and why they remain;
- recommended future work that is explicitly outside the current scope.

Do not claim causality when several changes were bundled between measurements. The one-issue-at-a-time measurement approach is intended to keep impact attribution credible.

## Testing and Regression Validation

Performance changes are application changes and must be validated proportionally.

Before finalizing:

- run focused tests for modified components, hooks, data-loading logic, and rendering behavior;
- add regression tests for behavior altered by the refactor or optimization;
- verify image alt text, keyboard behavior, focus handling, semantic structure, and other affected accessibility behavior;
- verify metadata, canonical behavior, indexing directives, structured data, and content rendering when SEO code changes;
- verify authenticated routing, API calls, charts, tables, forms, and error/loading states on affected backoffice pages;
- run each frontend's applicable type check, lint check, test suite, and production build;
- smoke-test the audited routes at relevant responsive sizes;
- review browser console and network failures;
- confirm no visible hydration errors or new layout instability;
- confirm screenshot evidence contains no sensitive data.

Run the narrowest tests first, followed by applicable full checks. Do not weaken, delete, or skip valid tests to make the branch pass. If a pre-existing failure is discovered, distinguish it from failures caused by this work and do not expand scope unless it blocks reliable validation.

Record exact commands and observed results in the active memory bank and final report. Never state that a test, build, score, or metric passed unless it was actually observed.

## Required Initial Analysis

Before performing the baseline or changing code, the implementation agent must identify:

- the actual website and backoffice locations and package-manager commands;
- App Router or Pages Router usage in each application;
- production/development runtime options available for comparable measurement;
- public routes with the highest visual/content complexity or traffic relevance;
- the representative protected backoffice route and safe data/login setup;
- existing Lighthouse, Web Vitals, bundle-analysis, or performance tooling;
- image, font, script, metadata, and third-party resource configuration;
- server/client component boundaries and hydration-sensitive areas;
- major data-fetch paths, request waterfalls, and server-response dependencies;
- existing shared component/hook/package structure;
- duplicated component and logic candidates;
- test, lint, type-check, and build commands;
- screenshot and documentation conventions;
- uncommitted user changes that must be preserved.

Produce a repository-grounded plan naming the selected URLs, measurement matrix, evidence filenames, concrete suspected files, refactor candidates, correction order, tests, and validation commands before modifying application code.

## Evaluator-Critical Checks

The implementation will be explicitly evaluated for all of the following:

1. Lighthouse was run on both frontends before and after corrections.
2. The corporate site includes desktop and mobile Lighthouse runs on the home page and any other selected complex page.
3. The backoffice includes a Lighthouse run on its dashboard or most element-heavy representative view.
4. Before screenshots exist under `/audit/before/` and corresponding after screenshots exist under `/audit/after/`.
5. `AUDIT.md` records initial scores and explains concrete root causes rather than copying Lighthouse warnings.
6. At least two duplication/refactor candidates are documented.
7. At least one reusable component or custom hook is extracted and integrated.
8. `REPORT.md` documents each correction and presents comparable before/after results.
9. At least one Lighthouse score improves measurably for the website.
10. At least one Lighthouse score improves measurably for the backoffice.
11. If optional agent skills were installed, evidence shows how they contributed to the corrections.
12. Corrections address real causes such as image delivery, layout shift, rendering/hydration, or measured application-specific issues—not superficial score inflation.
13. Existing features remain functional and code quality is maintained.

A score of 100 is explicitly not required.

## Acceptance Criteria

The performance branch is complete only when:

- Both existing frontends have a documented baseline collected before corrections.
- The corporate home page was audited in desktop and mobile modes, along with any additional selected complex public routes.
- The backoffice dashboard or most element-heavy representative view was audited in a valid authenticated state.
- All four Lighthouse scores are recorded for each required run, with available Web Vitals and environment details.
- Verifiable baseline screenshots exist in `/audit/before/`.
- `AUDIT.md` contains the measurement protocol, baseline tables, prioritized findings, code-level root causes, validation plans, and at least two detailed refactor candidates.
- At least one meaningful reusable component or custom hook has replaced real duplication.
- Performance fixes are targeted, evidence-based, and incrementally validated.
- Applicable required findings from any installed performance skill are addressed and its use is documented.
- Corresponding after measurements use the same URLs, modes, and comparable conditions.
- Verifiable final screenshots exist in `/audit/after/`.
- `REPORT.md` explains the implemented corrections, delivered refactor, before/after deltas, biggest impact, tradeoffs, and unresolved limitations.
- At least one Lighthouse score improves for each frontend.
- No correction achieves a score gain by removing required functionality, weakening accessibility/SEO/security, or bypassing real application behavior.
- Focused tests and the applicable test, type-check, lint, build, and smoke checks pass with recorded evidence.
- Existing behavior outside the targeted performance and duplication corrections remains unchanged.

## Scope Boundaries

In scope:

- Lighthouse measurement of both existing frontends;
- representative page selection and repeatable audit methodology;
- `/audit/before/` and `/audit/after/` screenshot evidence;
- `AUDIT.md` and `REPORT.md`;
- source-level root-cause investigation;
- targeted image, font, rendering, loading, hydration, bundle, layout, responsiveness, accessibility, best-practice, or SEO corrections supported by evidence;
- analysis of at least two duplication candidates;
- extraction and integration of at least one shared component or custom hook;
- focused tests and validation needed to prove performance and behavior.

Out of scope unless a newer requirement explicitly adds it:

- redesigning or rewriting either frontend;
- changing product requirements or removing working features to improve scores;
- broad backend optimization, database redesign, or API-contract changes;
- production observability or real-user monitoring infrastructure;
- CDN, hosting, cloud, or deployment migration;
- unrelated dependency upgrades or monorepo restructuring;
- exhaustive optimization of every Lighthouse audit;
- a perfect score of 100;
- Git commits, pushes, pull requests, or new skill installation without the required user authorization.

## Handoff Expectations

The implementation agent should begin with repository inspection and a written measurement/implementation plan. Keep the active project memory bank current with selected pages, baseline evidence, findings, decisions, corrections, metric deltas, validation results, blockers, and next steps.

Before finalizing:

1. Reconcile every required audit run and deliverable against this document.
2. Verify baseline evidence predates implementation changes.
3. Confirm each reported root cause maps to real code or delivery behavior.
4. Confirm the same page/mode matrix was measured after corrections.
5. Confirm at least one score improved independently for each frontend.
6. Verify the required reusable component or custom hook is genuinely integrated.
7. Run and record all applicable regression checks.
8. Review screenshots and reports for sensitive backoffice information.
9. Report metrics that regressed or remained unchanged as honestly as improvements.
10. Update durable implementation memory only after the performance iteration is genuinely finalized.
