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

    def test_query_string_preserved(self):
        assert transform_text("https://x.com/i/web?foo=bar&baz=1") == (
            "https://fixupx.com/i/web?foo=bar&baz=1"
        )

    def test_query_without_path(self):
        assert transform_text("https://x.com?ref=home") == "https://fixupx.com?ref=home"

    def test_fragment_preserved(self):
        assert transform_text("https://x.com/page#section") == (
            "https://fixupx.com/page#section"
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


class TestMultipleLinks:
    def test_two_links(self):
        src = "first https://x.com/a then https://www.x.com/b end"
        assert transform_text(src) == (
            "first https://fixupx.com/a then https://www.fixupx.com/b end"
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
