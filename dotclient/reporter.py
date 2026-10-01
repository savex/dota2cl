#    Author: Alex Savatieiev (a.savex@gmail.com)
#    November 2025
import ruamel.yaml

from abc import ABC, abstractmethod
from datetime import datetime

from dotclient.dota2cl import dota2cl
from dotclient.log import logger_cli


class dotaReporter(ABC):
    """Base class for reporting data from the API client."""
    payload: dict = {}
    time_fmt: str = "%Y-%m-%dT%H:%M:%S.%fZ"

    def __init__(self, args) -> None:
        # TODO: Add jinja2 support to render report as HTML or Markdown
        self.output = args.output
        self.yaml = ruamel.yaml.YAML()
        self.yaml.preserve_quotes = True
        self.yaml.explicit_start = True
        self.trottle = args.trottle

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

    def save_payload(self, payload: dict) -> None:
        # TODO: Add option to save as JSON or YAML
        self.yaml.dump(self.payload, self.output)


class topTeamsReport(dotaReporter):
    """Report for top teams by combined player experience."""
    def __init__(self, args, api_client: dota2cl) -> None:
        super().__init__(args)
        self.teams_count = args.num_teams
        self.preload_teams = args.preload_teams
        self.api_client = api_client

    def generate_payload(self) -> None:
        """Creates a report of the top teams by combined player experience."""
        if self.preload_teams:
            teams_data = {t["team_id"]: t for t in self.api_client.get_teams()}
        else:
            teams_data = {}

        players = self.api_client.get_pro_players()
        # Calculate experience for each player
        # and create teams with their players

        # it looks messy, but it is more efficient to do it in one pass
        # instead of multiple passes over the data
        teams = {}
        for player in players:
            if player.get("full_history_time") is None:
                continue

            _history_start = datetime.strptime(
                player.get("full_history_time"),
                self.time_fmt)
            _experience = (datetime.now() - _history_start).total_seconds()
            player["experience"] = _experience

            team_id = player.get("team_id")
            if team_id is not None:
                if team_id == 0:
                    # There is a discrepancy in the API where some players
                    # have team_id == 0, but there is no team with ID 0.
                    # Try to look up the team by name instead.
                    if self.preload_teams:
                        # I've chosen to use team name
                        # It could be possible to use team_tag too
                        # TODO: move this to portable method with targeted key support. # noqa E501
                        team_name = player.get("team_name")
                        if team_name is not None:
                            filtered_teams = [t for t in teams_data.values()
                                              if t.get("name") == team_name]
                            _filtered_size = len(filtered_teams)
                            if _filtered_size > 1:
                                # Additional logic of data matching could be
                                # implemented here to try to find the correct
                                # team, but for now just log a warning and
                                # skip the player
                                logger_cli.warning(
                                    "Multiple teams found with "
                                    f"name '{team_name}' for player "
                                    f"'{player.get('personaname')}'")
                                continue
                            elif _filtered_size == 0:
                                # No such team found,
                                # log a warning and skip the player
                                logger_cli.warning(
                                    f"No team found with name '{team_name}' "
                                    f"for player '{player.get('personaname')}'")  # noqa: E501
                                player["team_id"] = None
                                continue
                            else:
                                # The only proper output is when count is 1
                                new_team_id = filtered_teams[0].get("team_id")
                                logger_cli.debug(
                                    f"Found team ID {new_team_id} for "
                                    f"player '{player.get('personaname')}' "
                                    f"with team name '{team_name}'")
                                player["team_id"] = new_team_id
                                team_id = new_team_id
                        else:
                            # Corrupted data, team_id is 0 and no team_name
                            logger_cli.warning(
                                f"Player '{player.get('personaname')}' "
                                "has team_id 0 and no team_name")
                            player["team_id"] = None
                            continue
                    else:
                        # No name lookup possible as it will generate
                        # a lot of requests, just log a warning
                        # and skip the player
                        logger_cli.warning(
                            f"Player '{player.get('personaname')}' "
                            "has team_id 0 and teams data is not preloaded")
                        player["team_id"] = None
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
                teams_data[team_id] = self.api_client.get_team_by_id(team_id)
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
