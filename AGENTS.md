# AGENTS.md

Rules for anyone (human or coding agent) changing this repository. The typing logic lives in the
`ngosen` submodule ([ngosen/ngosen](https://github.com/ngosen/ngosen)); its `AGENTS.md` applies to
anything sent there, and the rules below follow it. Outside the code, fcitx5-lotus is named only in the
README credit line and the credit line on the settings About page.

Most of this work is done with an AI coding agent. That is allowed, but the output has to read like a
careful human wrote it, and the person sending it must be able to explain every line.

## What this repository is

The IBus engine of Ngó Sen for GNOME, where IBus is the input method framework. It types with an
underlined preedit, as IBus engines usually do. An option types straight into fields that report the
text around the cursor; that path handles how GNOME Shell passes deletions on and keeps the core's
click check, and fixes for single apps still belong to fcitx5-ngosen. A tap of Ctrl+Shift switches between Vietnamese and English inside the engine,
for every app at once; Super+Space still switches GNOME's input sources.

## Code

- **English only** for identifiers, comments, log strings and commit messages. User-facing strings are
  translatable, with Vietnamese in `po/vi.po`.
- **Comments say why, not what or how.** Most comments are one line; a block of more than 3 lines needs a
  real reason.
- **No measurements, dates or history in code.** They belong in the commit message or PR. Refer to a real
  issue as `#123`, and to one in the core repository as `ngosen/ngosen#123`.
- **Typing logic goes into the core, not here.** This repository holds the IBus shell: it turns IBus
  calls into `ngosen::Host`, `ngosen::KeyPress` and `ngosen::EngineResources` (headers in
  `ngosen/src/core/`). A change in how words are typed is a PR to ngosen/ngosen.
- **The submodule points at a released `ngosen-*` tag** on `main` and in every release. A branch may pin
  an untagged commit while a core change waits for its release; CI refuses it on the way to `main`.
- **Never lose or double the preedit.** On reset, focus out and disable the app commits the preedit
  itself, so the shell drops it without committing.
- **No "lotus" in names.** `misc/check-new-names.sh` enforces this in CI.
- **Match surrounding code.** clang-format (`.clang-format`), `camelCase` functions, `snake_case_`
  members, functions under ~50 lines. Run clang-format before pushing; CI fails on any diff.
- **Build as C++17.** Ubuntu 24.04 is the oldest system supported.
- **Installing the package is all a user does.** As with ibus-unikey, the package plus adding the input
  source in GNOME Settings must be enough: no settings to edit, no `input` group or other permission, no
  service to enable. A library the engine loads at run time is still a dependency in every package
  (`packaging/debian/control`, both RPM specs, `packaging/arch/PKGBUILD`), and without it the engine
  falls back to a safe behaviour instead of failing.
- **A bug fix comes with a test that fails without it.** Check this by undoing the fix and watching that
  test, and only that test, fail.
- **Reuse one build directory.** Rebuild in `build/`; a new directory per experiment wears out the SSD.

## Commits

- Conventional Commits, imperative subject of at most 72 characters.
- The body says what was wrong for the user and why this fixes it. Numbers go here, one line each, with
  how they were measured.
- One logical change per commit; every commit builds and passes `ctest`.
- No AI trailer in commits. AI assistance is disclosed in PR descriptions and comments, which end with the
  line `Assisted-by: AI`.

## Pull requests

Every change goes through a PR. Features go into `next`; a fix for a bug in the current release goes
into `patch`. Never merge into `main` directly; `main` changes only through a release PR
([RELEASING.md](RELEASING.md)). Each PR adds a line under `## [Chưa phát hành]` in
[CHANGELOG.md](CHANGELOG.md): what changed for the user, with the PR number, in Vietnamese.
