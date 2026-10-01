# Brief

This dotclient module written as a portable means to get information from OPENDOTA API.
Main goals were:
- provide client class with as much extendability as possible
- mentioned class should have a simple timed caching ability of requests
- also, client should be able to check handles against schema if possible
- main api base class should be reusable with minimal updates to use against different openapi based services

Reporting is done with an overloaded methods to able to create different types and potentially handle HTML reports as well.

All comments are inline.

During the implementation it was discovered that proPlayers data has discrepancies with 'teams' listing.
In specific, many players has team_id of '0', which is not correct. Some of them have team's 'name' and/or 'tag'.
So, additional team_name lookup was implemented which is possible if teams data will be preloaded on the start.
It can be arranged by setting corresponding option.

Additional time was spent to include coverage, some unittests and profiling