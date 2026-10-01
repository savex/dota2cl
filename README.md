# Overview

The `dotclient` module is a portable client for retrieving data from the OpenDota API.

## Design Goals

- Provide a client class that is as extensible as possible.
- Support simple time-based caching of requests.
- Validate endpoints against the API schema where possible.
- Keep the base API class reusable, so it can work with other OpenAPI-based services with minimal changes.

## Reporting

Reports are generated through overridable methods. This makes it possible to add new report types, including HTML reports.

## Known Data Issue

During implementation, the `proPlayers` data was found to be inconsistent with the `teams` listing. Many players have a `team_id` of `0`, which is incorrect, although some of them still carry the team's `name` and/or `tag`.

To work around this, the client can look up a player's team by name. This lookup requires the teams data to be loaded at startup, which is enabled with the `--preload-teams` option.

## Additional Notes

- Code documentation is provided as inline comments.
- The project includes unit tests, coverage reporting, and profiling scripts.

## Installation

```bash
pip install .
dotclient --version
```

For development, install in editable mode with test dependencies:

```bash
pip install -e ".[test]"
./cover.sh
```

## Versioning and Releases

The project follows [Semantic Versioning](https://semver.org/). The version is not stored in the source code; `setuptools-scm` derives it from the latest git tag at build time:

- A tagged commit `v0.2.0` builds as `0.2.0`.
- Commits after a tag build as development versions, for example `0.2.1.dev3+g4ddaef9`.

To make a release:

1. Move the entries under `[Unreleased]` in [CHANGELOG.md](CHANGELOG.md) to a new version section and commit.
2. Tag the commit and push the tag:

   ```bash
   git tag v0.2.0
   git push origin v0.2.0
   ```

3. The release workflow runs the tests, builds the package, and publishes a GitHub release with the wheel and source archive attached.
