# Overview

The `dota2cl` package is a portable client for retrieving data from the OpenDota API.

## Design Goals

- Provide a client class that is as extensible as possible.
- Support simple time-based caching of requests.
- Validate endpoints against the API schema where possible.
- Keep the base API class reusable, so it can work with other OpenAPI-based services with minimal changes.

## Reporting

Reports are generated through overridable methods. A report subclass of `DotaReporter` implements `generate_payload()` for the data and, for HTML output, `html_body()` for the markup. The base class handles the output format and destination.

The report is written as YAML to stdout by default. Give a file path to save it, and use `-f html` for an HTML page:

```bash
dota2cl                          # YAML to stdout
dota2cl report.yaml              # YAML to a file
dota2cl -f html top_teams.html   # HTML page
```

The default format can also be set with `format` in the `[report]` section of the config file.

HTML reports share the stylesheet in `dota2cl/templates/report.css`. Reports can also be rendered with jinja2 templates from the same folder by creating them with `use_jinja2=True`. This is not a command line option. Install jinja2 with `pip install ".[html]"`.

## Known Data Issue

During implementation, the `proPlayers` data was found to be inconsistent with the `teams` listing. Many players have a `team_id` of `0`, which is incorrect, although some of them still carry the team's `name` and/or `tag`.

To work around this, the client can look up a player's team by name. This lookup requires the teams data to be loaded at startup, which is enabled with the `--preload-teams` option.

## Additional Notes

- Code documentation is provided as inline comments.
- The project includes unit tests, coverage reporting, and profiling scripts.

## Installation

```bash
pip install .
dota2cl --version
```

The application can also be run as a module with `python -m dota2cl`.

For development, install in editable mode with test dependencies:

```bash
pip install -e ".[test]"
./cover.sh
```

## Configuration

Settings are applied in the following order, each one overriding the previous:

1. Application defaults.
2. The configuration file, `dota2cl.conf`.
3. Environment variables named `DOTA2CL_<SECTION>_<KEY>`, for example `DOTA2CL_API_THROTTLE=true` or `DOTA2CL_REPORT_NUM_TEAMS=10`. The API key can also be set with `OPENDOTA_API_KEY`.
4. Command line options.

A default configuration file with every setting and its default value is included in the package. The file is located as follows:

- `--config PATH` or the `DOTA2CL_CONFIG` environment variable, if set.
- On Linux-like systems, `/etc/dota2cl.conf`. If the file does not exist and `/etc` is writable, it is created from the bundled copy on the first run. Otherwise, the bundled copy is used.
- On other systems, the bundled copy in the package folder.

The log file is written to the user cache directory (`~/.cache/dota2cl/` on Linux, `~/Library/Caches/dota2cl/` on macOS, `%LOCALAPPDATA%\dota2cl\` on Windows), or to the current directory if the cache directory cannot be used. Set `file` in the `[logging]` section to choose another location.

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
