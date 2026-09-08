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
