"""Command-line workflows for data ingestion and reproducible backtests."""

from __future__ import annotations

import argparse
import json
from pathlib import Path
from typing import Sequence

from quant_backtester.backtest import run_backtest
from quant_backtester.data import download_history, load_csv
from quant_backtester.performance import performance_report
from quant_backtester.strategy import MeanReversionStrategy


def _parser() -> argparse.ArgumentParser:
    parser = argparse.ArgumentParser(prog="quant-backtester")
    commands = parser.add_subparsers(dest="command", required=True)

    download = commands.add_parser("download", help="download and validate daily OHLCV data")
    download.add_argument("ticker")
    download.add_argument("--start", required=True)
    download.add_argument("--end")
    download.add_argument("--output", required=True)

    backtest = commands.add_parser("backtest", help="run a strategy against an OHLCV CSV")
    backtest.add_argument("csv_path")
    backtest.add_argument("--symbol", required=True)
    backtest.add_argument("--initial-cash", type=float, default=10000.0)
    backtest.add_argument("--commission", type=float, default=0.0)
    backtest.add_argument("--slippage-bps", type=float, default=0.0)
    backtest.add_argument("--max-position-size", type=int)
    backtest.add_argument("--lookback", type=int, default=20)
    backtest.add_argument("--z-threshold", type=float, default=1.5)
    backtest.add_argument("--output-directory", default="reports/latest")
    return parser


def main(argv: Sequence[str] | None = None) -> None:
    arguments = _parser().parse_args(argv)
    if arguments.command == "download":
        data = download_history(
            ticker=arguments.ticker,
            start=arguments.start,
            end=arguments.end,
            output_path=arguments.output,
        )
        print(f"Saved {len(data)} daily bars to {arguments.output}")
        return

    prices = load_csv(arguments.csv_path)
    result = run_backtest(
        prices,
        symbol=arguments.symbol,
        strategy=MeanReversionStrategy(
            lookback=arguments.lookback,
            z_threshold=arguments.z_threshold,
        ),
        initial_cash=arguments.initial_cash,
        commission=arguments.commission,
        slippage_bps=arguments.slippage_bps,
        max_position_size=arguments.max_position_size,
    )
    metrics = performance_report(result.equity_curve, result.trades)
    output_directory = Path(arguments.output_directory)
    output_directory.mkdir(parents=True, exist_ok=True)
    result.equity_curve.to_csv(output_directory / "equity_curve.csv")
    result.trades.to_csv(output_directory / "trades.csv", index=False)
    result.rejections.to_csv(output_directory / "rejections.csv", index=False)
    (output_directory / "metrics.json").write_text(json.dumps(metrics, indent=2))
    print(json.dumps(metrics, indent=2))


if __name__ == "__main__":
    main()
