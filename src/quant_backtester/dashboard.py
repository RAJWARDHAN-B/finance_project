"""Local interactive dashboard for historical strategy research."""

from __future__ import annotations

from datetime import date, timedelta
from pathlib import Path

import pandas as pd

from quant_backtester.backtest import run_backtest
from quant_backtester.data import download_history, load_csv, validate_ohlcv
from quant_backtester.performance import drawdown_series, performance_report
from quant_backtester.returns import buy_and_hold
from quant_backtester.strategy import MeanReversionStrategy


def main() -> None:
    import streamlit as st

    st.set_page_config(page_title="Quant Terminal", page_icon="Q", layout="wide")
    st.markdown(
        """
        <style>
        :root { color-scheme: dark; }
        .stApp { background: #101416; color: #e4e9e6; }
        [data-testid="stSidebar"] { background: #171d1f; border-right: 1px solid #354044; }
        h1, h2, h3 { color: #e4e9e6; letter-spacing: 0; }
        .terminal-kicker { color: #91a39d; font: 12px monospace; text-transform: uppercase; }
        .terminal-title { color: #c8f169; font: 700 30px monospace; margin: 0 0 6px 0; }
        .terminal-rule { border-bottom: 1px solid #354044; margin: 10px 0 20px 0; }
        [data-testid="stMetric"] { background: #171d1f; border: 1px solid #354044; padding: 12px; }
        [data-testid="stMetricValue"] { color: #c8f169; font-family: monospace; font-size: 20px; white-space: nowrap; }
        [data-testid="stMetricLabel"] { font-size: 13px; }
        [data-testid="stAlert"] { background: #171d1f; border: 1px solid #354044; color: #e4e9e6; }
        .stButton > button { background: #c8f169; border: 1px solid #c8f169; color: #101416; font-weight: 700; }
        .stButton > button:hover { background: #d9ff8a; border-color: #d9ff8a; color: #101416; }
        button[role="tab"][aria-selected="true"] { color: #c8f169; border-bottom-color: #c8f169; }
        .stTabs [data-baseweb="tab-highlight"] { background-color: #c8f169; }
        div[data-testid="stDataFrame"] { border: 1px solid #354044; }
        </style>
        <div class="terminal-kicker">Quant Research / Historical Simulation</div>
        <div class="terminal-title">MARKET LAB</div>
        <div class="terminal-rule"></div>
        """,
        unsafe_allow_html=True,
    )

    with st.sidebar:
        st.subheader("Run configuration")
        source = st.radio("Market data", ["Local CSV", "Upload CSV", "Yahoo Finance"])
        symbol = st.text_input("Symbol", value="SPY").strip().upper()
        uploaded = None
        local_path = None
        start = None
        end = None
        if source == "Local CSV":
            available_files = sorted(Path("data").glob("*.csv"))
            if available_files:
                local_path = st.selectbox("Dataset", available_files, format_func=lambda path: path.name)
            else:
                st.caption("No local CSV files found in data/.")
        elif source == "Upload CSV":
            uploaded = st.file_uploader("OHLCV CSV", type=["csv"])
        else:
            start = st.date_input("Start date", value=date.today() - timedelta(days=365 * 5))
            end = st.date_input("End date", value=date.today())

        lookback = st.number_input("Lookback bars", min_value=2, max_value=500, value=20)
        threshold = st.number_input("Entry z-score", min_value=0.1, max_value=5.0, value=1.5, step=0.1)
        initial_cash = st.number_input("Initial cash", min_value=1.0, value=10000.0, step=1000.0)
        commission = st.number_input("Commission per fill", min_value=0.0, value=0.0, step=0.5)
        slippage_bps = st.number_input("Slippage (bps)", min_value=0.0, value=5.0, step=1.0)
        max_position_size = st.number_input("Max shares (0 = uncapped)", min_value=0, value=0)
        run_clicked = st.button("Run backtest", type="primary", use_container_width=True)

    if run_clicked:
        try:
            if source == "Local CSV":
                if local_path is None:
                    raise ValueError("Add a CSV under data/ or choose another data source")
                prices = load_csv(local_path)
            elif source == "Upload CSV":
                if uploaded is None:
                    raise ValueError("Choose a CSV file to upload")
                prices = validate_ohlcv(pd.read_csv(uploaded, index_col=0, parse_dates=True))
            else:
                if start is None or end is None or start >= end:
                    raise ValueError("The end date must be later than the start date")
                prices = download_history(symbol, start.isoformat(), end.isoformat())

            result = run_backtest(
                prices,
                symbol=symbol,
                strategy=MeanReversionStrategy(lookback=int(lookback), z_threshold=float(threshold)),
                initial_cash=float(initial_cash),
                commission=float(commission),
                slippage_bps=float(slippage_bps),
                max_position_size=int(max_position_size) or None,
            )
            st.session_state["backtest_result"] = result
            st.session_state["backtest_prices"] = prices
            st.session_state["backtest_symbol"] = symbol
            st.session_state["backtest_metrics"] = performance_report(result.equity_curve, result.trades)
        except (ValueError, OSError) as error:
            st.error(str(error))

    result = st.session_state.get("backtest_result")
    if result is None:
        st.info("Load historical OHLCV data, set execution assumptions, and run a backtest.")
        return

    prices = st.session_state["backtest_prices"]
    metrics = st.session_state["backtest_metrics"]
    symbol = st.session_state["backtest_symbol"]
    st.caption(
        f"{symbol}  |  {prices.index[0].date()} to {prices.index[-1].date()}  |  "
        f"{len(prices):,} daily bars  |  next-open fills"
    )

    metric_columns = st.columns(5)
    metric_columns[0].metric("Final equity", f"${metrics['final_equity']:,.2f}")
    metric_columns[1].metric("Total return", f"{metrics['total_return']:.2%}")
    metric_columns[2].metric("Sharpe", "N/A" if metrics["sharpe_ratio"] is None else f"{metrics['sharpe_ratio']:.2f}")
    metric_columns[3].metric("Max DD", f"{metrics['max_drawdown']:.2%}")
    metric_columns[4].metric("Closed trades", str(metrics["trade_count"]))

    baseline = buy_and_hold(prices, initial_capital=float(metrics["start_equity"]))
    chart_data = pd.DataFrame(
        {
            "Strategy": result.equity_curve["equity"],
            "Buy and hold": baseline["equity"].reindex(result.equity_curve.index),
        }
    )
    chart_tab, risk_tab, trades_tab, metrics_tab = st.tabs(
        ["Equity", "Risk", "Trades", "Metrics"]
    )
    with chart_tab:
        st.line_chart(chart_data, color=["#c8f169", "#5ec8d4"], height=360)
    with risk_tab:
        st.area_chart(drawdown_series(result.equity_curve), color="#e7a84b", height=300)
        st.caption(f"Maximum underwater duration: {metrics['max_drawdown_duration']} bars")
    with trades_tab:
        st.subheader("Filled trades")
        st.dataframe(result.trades, use_container_width=True, hide_index=True)
        st.subheader("Unfilled quantities")
        st.dataframe(result.rejections, use_container_width=True, hide_index=True)
        st.download_button(
            "Download trade ledger",
            result.trades.to_csv(index=False),
            file_name=f"{symbol.lower()}_trades.csv",
            mime="text/csv",
        )
    with metrics_tab:
        st.dataframe(
            pd.DataFrame([metrics]).T.rename(columns={0: "Value"}),
            use_container_width=True,
        )


if __name__ == "__main__":
    main()