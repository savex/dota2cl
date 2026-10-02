#    Author: Alex Savatieiev (a.savex@gmail.com)
#    November 2025
import ruamel.yaml

from abc import ABC, abstractmethod
from datetime import datetime, timezone

from dota2cl.client import Dota2Client
from dota2cl.exceptions import ApiRequestError
from dota2cl.log import logger_cli


class DotaReporter(ABC):
    """Base class for reporting data from the API client."""

    def __init__(self, args) -> None:
        # TODO: Add jinja2 support to render report as HTML or Markdown
        # Set per instance, as a class level dict would be shared
        # between all reports
        self.payload: dict = {}
        self.output = args.output
        self.yaml = ruamel.yaml.YAML()
        self.yaml.preserve_quotes = True
        self.yaml.explicit_start = True
        self.throttle = args.throttle

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

    def save_payload(self, payload: dict) -> None:
        # TODO: Add option to save as JSON or YAML
        self.yaml.dump(payload, self.output)


class TopTeamsReport(DotaReporter):
    """Report for top teams by combined player experience."""
    def __init__(self, args, api_client: Dota2Client) -> None:
        super().__init__(args)
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
