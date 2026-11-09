# AGENTS.md

Rules for anyone (human or coding agent) changing this repository. The typing logic lives in the
`ngosen` submodule ([ngosen/ngosen](https://github.com/ngosen/ngosen)); its `AGENTS.md` applies to
anything sent there, and the rules below follow it. Outside the code, fcitx5-lotus is named only in the
README credit line and the credit line on the settings About page.

Most of this work is done with an AI coding agent. That is allowed, but the output has to read like a
careful human wrote it, and the person sending it must be able to explain every line.

## What this repository is

The IBus engine of Ngó Sen for GNOME, where IBus is the input method framework. By default it types
with Sen, as the fcitx5 edition does: straight into fields that report the text around the cursor, and
with an underlined preedit where a field cannot take that. That path handles how GNOME Shell passes
deletions on and keeps the core's click check. The mode menu keeps Sen or the underline per app, and a
setting turns Sen off for every app without a pick. On Wayland the engine learns the name of the app GNOME Shell relays from GNOME's portal,
as fcitx5 does, so the core's rules for single apps run here too; such rules still go into the core. A
tap of Ctrl+Shift switches between Vietnamese and English inside the engine, for every app at once;
Super+Space still switches GNOME's input sources.

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

## Testing in a real GNOME session

The typing rules are shared with fcitx5-ngosen and tested in the core, but the way text reaches apps is
not: GNOME Shell relays most apps under its own name, sends the text around the cursor only when asked,
and can deliver two commits in one batch. Bugs on that path show up only in a real session, so how much
to test there depends on what the change touches:

- **None:** typing rules in the core, settings, translations, packaging, CI and docs. `ctest` and CI are
  enough.
- **Short check, about 10 minutes:** anything in how the engine commits, shows the preedit, deletes,
  follows focus or forwards keys through GNOME Shell (`src/ngosen-ibus-engine.cpp`,
  `src/ngosen-ibus-host.cpp`, `src/ngosen-ibus-shell.cpp`), and a core update that changes when it waits
  for the app. On GNOME 50, type a Telex word with a BackSpace in it 3 times in a Firefox page and 3 times
  in a Chrome page, and "tooi" twice in the Firefox address bar while it autofills a bookmarked site.
  Say in the PR what was typed and what came out.
- **Full check, before a release** and for a change on that path with no earlier measurement: the same
  apps with 10 runs each at a slow and a fast pace, plus GTK, Qt, LibreOffice Writer and a terminal.

Write down before each run which runs should fail and which should pass; a run that differs proves
nothing until it is explained.

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
