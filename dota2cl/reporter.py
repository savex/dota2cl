#    Author: Alex Savatieiev (a.savex@gmail.com)
#    November 2025
import html
import os
import sys
import ruamel.yaml

from abc import ABC, abstractmethod
from datetime import datetime, timezone
from io import StringIO

from dota2cl import __version__
from dota2cl.client import Dota2Client
from dota2cl.const import default_report_format
from dota2cl.exceptions import ApiRequestError
from dota2cl.log import logger_cli

try:
    # Optional, only needed when reports are rendered with jinja2
    import jinja2
except ImportError:
    jinja2 = None

# HTML templates and the stylesheet shared by all HTML reports
templates_dir = os.path.join(os.path.dirname(__file__), "templates")
# Shown in HTML reports in place of missing values
missing_value = "\u2014"


class DotaReporter(ABC):
    """Base class for reporting data from the API client."""
    # Report title, used in HTML output
    title = "Dota 2 report"
    # Jinja2 template in templates_dir, used only when use_jinja2 is set
    html_template = "base.html"

    def __init__(self, args, use_jinja2: bool = False) -> None:
        # Set per instance, as a class level dict would be shared
        # between all reports
        self.payload: dict = {}
        # Path, '-' for stdout or a file-like object
        self.output = args.output
        self.format = getattr(args, "format", default_report_format)
        self.yaml = ruamel.yaml.YAML()
        self.yaml.preserve_quotes = True
        self.yaml.explicit_start = True
        self.throttle = args.throttle
        # Not exposed as a command line option on purpose.
        # Built-in HTML rendering is used when jinja2 is not installed.
        if use_jinja2 and jinja2 is None:
            logger_cli.warning("jinja2 is not installed, "
                               "using built-in HTML rendering")
            use_jinja2 = False
        self.use_jinja2 = use_jinja2

    # To provide convenience for users of the class, make it callable
    def __call__(self) -> None:
        self.generate_payload()
        self.save_payload(self.payload)

    # To make it uniform, subclasses should implement this method
    # to generate the payload for the report
    @abstractmethod
    def generate_payload(self) -> None:
        """Generates the payload for the report.
        To be implemented by subclasses."""
        raise NotImplementedError("Subclasses must implement this method")

    @staticmethod
    def parse_time(value: str) -> datetime:
        """
        Parse API ISO 8601 timestamp, e.g. '2025-02-21T10:00:14.982Z'.
        Fractional seconds are optional. Timestamps without
        a timezone are treated as UTC.
        Raises ValueError or TypeError for invalid values.
        """
        # Python < 3.11 fromisoformat() does not accept the 'Z' suffix
        if isinstance(value, str) and value.endswith("Z"):
            value = value[:-1] + "+00:00"
        parsed = datetime.fromisoformat(value)
        if parsed.tzinfo is None:
            parsed = parsed.replace(tzinfo=timezone.utc)
        return parsed

    @staticmethod
    def na(value):
        """Return the value, or a placeholder if it is missing."""
        return missing_value if value is None else value

    @classmethod
    def esc(cls, value) -> str:
        """Escape a value for HTML output."""
        return html.escape(str(cls.na(value)))

    @staticmethod
    def format_experience(seconds: float | None) -> str:
        """Format experience in seconds as days."""
        if seconds is None:
            return missing_value
        return f"{seconds / 86400:,.0f} days"

    def save_payload(self, payload: dict) -> None:
        """Render the payload in the selected format and write it out."""
        self.write(self.render(payload))

    def render(self, payload: dict) -> str:
        # New formats are added as render_<format> methods
        return getattr(self, f"render_{self.format}")(payload)

    def render_yaml(self, payload: dict) -> str:
        _out = StringIO()
        self.yaml.dump(payload, _out)
        return _out.getvalue()

    def render_html(self, payload: dict) -> str:
        context = {
            "title": self.title,
            "generated": datetime.now(timezone.utc).strftime(
                "%Y-%m-%d %H:%M UTC"),
            "version": __version__,
            "css": self.load_css(),
        }
        if self.use_jinja2:
            return self.render_jinja2(payload, context)
        return self.html_page(self.html_body(payload), context)

    def render_jinja2(self, payload: dict, context: dict) -> str:
        env = jinja2.Environment(
            loader=jinja2.FileSystemLoader(templates_dir),
            autoescape=True, trim_blocks=True, lstrip_blocks=True)
        env.filters["na"] = self.na
        env.filters["experience"] = self.format_experience
        return env.get_template(self.html_template).render(
            payload=payload, **context)

    @staticmethod
    def load_css() -> str:
        with open(os.path.join(templates_dir, "report.css"),
                  encoding="utf-8") as f:
            return f.read()

    def html_page(self, body: str, context: dict) -> str:
        """Wrap the report body into a full HTML page.
        Mirrors templates/base.html."""
        _title = html.escape(context["title"])
        return (
            "<!DOCTYPE html>\n"
            '<html lang="en">\n<head>\n'
            '<meta charset="utf-8">\n'
            '<meta name="viewport" '
            'content="width=device-width, initial-scale=1">\n'
            f"<title>{_title}</title>\n"
            f"<style>\n{context['css']}</style>\n"
            "</head>\n<body>\n"
            '<header class="page-head">\n'
            f"<h1>{_title}</h1>\n"
            f'<p>Generated {context["generated"]}</p>\n'
            "</header>\n"
            f"<main>\n{body}</main>\n"
            '<footer class="page-foot">'
            f"dota2cl {html.escape(context['version'])} "
            "&middot; data from OpenDota</footer>\n"
            "</body>\n</html>\n"
        )

    @classmethod
    def html_stats(cls, stats: dict) -> str:
        """Labeled values shown as a row of cells."""
        cells = "".join(f"<div><dt>{html.escape(label)}</dt>"
                        f"<dd>{cls.esc(value)}</dd></div>"
                        for label, value in stats.items())
        return f'<dl class="stats">{cells}</dl>\n'

    def html_body(self, payload: dict) -> str:
        """Return the HTML for the report data, without the page around it.
        To be implemented by subclasses that support HTML output."""
        raise NotImplementedError(
            f"{type(self).__name__} does not support HTML output")

    def write(self, text: str) -> None:
        if hasattr(self.output, "write"):
            self.output.write(text)
        elif self.output in (None, "-"):
            sys.stdout.write(text)
        else:
            # The file is opened only now, so a failed report
            # does not leave an empty file behind
            with open(self.output, "w", encoding="utf-8") as f:
                f.write(text)
            logger_cli.info(f"Report saved to '{self.output}'")


