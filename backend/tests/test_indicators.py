from app.indicators import avg_dollar_volume, pct_from_52w_high, relative_strength, sma


def test_sma_basic():
    assert sma([1, 2, 3, 4, 5], 3) == 4.0


def test_sma_not_enough_data_returns_none():
    assert sma([1, 2], 5) is None


def test_pct_from_52w_high_at_high():
    assert pct_from_52w_high([10, 20, 30]) == 0.0


def test_pct_from_52w_high_below_high():
    result = pct_from_52w_high([10, 20, 30, 27])
    assert round(result, 2) == -10.0


def test_relative_strength_outperforms():
    stock = [100, 110]  # +10%
    benchmark = [100, 105]  # +5%
    result = relative_strength(stock, benchmark)
    assert round(result, 2) == 5.0


def test_relative_strength_insufficient_data_returns_none():
    assert relative_strength([100], [100, 105]) is None


def test_avg_dollar_volume():
    closes = [10, 20]
    volumes = [100, 200]
    # (20*200 + 10*100) / 2 = (4000 + 1000) / 2 = 2500
    assert avg_dollar_volume(closes, volumes) == 2500.0
