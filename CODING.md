# Coding guidelines

Quantum is going public, so the repository is written in **English**.

## Language

- **Everything in the repository is English**: code (identifiers, comments,
  docstrings), error messages, tests (names, comments), `SPEC.md`, docs,
  CHANGELOG, commit messages.
- **New code is English (since 2026-09-24).** The Portuguese that existed —
  `SPEC.md`, the tests, the framework code, the admin, the guide — was
  translated in a dedicated pass in 0.21, not piecemeal in unrelated changes:
  a rename mixed into a feature commit hides the feature.
- Left in Portuguese on purpose: `projects/tarefas`, an app whose content is
  Portuguese.
- Domain words that are not prose stay as they are — `cnpj` (a Brazilian tax
  ID rule), a column called `nome` in an app's schema.
- Example apps may show content in any language (`projects/tarefas` is a
  Portuguese to-do app); their code and comments are English.

## Code

- Type hints on public functions; docstrings on anything non-obvious — say
  *why*, and what went wrong before when a rule exists because of a bug.
- Absolute imports: `from quantum.core.parser import QuantumParser`.
- Parsers in `quantum/core/parsers/<category>/`, executors in
  `quantum/runtime/executors/<category>/`, registered in their registries
  (see `CLAUDE.md`).

## Behavior changes

Every behavior change ships with:

1. a rule with an ID in `SPEC.md`;
2. a test that cites the ID and fails on the old code;
3. an example and a guide page when it is a user-facing feature;
4. a CHANGELOG entry.

Nothing is accepted without effect, and nothing fails silently: an attribute
that does nothing is a parse error; an input that cannot be honored is an
error that says what to do.
