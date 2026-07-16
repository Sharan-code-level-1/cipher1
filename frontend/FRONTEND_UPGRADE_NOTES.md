# AutoClaim AI Frontend Upgrade Notes

This frontend-only upgrade keeps the existing backend parameters, routes, payload names, role routing and claim workflow intact.

## What changed

- Upgraded the login/register experience into a clean Apple-inspired product layout using system fonts, large typography and a motion evidence-visual hero.
- Improved global visual system: cards, buttons, inputs, badges, tables, page titles and spacing.
- Added responsive mobile navigation to the app shell.
- Improved logout behavior by calling `/auth/logout` before clearing local state.
- Fixed login failure cleanup so partial tokens are cleared if `/auth/me` fails.
- Fixed multipart upload handling by allowing Axios/browser to set the multipart boundary.
- Added frontend image selection validation for file count, MIME type, duplicate files and 5 MB max size.
- Improved new-claim page with clearer submission states while keeping the same backend sequence: create claim -> upload images -> submit claim.
- Refreshed dashboard, vehicles, claims list, claim detail and surveyor queue layouts.

## Validation completed

- `npm install --include=dev` passed.
- `npm run build` passed.
- `npm audit --audit-level=moderate` returned 0 vulnerabilities.
- Vite dev server returned HTTP 200 on `/login`.

## Known remaining gap

The main JS bundle is above Vite's 500 KB warning threshold because all dashboard/chart pages are loaded in the main route tree. This is not a build blocker. The next safe upgrade is route-level lazy loading.
