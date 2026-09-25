import json

import pandas as pd

from quant_backtester.cli import main


def test_cli_backtest_writes_equity_trades_and_metrics(tmp_path) -> None:
    prices = pd.DataFrame(
        {
            "Open": [100.0, 100.0, 100.0, 100.0],
            "High": [101.0, 101.0, 101.0, 101.0],
            "Low": [99.0, 99.0, 99.0, 99.0],
            "Close": [100.0, 100.0, 100.0, 100.0],
            "Volume": [1000.0] * 4,
        },
        index=pd.date_range("2024-01-01", periods=4),
    )
    input_path = tmp_path / "prices.csv"
    output_path = tmp_path / "report"
    prices.to_csv(input_path)

    main(
        [
            "backtest",
            str(input_path),
            "--symbol",
            "TEST",
            "--output-directory",
            str(output_path),
        ]
    )

    assert (output_path / "equity_curve.csv").exists()
    assert (output_path / "trades.csv").exists()
    assert (output_path / "rejections.csv").exists()
    report = json.loads((output_path / "metrics.json").read_text())
    assert report["final_equity"] == 10000.0