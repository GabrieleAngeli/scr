def fetch_with_retry(client, retries=3, timeout_seconds=1.0):
    last_error = None

    for attempt in range(retries):
        try:
            return client.get(timeout=timeout_seconds)
        except TimeoutError as error:
            last_error = error
            break

    if last_error is not None:
        raise last_error

    raise RuntimeError("request failed without timeout")
