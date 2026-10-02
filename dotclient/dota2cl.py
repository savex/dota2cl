#    Author: Alex Savatieiev (a.savex@gmail.com)
#    November 2025
import requests
import time
import urllib.parse as urlparse

from datetime import datetime
from requests.exceptions import RequestException

from dotclient.const import api_client_throttle_timeout_sec, \
    resource_cache_timeout_sec, opendota_api_base_url, \
    requests_timeout_sec, api_client_max_retries, \
    api_client_retry_backoff_sec
from dotclient.exceptions import ApiRequestError, InvalidEndpointError, \
    InvalidResponseError, NotFoundError, RateLimitError, SchemaLoadError
from dotclient.log import logger_cli, logger
from dotclient.utils import secrets_filter


class apiClient:
    """
    Simple API client that loads schema from root endpoint and validates
    endpoints before making requests. It also handles throttle of requests.
    """
    def __init__(self, base_url: str, api_key: str | None = None,
                 throttle: bool = False,
                 timeout_sec: float = requests_timeout_sec,
                 throttle_timeout_sec: float =
                 api_client_throttle_timeout_sec,
                 max_retries: int = api_client_max_retries,
                 retry_backoff_sec: float = api_client_retry_backoff_sec,
                 cache_timeout_sec: float = resource_cache_timeout_sec):
        self.api_key = api_key
        # add key to filter to avoid logging it in clear text
        if api_key is not None:
            secrets_filter.add_secret(api_key)
        self.is_anonymous = api_key is None
        self.base_url = base_url
        # Set before loading the schema, as it makes a request
        self.timeout_sec = timeout_sec
        logger_cli.debug("...initializing API client "
                         f"with base URL: {self.base_url}")
        try:
            self.schema = self.load_schema()
        except SchemaLoadError as e:
            logger_cli.warning(f"{e}. "
                               "Validation of endpoints will be skipped.")
            self.schema = {}
        self.rest_handle_validation = bool(self.schema)

        self.throttle_requests = throttle
        self.throttle_timeout_sec = throttle_timeout_sec
        # time.monotonic() of the last request, None until one is made,
        # so the first request is not delayed
        self.last_request_time: float | None = None
        self.cache_request_timeout_sec = cache_timeout_sec
        self.max_retries = max_retries
        self.retry_backoff_sec = retry_backoff_sec
        # Cached responses keyed by handle
        self._cache: dict[str, dict] = {}

    def load_schema(self) -> dict:
        """
        Load API schema from the root endpoint.
        Raises SchemaLoadError if it can't be fetched or parsed.
        """
        try:
            resp = requests.get(self.base_url, timeout=self.timeout_sec)
            resp.raise_for_status()
            schema = resp.json()
        except ValueError as e:
            raise SchemaLoadError(
                f"Invalid JSON received for API schema: {e}") from e
        except RequestException as e:
            raise SchemaLoadError("Failed to load API schema "
                                  f"from {self.base_url}: {e}") from e
        if not isinstance(schema, dict):
            raise SchemaLoadError("API schema is not a JSON object")
        return schema

    def _check_request_time(self, timestamp: float) -> bool:
        """
        Check if the cached item is older than the cache timeout.
        """
        return datetime.now().timestamp() - timestamp > \
            self.cache_request_timeout_sec

    def _get_cached_item(self, handle: str, page_size: int = 0,
                         id_name: str | None = None) -> dict:
        """
        Get cached item by handle.
        """
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
                    if not isinstance(next_page, list):
                        raise InvalidResponseError(
                            f"Expected a list for page {page} of '{handle}', "
                            f"got {type(next_page).__name__}")
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

        item = self._cache.get(handle)
        if item is None:
            logger.debug(f"No cache found for {handle}. Fetching new data.")
        elif self._check_request_time(item["timestamp"]):
            logger.debug(f"Cache expired for {handle}. Fetching new data.")
        else:
            logger.debug(f"Using cached data for {handle}")
            return item["data"]

        item = {
            "handle": handle,
            "timestamp": datetime.now().timestamp(),
            "data": get_data()
        }
        self._cache[handle] = item
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
        Raises InvalidEndpointError if the endpoint is not in the schema,
        ApiRequestError (or its subclasses) if the request fails and
        InvalidResponseError if the response body is not valid JSON.
        """
        if self.rest_handle_validation and \
                not self.validate_endpoint(endpoint, id_name=id_name):
            raise InvalidEndpointError(f"Endpoint '{endpoint}' is not valid.")

        # Prepare params dict with API key if not anonymous
        if params is None:
            params = {}
        if not self.is_anonymous:
            params["key"] = self.api_key

        url = urlparse.urljoin(self.base_url + "/", endpoint)
        response = self._request_with_retries(url, params, endpoint)

        if len(response.content) == 0:
            return {}
        try:
            return response.json()
        except ValueError:
            raise InvalidResponseError(
                f"Invalid JSON received from '{endpoint}'") from None

    def _throttle(self) -> None:
        """
        Wait until throttle timeout has passed since the last request.
        """
        if not self.throttle_requests or self.last_request_time is None:
            return
        # Monotonic clock is not affected by system time changes
        time_since_last_request = time.monotonic() - self.last_request_time
        if time_since_last_request < self.throttle_timeout_sec:
            wait_time = self.throttle_timeout_sec - time_since_last_request
            logger_cli.debug("...throttle request. "
                             f"Waiting for {wait_time:.2f} seconds.")
            time.sleep(wait_time)

    @staticmethod
    def _get_retry_after(response) -> float | None:
        """
        Get 'Retry-After' header value in seconds, if it is a number.
        """
        _value = getattr(response, "headers", {}).get("Retry-After")
        try:
            return float(_value) if _value is not None else None
        except ValueError:
            # HTTP date format is not supported, use backoff instead
            return None

    def _request_with_retries(self, url: str, params: dict,
                              endpoint: str):
        """
        Send GET request, retrying on 429 Too Many Requests.
        Errors are re-raised without the original exception attached,
        as its message contains the full URL with the API key.
        """
        for attempt in range(self.max_retries + 1):
            self._throttle()
            logger.debug(f"Requesting {endpoint} with params: {params}")
            try:
                response = requests.get(url, params=params,
                                        timeout=self.timeout_sec)
            except RequestException as e:
                raise ApiRequestError(
                    f"Request to '{endpoint}' failed: {type(e).__name__}",
                    endpoint=endpoint) from None
            finally:
                self.last_request_time = time.monotonic()

            status = response.status_code
            if status == 429:
                retry_after = self._get_retry_after(response)
                if attempt >= self.max_retries:
                    raise RateLimitError(
                        f"Rate limit exceeded for '{endpoint}' "
                        f"after {self.max_retries} retries",
                        endpoint=endpoint, retry_after=retry_after)
                wait_time = retry_after if retry_after is not None \
                    else self.retry_backoff_sec * 2 ** attempt
                logger_cli.warning(f"Rate limited on '{endpoint}', "
                                   f"retrying in {wait_time:.0f} seconds "
                                   f"({attempt + 1}/{self.max_retries})")
                time.sleep(wait_time)
                continue
            if status == 404:
                raise NotFoundError(f"Resource '{endpoint}' not found",
                                    endpoint=endpoint)
            if status >= 400:
                raise ApiRequestError(
                    f"Request to '{endpoint}' failed with HTTP {status}",
                    endpoint=endpoint, status_code=status)
            return response


class dota2cl(apiClient):
    def __init__(self, api_key: str | None = None, throttle: bool = False,
                 base_url: str = opendota_api_base_url, **options):
        # options are the apiClient timeout, retry and cache settings
        super().__init__(base_url, api_key, throttle=throttle, **options)

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
