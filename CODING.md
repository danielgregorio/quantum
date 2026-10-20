# Coding guidelines

Quantum is going public, so the repository is written in **English**.

## Language

- **Everything in the repository is English**: code (identifiers, comments,
  docstrings), error messages, what a page, a screen or a command says to its
  user, tests (names, comments, their data), example apps and their content,
  `SPEC.md`, docs, CHANGELOG, commit messages. No exceptions for Portuguese:
  whoever asks for the work, in whatever language, the repository's text is
  English.
- **Translations are the one place for other languages**, and they translate
  an English source: the site's pages under `docs/pt/`, `docs/es/` and
  `docs/zh/` (with their glossaries and the strings of the site's theme), and
  a game's `qg:language` phrases. Nothing else is written in another language
  first.
- What is not prose stays as it is: a person's or a place's name, the name of
  a national format a validator checks (`cep`, `cpf`, `cnpj`), a keyboard
  layout (`br`, `abnt2`), a character a test types to exercise it (`ç`, `ñ`).
- The Portuguese that existed was translated in dedicated passes (0.21, and
  2026-10-20 for `os/`, `projects/tasks` and the rest), not piecemeal in
  unrelated changes: a rename mixed into a feature commit hides the feature.

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
