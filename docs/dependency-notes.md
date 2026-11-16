# Dependency audit

The installed full development/operations environment was scanned with pip-audit. It flagged CVE-2025-69872 / PYSEC-2026-2447 in `diskcache` 5.6.3, brought in by optional operations tooling. No fixed release was listed by the scanner.

The advisory concerns code execution if an attacker can write a pickle-based cache later read by the application. Keep operations caches private to the local user; never mount untrusted/shared cache folders. This is not an assurance that the advisory is fixed. The inference dependency set excludes diskcache, MLflow, DVC and Evidently; CI audits it separately and fails on findings. A separate non-blocking full-environment audit preserves the known operations finding in its artifact.

Recheck the advisory before sharing an operations host with untrusted users. Do not suppress the finding silently or call the full environment vulnerability-free.
