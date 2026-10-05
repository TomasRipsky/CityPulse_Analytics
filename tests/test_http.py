import httpx
import pytest

from citypulse.http import Http, NotPublishedError, backoff_delay

URL = "https://example.test/data"


def make_http(handler, sleeps=None, max_attempts=5):
    client = httpx.Client(transport=httpx.MockTransport(handler))
    sleep = sleeps.append if sleeps is not None else (lambda seconds: None)
    return Http(client, max_attempts=max_attempts, sleep=sleep)


def sequence(*responses):
    """A handler answering with each response in turn (callables raise or build one)."""
    calls = iter(responses)

    def handler(request):
        response = next(calls)
        return response(request) if callable(response) else response

    return handler


def test_get_json_retries_a_server_error_once():
    http = make_http(sequence(httpx.Response(503), httpx.Response(200, json={"ok": 1})))
    assert http.get_json(URL, {"a": 1}) == {"ok": 1}


def test_get_json_honours_retry_after():
    sleeps = []
    http = make_http(
        sequence(httpx.Response(429, headers={"Retry-After": "7"}), httpx.Response(200, json={})),
        sleeps,
    )
    http.get_json(URL, {})
    assert sleeps == [7.0]


def test_get_json_gives_up_after_max_attempts():
    http = make_http(lambda request: httpx.Response(500), max_attempts=3)
    with pytest.raises(httpx.HTTPStatusError):
        http.get_json(URL, {})


def test_get_json_retries_transport_errors():
    def boom(request):
        raise httpx.ConnectError("down", request=request)

    http = make_http(sequence(boom, httpx.Response(200, json={"ok": 2})))
    assert http.get_json(URL, {}) == {"ok": 2}


def test_get_json_does_not_retry_a_client_error():
    calls = []

    def handler(request):
        calls.append(request)
        return httpx.Response(400, json={"reason": "bad parameter"})

    with pytest.raises(httpx.HTTPStatusError):
        make_http(handler).get_json(URL, {})
    assert len(calls) == 1


@pytest.mark.parametrize("status", [403, 404])
def test_download_of_a_missing_file_is_not_published(tmp_path, status):
    http = make_http(lambda request: httpx.Response(status))
    with pytest.raises(NotPublishedError):
        http.download(URL, tmp_path / "f.zip")
    assert not (tmp_path / "f.zip").exists()


def test_download_reports_what_the_server_said(tmp_path):
    headers = {"ETag": '"abc123"', "Last-Modified": "Wed, 12 Feb 2025 10:00:00 GMT"}
    http = make_http(lambda request: httpx.Response(200, headers=headers, content=b"zip"))
    info = http.download(URL, tmp_path / "f.zip")
    assert (info.size, info.etag, info.last_modified) == (
        3,
        '"abc123"',
        "Wed, 12 Feb 2025 10:00:00 GMT",
    )


def test_download_retries_a_truncated_body(tmp_path):
    short = httpx.Response(200, headers={"Content-Length": "10"}, content=b"12345")
    full = httpx.Response(200, content=b"1234567890")
    http = make_http(sequence(lambda r: short, full))
    assert http.download(URL, tmp_path / "f.zip").size == 10
    assert (tmp_path / "f.zip").read_bytes() == b"1234567890"


def test_download_never_leaves_a_partial_file(tmp_path):
    def short(request):
        return httpx.Response(200, headers={"Content-Length": "10"}, content=b"12345")

    http = make_http(short, max_attempts=2)
    with pytest.raises(OSError):
        http.download(URL, tmp_path / "f.zip")
    assert list(tmp_path.iterdir()) == []  # neither the file nor its .part


def test_backoff_delay():
    assert backoff_delay(1, "3", rng=lambda: 0.0) == 3.0
    assert backoff_delay(2, None, rng=lambda: 0.5) == 4.5
    assert backoff_delay(1, "-1", rng=lambda: 0.0) == 2.0  # negative Retry-After is ignored
    assert backoff_delay(10, None, rng=lambda: 0.0) == 60.0  # capped