class TopTeamsReport(DotaReporter):
    """Report for top teams by combined player experience."""
    title = "Top Dota 2 teams by experience"
    html_template = "top_teams.html"

    def __init__(self, args, api_client: Dota2Client, **kwargs) -> None:
        super().__init__(args, **kwargs)
        self.teams_count = args.num_teams
        self.preload_teams = args.preload_teams
        self.api_client = api_client

    @staticmethod
    def _group_teams_by(teams, key: str) -> dict[str, list[dict]]:
        """
        Group teams by the value of the given key, e.g. 'name' or 'tag'.
        Values are not guaranteed to be unique, so each maps to a list.
        """
        grouped: dict[str, list[dict]] = {}
        for team in teams:
            grouped.setdefault(team.get(key), []).append(team)
        return grouped

    @staticmethod
    def _resolve_team_id(player: dict,
                         teams_by_name: dict[str, list[dict]] | None
                         ) -> int | None:
        """
        Return the player's team ID, or None if the player
        cannot be assigned to a team.
        There is a discrepancy in the API where some players have
        team_id == 0, but there is no team with ID 0. Those are looked up
        by team name instead. teams_by_name is None when teams data
        is not preloaded.
        """
        team_id = player.get("team_id")
        if team_id != 0:
            return team_id

        _player_name = player.get("personaname")
        if teams_by_name is None:
            # No name lookup possible as it will generate
            # a lot of requests
            logger_cli.warning(
                f"Player '{_player_name}' "
                "has team_id 0 and teams data is not preloaded")
            return None

        team_name = player.get("team_name")
        if team_name is None:
            # Corrupted data, team_id is 0 and no team_name
            logger_cli.warning(
                f"Player '{_player_name}' has team_id 0 and no team_name")
            return None

        matches = teams_by_name.get(team_name, [])
        if len(matches) > 1:
            # Additional logic of data matching could be implemented here
            # to try to find the correct team, but for now skip the player
            logger_cli.warning(
                f"Multiple teams found with name '{team_name}' "
                f"for player '{_player_name}'")
            return None
        if not matches:
            logger_cli.warning(
                f"No team found with name '{team_name}' "
                f"for player '{_player_name}'")
            return None

        # The only proper output is when count is 1
        team_id = matches[0].get("team_id")
        logger_cli.debug(
            f"Found team ID {team_id} for player '{_player_name}' "
            f"with team name '{team_name}'")
        return team_id

    def generate_payload(self) -> None:
        """Creates a report of the top teams by combined player experience."""
        if self.preload_teams:
            teams_data = {t["team_id"]: t for t in self.api_client.get_teams()}
            # I've chosen to use team name
            # It could be possible to use team tag too
            teams_by_name = self._group_teams_by(teams_data.values(), "name")
        else:
            teams_data = {}
            teams_by_name = None

        players = self.api_client.get_pro_players()
        # Calculate experience for each player
        # and create teams with their players

        # it is more efficient to do it in one pass
        # instead of multiple passes over the data
        teams = {}
        # API timestamps are in UTC, so compare against UTC time.
        # Taken once, so all players are measured from the same moment.
        _now = datetime.now(timezone.utc)
        for player in players:
            if player.get("full_history_time") is None:
                continue

            try:
                _history_start = self.parse_time(
                    player.get("full_history_time"))
            except (ValueError, TypeError):
                logger_cli.warning(
                    f"Player '{player.get('personaname')}' has invalid "
                    f"full_history_time "
                    f"'{player.get('full_history_time')}', skipping")
                continue
            _experience = (_now - _history_start).total_seconds()
            # Player dicts are shared with the API client cache,
            # so work on a copy to keep cached data unchanged.
            # Shallow copy is enough as only top-level keys are set.
            player = dict(player)
            player["experience"] = _experience

            team_id = self._resolve_team_id(player, teams_by_name)
            player["team_id"] = team_id
            if team_id is None:
                continue

            if team_id not in teams:
                teams[team_id] = {"experience": 0, "players": []}
            teams[team_id]["players"].append(player)
            teams[team_id]["experience"] += player["experience"]

        # Sort teams by combined player experience
        sorted_teams = sorted(
            teams,
            key=lambda team: teams[team]["experience"],
            reverse=True
        )

        # Get top N teams
        top_teams = sorted_teams[:self.teams_count]

        # """
        # * Team Name
        # * Team ID
        # * Wins
        # * Losses
        # * Rating
        # * Team Experience
        # * For each Player:
        #     * Personaname
        #     * Player Experience
        #     * Country Code
        # """
        top_teams_data = []
        for team_id in top_teams:
            if team_id not in teams_data:
                try:
                    teams_data[team_id] = \
                        self.api_client.get_team_by_id(team_id)
                except ApiRequestError as e:
                    # Keep the team in the report with empty details
                    # instead of failing the whole report
                    logger_cli.warning(
                        f"Failed to get details for team {team_id}: {e}")
                    teams_data[team_id] = {}
            _team = {
                "Team Name": teams_data[team_id].get("name"),
                "Team ID": team_id,
                "Wins": teams_data[team_id].get("wins"),
                "Losses": teams_data[team_id].get("losses"),
                "Rating": teams_data[team_id].get("rating"),
                "Team Experience": teams[team_id]["experience"],
                "Players": []
            }
            for player in teams[team_id]["players"]:
                _team["Players"] += [{
                    "Personaname": player.get("personaname"),
                    "Player Experience": player.get("experience"),
                    "Country Code": player.get("country_code"),
                }]
            top_teams_data += [_team]
        self.payload = {"top_teams": top_teams_data}

    def html_body(self, payload: dict) -> str:
        """Team cards. Mirrors templates/top_teams.html."""
        if not payload["top_teams"]:
            return '<p class="empty">No teams found</p>\n'
        cards = ""
        for rank, team in enumerate(payload["top_teams"], start=1):
            players = "".join(
                '<div class="player">'
                f'<span>{self.esc(p["Personaname"])}</span>'
                f'<span class="country">{self.esc(p["Country Code"])}</span>'
                f'<span class="num">'
                f'{self.format_experience(p["Player Experience"])}</span>'
                "</div>\n"
                for p in team["Players"])
            cards += (
                '<article class="team">\n'
                '<header class="team-head">'
                f'<span class="rank">#{rank}</span>'
                f'<h2>{self.esc(team["Team Name"])}</h2>'
                f'<span class="team-id">ID {self.esc(team["Team ID"])}</span>'
                "</header>\n"
                + self.html_stats({
                    "Wins": team["Wins"],
                    "Losses": team["Losses"],
                    "Rating": team["Rating"],
                    "Experience":
                        self.format_experience(team["Team Experience"]),
                }) +
                '<div class="players">\n'
                '<div class="player head"><span>Player</span>'
                '<span>Country</span><span class="num">Experience</span>'
                "</div>\n"
                f"{players}"
                "</div>\n"
                "</article>\n"
            )
        return f'<section class="teams">\n{cards}</section>\n'
