"""Tests for data source modules."""

from __future__ import annotations

import pytest

from coin_trader.data.notice_fetcher import NoticeFetcher
from coin_trader.data.protocols import DataSource


class TestNoticeFetcher:
    def test_extract_tickers(self):
        tickers = NoticeFetcher._extract_tickers(
            "신규 디지털 자산 거래지원 안내 (BTC)"
        )
        assert "KRW-BTC" in tickers

    def test_extract_multiple_tickers(self):
        tickers = NoticeFetcher._extract_tickers(
            "거래지원 안내 (BTC) 및 (ETH)"
        )
        assert "KRW-BTC" in tickers
        assert "KRW-ETH" in tickers

    def test_extract_no_tickers(self):
        tickers = NoticeFetcher._extract_tickers("일반 공지사항입니다")
        assert tickers == []

    def test_extract_single_ticker(self):
        tickers = NoticeFetcher._extract_tickers("유의종목 지정 안내 (DOGE)")
        assert tickers == ["KRW-DOGE"]

    def test_custom_keywords(self):
        fetcher = NoticeFetcher(keywords=["custom"])
        assert "custom" in fetcher.keywords

    def test_name(self):
        fetcher = NoticeFetcher()
        assert fetcher.name == "notice_fetcher"


class TestDataSourceProtocol:
    def test_protocol_is_abstract(self):
        with pytest.raises(TypeError):
            DataSource()  # type: ignore[abstract]
