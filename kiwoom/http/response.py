class Response:
    """
    Response wrapper for aiohttp.ClientResponse
    """

    def __init__(self, url: str, status: int, headers: dict, body: dict):
        """
        Simply wrap aiohttp.ClientResponse to escape from async context.

        Args:
            url (str): url of the response
            status (int): status code of the response
            headers (dict): headers of the response
            body (dict): body of the response
        """

        self.url = url
        self.status = status
        self.headers = headers
        self.body = body

    def json(self) -> dict:
        """
        Returns already parsed body.

        Returns:
            dict: body in json format
        """
        return self.body
