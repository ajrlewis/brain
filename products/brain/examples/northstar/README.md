# Northstar example corpus

Northstar is a wholly fictional private-equity firm used for local demonstrations and
PostgreSQL integration tests. `seed/manifest.yaml` is the deterministic database-seed
contract. It names every stable identity and references the reviewable UTF-8 Markdown in
`documents/`; the seed command never contacts an external provider.

The text-only Skills are example content and are not production defaults or currently
inserted by `brain-seed-northstar`. Binary assets are intentionally deferred until Brain has
an explicit asset storage and delivery contract.
