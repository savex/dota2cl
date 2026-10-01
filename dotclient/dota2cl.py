#    Author: Alex Savatieiev (a.savex@gmail.com)
#    November 2025
import requests
import time
import urllib.parse as urlparse

from datetime import datetime
from requests.exceptions import RequestException

from dotclient.const import api_client_trottle_timeout_sec, \
    resource_cache_timeout_sec, opendota_api_base_url, \
    requests_timeout_sec
from dotclient.log import logger_cli, logger


class apiClient:
    """
    Simple API client that loads schema from root endpoint and validates
    endpoints before making requests. It also handles trottle of requests.
    """
    def __init__(self, base_url: str, api_key: str | None = None,
                 trottle: bool = False):
        self.api_key = api_key
        self.is_anonymous = api_key is None
        self.base_url = base_url
        logger_cli.debug("...initializing API client "
                         f"with base URL: {self.base_url}")
        self.schema = self.load_schema()
        if not self.schema:
            logger_cli.warning("Failed to load API schema. "
                               "Validation of endpoints will be skipped.")
            self.rest_handle_validation = False
        else:
            self.rest_handle_validation = True

        # TODO: load options from config file, e.g. trottle_requests, trottle_timeout_sec  # noqa: E501
        self.trottle_requests = trottle
        self.trottle_timeout_sec = api_client_trottle_timeout_sec
        self.last_request_time = datetime.now()
        self.cache_request_timeout_sec = resource_cache_timeout_sec

    def load_schema(self) -> dict | None:
        # load schema with basic error handling
        try:
            resp = requests.get(self.base_url, timeout=requests_timeout_sec)
            resp.raise_for_status()
            return resp.json()
        except ValueError as e:
            logger_cli.error(f"Invalid JSON received for API schema: {e}")
            return {}
        except RequestException as e:
            logger_cli.error("Failed to load API schema "
                             f"from {self.base_url}: {e}")
            return {}

    def _check_request_time(self, timestamp: float) -> bool:
        """
        Check if the last request was made more than 1 hour ago.
        """
        return datetime.now().timestamp() - timestamp > \
            self.cache_request_timeout_sec

    def _get_cached_item(self, handle: str, page_size: int = 0,
                         id_name: str | None = None) -> dict:
        """
        Get cached item by handle.
        """
        def _update_cache(handle, data):
            setattr(self, handle, {
                "handle": handle,
                "timestamp": datetime.now().timestamp(),
                "data": data
            })

        def get_data():
            if page_size > 0:
                logger_cli.debug(f"...getting paginated data for {handle}, "
                                 f"page size: {page_size}")
                data = []
                page = 0
                while True:
                    next_page = self.get(handle, params={"page": page},
                                         id_name=id_name)
                    # On very rare occasions, item count might match
                    # page size exactly, so we need to check if the
                    # next page is empty to avoid infinite loop
                    if not next_page:
                        break
                    logger_cli.debug(f"Got {len(next_page)} items "
                                     f"for page {page}")
                    data += next_page
                    page += 1
                    # If the number of items returned is less than
                    # the page size, we have reached the end
                    if len(next_page) < page_size:
                        break
                return data
            else:
                return self.get(handle, id_name=id_name)

        try:
            item = getattr(self, handle)
        except AttributeError:
            logger.debug(f"No cache found for {handle}. Fetching new data.")
            _update_cache(handle, get_data())
            item = getattr(self, handle)

        if not self._check_request_time(item["timestamp"]):
            logger.debug(f"Using cached data for {handle}")
        else:
            logger.debug(f"Cache expired for {handle}. Fetching new data.")
            _update_cache(handle, get_data())

        return item["data"]

    def validate_endpoint(self, endpoint: str,
                          id_name: str | None = None) -> bool:
        """
        Validate if the endpoint exists in the API schema.
        """
        if id_name is not None:
            _idx = endpoint.find('/')
            if _idx == -1:
                logger_cli.error(f"Invalid endpoint '{endpoint}' for "
                                 f"id_name '{id_name}'")
                return False
            else:
                _handle = f"/{endpoint[:_idx]}/{{{id_name}}}"
        else:
            _handle = f"/{endpoint}"

        # Safe guard for when schema is not loaded properly
        if not self.rest_handle_validation or \
                not self.schema or \
                "paths" not in self.schema:
            return True
        else:
            return _handle in self.schema["paths"]

    def get(self, endpoint: str, params: dict | None = None,
            id_name: str | None = None) -> dict:
        """
        Make a GET request to the OPENDOTA API.
        """
        if self.rest_handle_validation and \
                not self.validate_endpoint(endpoint, id_name=id_name):
            return {"error": f"Endpoint '{endpoint}' is not valid."}

        # Prepare params dict with API key if not anonymous
        if params is None:
            params = {}
        if not self.is_anonymous:
            params["key"] = self.api_key

        url = urlparse.urljoin(self.base_url + "/", endpoint)

        # Handle trottle of requests
        if self.trottle_requests:
            time_since_last_request = \
                (datetime.now() - self.last_request_time).total_seconds()
            if time_since_last_request < self.trottle_timeout_sec:
                wait_time = self.trottle_timeout_sec - time_since_last_request
                logger_cli.debug("...trottle request. "
                                 f"Waiting for {wait_time:.2f} seconds.")
                time.sleep(wait_time)

        logger.debug(f"Requesting {endpoint} with params: {params}")
        response = requests.get(url, params=params,
                                timeout=requests_timeout_sec)
        self.last_request_time = datetime.now()

        response.raise_for_status()

        return response.json() if len(response.content) > 0 else {}


class dota2cl(apiClient):
    def __init__(self, api_key: str | None = None, trottle: bool = False):
        super().__init__(opendota_api_base_url, api_key,
                         trottle=trottle)
        self.cache_request_timeout_sec = 60  # 1 min

    def get_pro_players(self) -> dict:
        """
        Get pro players.
        """
        _handle = "proPlayers"
        logger_cli.info("-> getting pro players from API "
                        f"with handle '{_handle}'")
        return self._get_cached_item(_handle)

    def get_teams(self) -> dict:
        """
        Get teams.
        """
        _handle = "teams"
        logger_cli.info(f"-> getting teams from API with handle '{_handle}'")
        return self._get_cached_item(_handle, page_size=1000)

    def get_team_by_id(self, team_id: int) -> dict:
        """
        Get team by ID.
        """
        _handle = f"teams/{team_id}"
        logger_cli.info(f"-> getting team with ID {team_id} "
                        f"from API with handle '{_handle}'")
        return self._get_cached_item(_handle, id_name="team_id")
