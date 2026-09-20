import json
from types import SimpleNamespace
from unittest.mock import Mock, patch

from crawler.pipelines.backend_sink import BackendSinkPipeline


def test_backend_sink_normalizes_optional_fields_and_authenticates():
    pipeline = BackendSinkPipeline("http://127.0.0.1:8000", "secret", True)
    response = Mock()
    response.__enter__ = Mock(return_value=SimpleNamespace(status=200))
    response.__exit__ = Mock(return_value=False)
    with patch("crawler.pipelines.backend_sink.urllib.request.urlopen", return_value=response) as send:
        item = pipeline.process_item({
            "title": "政策通知",
            "source_url": "https://example.test/1",
            "pub_date": None,
            "category": "gov_general",
        }, Mock())
    assert item["title"] == "政策通知"
    request = send.call_args.args[0]
    payload = json.loads(request.data)
    assert payload["pub_date"] == ""
    assert payload["doc_number"] == ""
    assert payload["subsidy"] is False
    assert request.headers["X-token"] == "secret"


def test_backend_sink_disables_after_first_connection_failure():
    pipeline = BackendSinkPipeline("http://127.0.0.1:1", "secret", True)
    with patch("crawler.pipelines.backend_sink.urllib.request.urlopen", side_effect=OSError("down")) as send:
        pipeline.process_item({"title": "a"}, Mock())
        pipeline.process_item({"title": "b"}, Mock())
    assert send.call_count == 1
    assert pipeline.failed
