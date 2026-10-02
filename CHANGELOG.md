# Changelog

All notable changes to this project are documented in this file.

The format is based on [Keep a Changelog](https://keepachangelog.com/en/1.1.0/),
and this project adheres to [Semantic Versioning](https://semver.org/spec/v2.0.0.html).

## [Unreleased]

### Added
- Configuration file `dota2cl.conf`, bundled with the package. On Linux-like
  systems it is placed in `/etc` on first run when `/etc` is writable.
- Settings precedence: defaults < config file < `DOTA2CL_<SECTION>_<KEY>`
  environment variables < command line options.
- `--config` option and `DOTA2CL_CONFIG` environment variable.
- `--no-throttle` and `--no-preload-teams` options, to turn off values
  enabled in the config file.
- Version is derived from git tags using `setuptools-scm`.
- `--version` command line option.
- Version is written to the log file and the CLI header on every run.
- GitHub Actions workflows for testing and for tagged releases.

### Changed
- Renamed to `dota2cl` everywhere. This breaks existing installs and imports:
  - The command is `dota2cl` instead of `dotclient`.
  - The package is `dota2cl` instead of `dotclient`, run as `python -m dota2cl`.
  - The distribution is `dota2cl` instead of `dota2client`. Uninstall the old
    one with `pip uninstall dota2client`.
  - The API client module is `dota2cl.client` instead of `dotclient.dota2cl`.
- Classes renamed to follow PEP 8: `apiClient` to `ApiClient`, `dota2cl` to
  `Dota2Client`, `dotaReporter` to `DotaReporter`, and `topTeamsReport` to
  `TopTeamsReport`.
- The log file is opened when the application starts instead of on import,
  and is written to the user cache directory, or the current directory
  as a fallback, instead of next to the package.
- API timeouts, retries, throttle wait and cache timeout are configurable.
- Packaging moved from `setup.py` to `pyproject.toml`.
- Minimum supported Python version is 3.10.
- Test runner exits with a non-zero code when tests fail.
- Team lookup by name for players with `team_id` 0 uses an index built once,
  instead of scanning all teams for every player.

### Removed
- `main.py`. Run the application with `dota2cl` or `python -m dota2cl`.
- `LOGFILE` environment variable. Use `DOTA2CL_LOGGING_FILE` instead.
- Unused `six` dependency.

### Fixed
- The cache timeout was hard-coded in the client, ignoring the constant.
- With throttling on, the first request waited about a second for no reason.
  The throttle now uses a monotonic clock.
- Console log colors are used only when stderr is a terminal, and can be
  turned off with `NO_COLOR` or `TERM=dumb`.
- API timestamps ending in `Z` failed to parse on Python 3.10.
- `cover.sh` returned success when tests failed.
- Top teams report modified player data stored in the API client cache.
- Report payload was a class attribute shared by all reports, and
  `save_payload()` ignored its argument.

## [0.1.1] - 2026-10-01

### Fixed
- Test suite startup error.
- Load API keys correctly and redact them from logs.
- Refresh expired cache entries and raise errors for invalid API responses.
- Retry rate-limited requests and keep reports running when team lookups fail.
- Parse UTC timestamps robustly for experience calculations.
- Console entry point, CLI help, throttle naming, and team-count validation.

## [0.1.0] - 2026-10-01

### Added
- OpenDota API client with time-based request caching and schema validation.
- Top teams report ranking teams by combined player experience, written as YAML.
- `dotclient` command line tool with team count, log level, team preloading, and throttling options.
- Unit tests, coverage, and profiling scripts.

[Unreleased]: https://github.com/savex/dota2cl/compare/v0.1.1...HEAD
[0.1.1]: https://github.com/savex/dota2cl/compare/v0.1.0...v0.1.1
[0.1.0]: https://github.com/savex/dota2cl/releases/tag/v0.1.0
