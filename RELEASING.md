# Releasing

What to update when a pull request is merged and when a version is released.

## After a pull request is merged

- `CHANGELOG.md`: one line under `## [Chưa phát hành]` saying what changed for the user, with the PR
  number. Part of every PR, not a follow-up.
- `README.md`: when a feature or the list of what this edition lacks changes.

## Branches

- `next` holds features, `patch` fixes for the current release, and `main` only what was released.
- After a release, bring `main` into `next` and `patch` through PRs.

## Releasing a version

The release is `X.Y.Z-N` (`N` is the packaging revision), tagged `ibus-ngosen-X.Y.Z-N`.

1. On a `release/X.Y.Z` branch, point the `ngosen` submodule at a released `ngosen-*` tag
   (`misc/check-core-tag.sh` must pass) and set the version in `CMakeLists.txt`,
   `packaging/debian/changelog`, `packaging/rpm/ibus-ngosen.spec` (with a `%changelog` entry) and
   `packaging/arch/PKGBUILD`. `packaging/check-version.sh X.Y.Z-N` must pass; the release workflow runs it
   on the tag.
2. `CHANGELOG.md`: turn `## [Chưa phát hành]` into `## [X.Y.Z-N] — DD/MM/YYYY` with a one-line summary,
   the core tag it uses and a link to the release, and start a new empty `## [Chưa phát hành]`.
3. Merge the PR into `main` once CI passes, then tag the merge commit through the API, not from a local
   checkout, where a stale local tag can point at the wrong commit:

   ```
   gh api repos/ngosen/ibus-ngosen/git/refs -f ref=refs/tags/ibus-ngosen-X.Y.Z-N -f sha=<merge commit>
   ```

4. Check the draft release before publishing: all packages and `SHA256SUMS` are attached and the sums
   match, and each pattern `install.sh` in the `ngosen` repository looks for matches exactly one line of
   `SHA256SUMS`; release notes list only the systems typed on with this version.
5. Publish it: `gh release edit ibus-ngosen-X.Y.Z-N --repo ngosen/ibus-ngosen --draft=false --latest`.
   Arch packages are attached to the release like the others; there is no AUR package.
6. The APT and pacman repositories are built in `ngosen/ngosen` and carry both editions. Rebuild them so
   they pick up this release, and check that the run passes:
   `gh workflow run package-repos.yml --repo ngosen/ngosen --ref <newest ngosen-* tag>`.
