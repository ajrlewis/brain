# API Documentation Preset

Adopted for Brain's typed Python, HTTP, and MCP contracts. FastAPI OpenAPI and callable documentation must describe authorization, provenance, version selection, and failure behavior where relevant.

- Give every callable a clear, typed signature so editors and static tools can expose its contract.
- Use the language's native documentation format, such as docstrings, JSDoc or TSDoc, XML documentation comments, or rustdoc.
- Require useful documentation for public modules, types, functions, and methods, and for internal callables whose behavior is not obvious from their name and signature. If the repository mandates documentation on every method, preserve and enforce that stronger rule.
- Document the contract rather than restating the implementation: purpose, important parameters and return values, errors, side effects, units, nullability, ordering, authorization, and lifecycle constraints where relevant.
- Add a concise example when correct usage is otherwise difficult to infer.
- Keep documentation beside the code it describes and update it in the same change as behavior. Stale documentation is a defect.
- Prefer clear names and types over verbose comments for trivial private implementation details.
- Preserve the repository's documentation generator and lint rules; record exact validation commands in `.agents/COMMANDS.md`.
