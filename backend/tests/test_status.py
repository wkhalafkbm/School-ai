from app.status import StatusCode, status_meta


def test_status_code_on_track_is_string_value():
    assert StatusCode.on_track == "on_track"


def test_all_five_status_codes_exist_as_string_values():
    expected = {"on_track", "watch", "needs_attention", "urgent", "opportunity"}
    assert {code.value for code in StatusCode} == expected


def test_status_meta_on_track_has_required_fields():
    entry = status_meta[StatusCode.on_track]
    assert "label" in entry
    assert "color_key" in entry
    assert "severity_rank" in entry


def test_status_meta_covers_all_codes_with_required_fields():
    for code in StatusCode:
        entry = status_meta[code]
        assert isinstance(entry["label"], str) and entry["label"]
        assert isinstance(entry["color_key"], str) and entry["color_key"]
        assert isinstance(entry["severity_rank"], int)


def test_urgent_has_highest_severity_rank():
    ranks = {code: status_meta[code]["severity_rank"] for code in StatusCode}
    assert ranks[StatusCode.urgent] > ranks[StatusCode.needs_attention]
    assert ranks[StatusCode.needs_attention] > ranks[StatusCode.watch]
    assert ranks[StatusCode.watch] > ranks[StatusCode.on_track]
