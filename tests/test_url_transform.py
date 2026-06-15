"""Unit tests for the URL transformation logic."""

import pytest

from src.url_transform import count_matches, has_x_link, transform_text


class TestTransformBasic:
    def test_simple_https(self):
        assert transform_text("https://x.com/user/status/123") == (
            "https://fixupx.com/user/status/123"
        )

    def test_simple_http(self):
        assert transform_text("http://x.com/user/status/123") == (
            "http://fixupx.com/user/status/123"
        )

    def test_www(self):
        assert transform_text("https://www.x.com/user/status/123") == (
            "https://www.fixupx.com/user/status/123"
        )

    def test_www_http(self):
        assert transform_text("http://www.x.com/abc") == "http://www.fixupx.com/abc"

    def test_bare_host_no_path(self):
        assert transform_text("https://x.com") == "https://fixupx.com"

    def test_query_string_stripped(self):
        # The whole query string (tracking) is removed; only the path is kept.
        assert transform_text("https://x.com/i/web?foo=bar&baz=1") == (
            "https://fixupx.com/i/web"
        )

    def test_query_without_path_stripped(self):
        assert transform_text("https://x.com?ref=home") == "https://fixupx.com"

    def test_fragment_stripped(self):
        assert transform_text("https://x.com/page#section") == (
            "https://fixupx.com/page"
        )

    def test_port_preserved(self):
        assert transform_text("https://x.com:8443/path") == (
            "https://fixupx.com:8443/path"
        )

    def test_trailing_slash(self):
        assert transform_text("https://x.com/") == "https://fixupx.com/"


class TestCaseInsensitivity:
    @pytest.mark.parametrize(
        "src,expected",
        [
            ("https://X.com/Foo", "https://fixupx.com/Foo"),
            ("https://X.COM/Foo", "https://fixupx.com/Foo"),
            ("HTTPS://x.com/Foo", "HTTPS://fixupx.com/Foo"),
            ("https://WWW.X.com/Foo", "https://WWW.fixupx.com/Foo"),
        ],
    )
    def test_case(self, src, expected):
        # Host is rewritten to lowercase fixupx.com; path/scheme case preserved.
        assert transform_text(src) == expected


class TestTrackingStripped:
    """Real-world X share URLs: the query is pure tracking and must be removed."""

    @pytest.mark.parametrize(
        "src,expected",
        [
            # ?s=20 is the "share source" tracker appended by the X app.
            (
                "https://x.com/jack/status/20?s=20",
                "https://fixupx.com/jack/status/20",
            ),
            # ?t=… session token plus ?s=… source.
            (
                "https://x.com/user/status/123?t=AbCdEf123&s=19",
                "https://fixupx.com/user/status/123",
            ),
            # ?ref_src=twsrc%5Etfw referral tracking from embeds.
            (
                "https://www.x.com/user/status/9?ref_src=twsrc%5Etfw",
                "https://www.fixupx.com/user/status/9",
            ),
            # ?cxt=… expanded-context tracker.
            (
                "https://x.com/i/web/status/5?cxt=HHwWgsest",
                "https://fixupx.com/i/web/status/5",
            ),
            # Path with photo index is kept (it's content, not query).
            (
                "https://x.com/user/status/7/photo/1?s=20",
                "https://fixupx.com/user/status/7/photo/1",
            ),
        ],
    )
    def test_tracking_removed(self, src, expected):
        assert transform_text(src) == expected


class TestMultipleLinks:
    def test_two_links(self):
        src = "first https://x.com/a then https://www.x.com/b end"
        assert transform_text(src) == (
            "first https://fixupx.com/a then https://www.fixupx.com/b end"
        )

    def test_two_links_both_detracked(self):
        src = "https://x.com/a/status/1?s=20 and https://x.com/b/status/2?t=xyz"
        assert transform_text(src) == (
            "https://fixupx.com/a/status/1 and https://fixupx.com/b/status/2"
        )

    def test_three_links_mixed(self):
        src = "http://x.com/1 https://x.com/2 https://www.x.com/3"
        assert transform_text(src) == (
            "http://fixupx.com/1 https://fixupx.com/2 https://www.fixupx.com/3"
        )

    def test_count(self):
        assert count_matches("https://x.com/a https://x.com/b") == 2


class TestNoChange:
    @pytest.mark.parametrize(
        "src",
        [
            "",
            "just some text without links",
            "check out twitter.com/user",
            "https://example.com/x.com",  # x.com only in path, not host
            "https://max.com/foo",
            "https://xx.com/foo",
            "https://mybox.com/x",
            "https://fixupx.com/already/fixed",  # already fixed, leave alone
            "https://x.com.evil.com/phish",  # x.com is not the host
            "https://notx.com/foo",
            "https://prefixx.com/foo",
            "ftp://x.com/foo",  # unsupported scheme
            "x.com/foo",  # no scheme
        ],
    )
    def test_unchanged(self, src):
        assert transform_text(src) == src

    @pytest.mark.parametrize(
        "src",
        [
            "https://example.com/x.com",
            "https://x.com.evil.com/phish",
            "ftp://x.com/foo",
            "",
            None,
        ],
    )
    def test_no_match_count(self, src):
        assert count_matches(src) == 0
        assert has_x_link(src) is False


class TestEdgeCases:
    def test_none_input(self):
        assert transform_text(None) is None

    def test_empty_input(self):
        assert transform_text("") == ""

    def test_link_in_sentence_with_punctuation(self):
        # A space terminates the host, link is rewritten.
        assert transform_text("see https://x.com/p now") == "see https://fixupx.com/p now"

    def test_does_not_double_rewrite(self):
        once = transform_text("https://x.com/a")
        twice = transform_text(once)
        assert once == twice == "https://fixupx.com/a"

    def test_has_x_link_true(self):
        assert has_x_link("go to https://x.com/x") is True

    def test_newline_separated_links(self):
        src = "https://x.com/a\nhttps://www.x.com/b"
        assert transform_text(src) == "https://fixupx.com/a\nhttps://www.fixupx.com/b"

    def test_angle_bracket_wrapped(self):
        # Discord users sometimes wrap links in <> to suppress embeds.
        assert transform_text("<https://x.com/a>") == "<https://fixupx.com/a>"

    def test_angle_bracket_wrapped_with_tracking(self):
        # The angle bracket terminates the URL; the query is still stripped.
        assert transform_text("<https://x.com/a?s=20>") == "<https://fixupx.com/a>"

    def test_link_with_tracking_in_sentence(self):
        assert transform_text("look https://x.com/u/status/1?s=20 wow") == (
            "look https://fixupx.com/u/status/1 wow"
        )
