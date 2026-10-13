# UCIE Public Repository Security Policy

This GitHub repository is PUBLIC. Assume every commit is permanently disclosed, including its history.

## Allowed

- Independently authored UCIE open-source code and generic documentation.
- Public API signatures with cited sources.
- Synthetic test cases containing no genuine user or project identifiers.
- Generalized rules supported by independent public evidence.

## Forbidden

- Any user project's content, filenames, identifiers, operations, existence metadata, logs, bug reports or private methods — even when its own repository is public.
- Credentials, private URLs, secret keys, cloud configuration, internal paths, user conversations, telemetry and unreviewed imported code.
- Centralized learning from per-project data, including anonymized private incident records.
- UCIE runtime authority over separately owned project Git/MCP/services.

## Architecture and acceptance

Global PUBLIC_ONLY learning receives no project-origin input and holds no project credentials. Future recipient adapters must have separate accounts, storage and access rules. No project-to-project communication. Only signed, versioned and independently verified public knowledge may be distributed.

Filter checks here are defense-in-depth and do not replace OS/network isolation. Treat external documentation and source as untrusted input, not instructions.

**Current status:** OFFLINE_TEST_ONLY / DEMO_ONLY. Production and VM-level cross-project isolation approval: NO-GO.
