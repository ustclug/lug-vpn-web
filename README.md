# LUG VPN web application

## Configuration

The application loads `config/example.py` first, then overlays
`config/default.py` when that file exists. Copy the example file and edit it for
each deployment. `config/default.py` is ignored by Git and excluded from Docker
build contexts.

The deployment-specific options are:

- `SITE_NAME`: application-owned branding used in page titles and email text.
- `APPLICATION_REASONS`: structured application reasons. An empty list hides
  the single-select field; free-form text remains available and optional.
- `LIBRARY_API_URL`: Library API endpoint. A falsey value hides and disables all
  checking features. `LIBRARY_API_TIMEOUT` is the request timeout in seconds.
- `CONSTITUTION_DOCUMENTS`, `TERMS_DOCUMENTS`, and `USAGE_DOCUMENTS`: ordered lists of
  `(tab_title, filename)` tuples. Filenames must be relative to `app/doc`.
- `APPLICATION_CONFIRMATION_ENABLED`: show Terms of Service in a confirmation
  modal before application submission. The modal is disabled with a warning if
  `TERMS_DOCUMENTS` is empty.

Markdown files are rendered as Jinja templates before Markdown conversion. The
documentation source must therefore be trusted. Missing or invalid paths log a
warning and render `*(missing)*`. Usage documents are rendered on the user
dashboard; an empty `USAGE_DOCUMENTS` list intentionally hides that section.

## Container deployment

The image contains neither operator configuration nor documentation. Mount them
at these paths when running the container:

```text
/srv/lugvpn-web/config/default.py
/srv/lugvpn-web/app/doc
```

The configuration mount is optional: without it the application uses
`config/example.py`. The documentation mount may be absent, in which case each
referenced document displays the missing-document placeholder. `TZ` remains an
environment variable and defaults to `Asia/Shanghai`.

Both service variants use the same `ustclug/lug-vpn-web:latest` image and supply
their differences through these mounts.

## Database performance

User Management joins the `monthtraffic` and `lastmonthtraffic` views, which
aggregate `radacct` records by their session start month. An index beginning
with `acctstarttime` allows these queries to scan the relevant month instead
of the full accounting history. The existing `(username, acctstarttime)` index
serves per-user queries and should be retained.

Check `SHOW INDEX FROM radius.radacct` first. If no index begins with
`acctstarttime`, add one (the following syntax is for MySQL 8.0 with InnoDB):

```sql
ALTER TABLE radius.radacct
  ADD INDEX idx_radacct_acctstarttime (acctstarttime),
  ALGORITHM=INPLACE,
  LOCK=NONE;
```

Index creation consumes I/O and can briefly require metadata locks, even with
`LOCK=NONE`. Compare `EXPLAIN ANALYZE SELECT * FROM monthtraffic` and the same
query for `lastmonthtraffic` before and after the change to check actual scan
counts and execution times; `EXPLAIN ANALYZE` executes the query. On a MySQL
8.0.46 deployment, both views previously scanned the full
`(username, acctstarttime)` index, and adding the time index noticeably improved
User Management loading.
