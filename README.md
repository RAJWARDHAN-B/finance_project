# Event-Driven Backtester

A beginner-friendly Python project for learning quantitative finance through software development.

The first milestone is an event-driven backtesting engine with a simple mean-reversion strategy. We will begin with historical daily data, then add realistic transaction costs, performance metrics, and tests before considering live data.

## Project Layout

```text
src/quant_backtester/  Application package
tests/                 Automated tests
data/                  Local market data (ignored by Git)
reports/               Generated charts and reports (ignored by Git)
```

## Setup

Create and activate the virtual environment:

```bash
python3 -m venv .venv
source .venv/bin/activate
python -m pip install --upgrade pip
python -m pip install -e '.[dev]'
```

Run the test suite:

```bash
python -m pytest
```

Run the placeholder command-line entry point:

```bash
python -m quant_backtester.cli
```

Download historical daily data from Yahoo Finance:

```python
from quant_backtester.data import download_history

prices = download_history(
  ticker="SPY",
  start="2020-01-01",
  end="2024-01-01",
  output_path="data/SPY.csv",
)
print(prices.head())
```

The loader validates the required `Open`, `High`, `Low`, `Close`, and `Volume` columns, sorts the timestamps, rejects missing or impossible prices, and optionally saves the cleaned data.

Calculate returns and create a buy-and-hold baseline:

```python
from quant_backtester.data import load_csv
from quant_backtester.returns import buy_and_hold

prices = load_csv("data/SPY.csv")
baseline = buy_and_hold(prices, initial_capital=10000)

print(baseline[["close", "equity"]].tail())
print("Final portfolio value:", baseline["equity"].iloc[-1])
```

The baseline assumes that the full investment is made at the first available closing price and held until the final date. It is deliberately simple: it does not model commissions, slippage, taxes, or timing decisions. Future strategies must beat this baseline after those costs, or they do not add value.

Run the first event-driven strategy backtest:

```python
from quant_backtester.backtest import run_backtest
from quant_backtester.strategy import MeanReversionStrategy

prices = load_csv("data/SPY.csv")
result = run_backtest(
  prices,
  symbol="SPY",
  strategy=MeanReversionStrategy(lookback=20, z_threshold=1.5),
  initial_cash=10000,
)

print(result.equity_curve.tail())
print(result.trades)
print("Final portfolio value:", result.final_equity)
```

Signals use the current close and orders execute at the next bar's open. The result contains an equity curve, a trade ledger, and the final portfolio state.

## Project Status

Implemented so far:

- Phase 0: project scaffolding, Python package setup, virtual environment, and testing flow
- Phase 1: OHLCV validation and ingestion
- Phase 2: simple returns, log returns, cumulative returns, and a buy-and-hold baseline
- Phase 3: event types and a queue-based event system for market, signal, order, and fill events
- Phase 4: portfolio accounting with cash, positions, and equity tracking
- Phase 5: a beginner mean-reversion strategy based on rolling z-scores
- Phase 5 integration: next-open event-driven backtest loop and equity curve

What is still pending:

- Add realistic execution costs, slippage, and position sizing
- Phase 6: realistic backtesting with costs and execution logic
- Phase 7+: performance analysis, research validation, and UI/dashboard work

## Phase-Wise Learning and Implementation Plan

The project is intentionally developed in phases. Each phase introduces a small amount of finance and software design, produces a working result, and adds tests before the next layer is started. Do not add machine learning, live trading, or tick data until the simpler daily-data system is trustworthy.

### Phase 0: Tools and Python Foundations — DONE

**Goal:** Become comfortable running and changing the project.

Learn:

- Python functions, classes, modules, and exceptions
- Virtual environments and package installation
- Git basics: commits, branches, and readable project history
- `pandas` DataFrames, indexes, filtering, and rolling calculations
- `pytest` tests and the arrange-act-assert pattern

Build:

- Activate `.venv` and run the existing tests.
- Read the package code and change the CLI message.
- Create a small DataFrame manually and calculate its percentage changes.

Completion check:

```bash
python -m pytest
python -m quant_backtester.cli
```

### Phase 1: Market Data and OHLCV — DONE

**Goal:** Understand what market data represents and make unreliable input safe to use.

Learn:

- Open, High, Low, Close, and Volume
- Trading days, timestamps, missing values, and duplicate rows
- Adjusted versus unadjusted prices
- Why data quality affects every backtest result

Build:

- Keep the `validate_ohlcv` function as the data contract.
- Add CSV loading and historical downloads.
- Add tests for missing columns, null values, duplicate timestamps, invalid prices, and negative volume.
- Download one symbol such as `SPY` and inspect the first and last rows.

Completion check:

- A valid CSV loads into a chronologically sorted DataFrame.
- Invalid input fails with a clear error.
- A sample file can be saved under `data/` and is ignored by Git.

### Phase 2: Returns and a Baseline — DONE

**Goal:** Learn how investment performance is measured before writing a trading strategy.

Learn:

- Simple return: $r_t = P_t / P_{t-1} - 1$
- Log return: $\log(P_t / P_{t-1})$
- Compounding and cumulative returns
- Buy-and-hold as a baseline

Build:

- Add a returns module that calculates daily and cumulative returns.
- Create a buy-and-hold result for the downloaded symbol.
- Plot the price and cumulative return.
- Test known input values by hand so the formulas are not accepted on intuition alone.

Completion check:

- The cumulative return agrees with the first and last prices.
- The baseline report states the start date, end date, initial capital, final value, and total return.

### Phase 3: Event-Driven Architecture — DONE

**Goal:** Understand how a trading system moves information through components.

Learn:

- Event-driven design and queues
- The difference between market data, signals, orders, and fills
- Why a strategy should not directly change cash or positions

Build these small domain objects:

- `MarketEvent`: a new OHLCV bar is available.
- `SignalEvent`: a strategy wants to increase, reduce, or close exposure.
- `OrderEvent`: the portfolio requests a quantity and direction.
- `FillEvent`: the simulated broker confirms an execution price and quantity.

Build a simple event loop:

1. Read one market bar.
2. Create a market event.
3. Let the strategy create a signal.
4. Convert the signal into an order.
5. Simulate a fill.
6. Update the portfolio.

Completion check:

- A test processes one bar in the expected event order.
- Components communicate through events rather than modifying one another's internal state.

### Phase 4: Portfolio, Orders, and Accounting — DONE

**Goal:** Make trades affect cash and positions correctly.

Learn:

- Long positions, quantities, notional value, and cash
- Market orders and execution price
- Mark-to-market portfolio value
- Basic accounting invariants

Build:

- A portfolio with initial cash, positions, cash balance, and total equity.
- Order creation from signals.
- A basic simulated broker that fills orders at the next bar's open.
- A trade ledger containing timestamp, symbol, side, quantity, price, and fees.

Test these invariants:

- Buying decreases cash.
- Selling increases cash.
- A position quantity changes by the fill quantity.
- Portfolio equity equals cash plus the market value of positions.
- A rejected order does not change the portfolio.

Completion check:

- A fixed sequence of bars and orders produces a hand-calculable final cash balance and position.

### Phase 5: First Strategy: Moving-Average Mean Reversion — DONE

**Goal:** Implement a simple, explainable strategy without accidentally using future information.

Learn:

- Simple moving averages
- Rolling windows and warm-up periods
- Mean reversion versus momentum
- Look-ahead bias and execution timing

Build:

- Calculate a rolling mean and rolling standard deviation.
- Generate a buy signal when price is sufficiently below its rolling mean.
- Generate an exit signal when price returns toward the mean.
- Start with one symbol and one position at a time.
- Generate the signal using the current bar but execute on the next bar.

Completion check:

- Signals are absent during the warm-up period.
- A test proves that changing a future price does not change an earlier signal.
- The strategy can be run through the event loop without directly changing the portfolio.

### Phase 6: Realistic Backtesting

**Goal:** Make the simulated results less optimistic.

Learn:

- Commission and spread costs
- Slippage and market impact
- Position sizing and exposure limits
- Why frequent trading can destroy a strategy's edge

Build:

- Commission per trade.
- Slippage in basis points.
- Maximum position size and available-cash checks.
- Rejected-order reasons.
- Complete trade and order logs.
- Configuration objects so assumptions are visible and reproducible.

Completion check:

- The same strategy produces a lower or equal final value after costs.
- Tests verify fee calculations, slippage direction, and position limits.

### Phase 7: Performance and Risk Metrics

**Goal:** Evaluate a strategy beyond whether the final balance increased.

Learn:

- Annualized return and volatility
- Sharpe ratio and its assumptions
- Maximum drawdown and recovery time
- Win rate, average win, average loss, and profit factor
- The difference between return and risk-adjusted return

Build:

- A performance report from the equity curve and trade ledger.
- Equity curve and drawdown charts in `reports/`.
- A comparison against buy-and-hold.
- Tests using small, known equity curves with expected metrics.

Completion check:

- Every report includes the data period, symbol, strategy settings, costs, and metrics.
- Results can be reproduced from the same input data and configuration.

### Phase 8: Research Discipline and Validation

**Goal:** Learn why a backtest can look impressive and still be wrong.

Learn:

- In-sample versus out-of-sample data
- Train, validation, and test periods
- Walk-forward evaluation
- Parameter overfitting and selection bias
- Survivorship bias and delisted securities

Build:

- A fixed chronological split into development and evaluation periods.
- Walk-forward backtesting without shuffling time series data.
- Parameter sensitivity tables for the moving-average window and entry threshold.
- A results table showing each run's assumptions.

Completion check:

- The final strategy is evaluated on data that was not used to choose its parameters.
- The README clearly reports both successful and unsuccessful experiments.

### Phase 9: Multiple Assets and Better Engineering

**Goal:** Extend the system while preserving correctness.

Learn:

- Portfolio diversification and asset allocation
- Correlation and concentration
- Configuration-driven applications
- Logging, type hints, and integration tests

Build:

- Multiple symbols with separate positions.
- Portfolio-level exposure and risk limits.
- A command-line command to run a configured backtest.
- Structured logging and error handling.
- Fast unit tests plus a small end-to-end test.

Completion check:

- One command creates a complete report from a configuration file.
- Existing single-asset behavior remains unchanged.

### Phase 10: Optional Advanced Extensions

Only begin these after Phases 0-9 are working and understood.

- Tick data and asynchronous broker APIs
- Limit order books and market microstructure
- Options pricing and volatility surfaces
- Risk metrics such as historical VaR and expected shortfall
- A web dashboard using Streamlit
- Machine-learning signals with strict time-series validation
- A separate C++ execution or limit-order-book project

These are separate learning tracks, not prerequisites for a credible first backtesting project. A reliable, explainable daily-data system is more valuable than a complicated system whose results cannot be trusted.

## Suggested Weekly Rhythm

For each phase:

1. Learn the finance concept in plain language.
2. Write down a small example with numbers.
3. Implement the smallest useful function.
4. Add tests before adding features.
5. Run one experiment and inspect the output.
6. Record assumptions, results, and questions in the README or a research note.

Do not move to the next phase merely because the code runs. Move when you can explain the calculation, identify its assumptions, and describe at least one way it could be wrong.

Here is a list of 14 high-impact portfolio projects divided across Quant Finance and Investment Banking.
Since your background spans AI Agents, Core ML, Computer Vision, and Software Development, these project concepts leverage those exact strengths to make your resume stand out to top-tier finance recruiters.
Part 1: Quant Finance Projects (Focus: Engineering, ML & High Performance)
 * Ultra-Low Latency C++ Limit Order Book Engine
   * Description: A C++ order matching engine using lock-free data structures (e.g., ring buffers) and memory alignment to parse mock ITCH market feeds, process buy/sell limit orders, and produce market execution fills in sub-microseconds.
 * Multi-Agent Algorithmic Trading Sandbox (Reinforcement Learning)
   * Description: A multi-agent RL framework (using Stable-Baselines3/Ray RLlib) where multiple AI trading agents continuously compete against each other in a simulated order-book environment to discover optimal order execution strategies (minimizing market impact).
 * Event-Driven Python Backtesting Framework with ML Alpha Models
   * Description: A modular Python engine built with pandas and NumPy to backtest custom trading strategies. Incorporates walk-forward cross-validation, realistic order slippage, transaction costs, and a XGBoost / Transformer signal to predict short-term price momentum.
 * Alternative Data Vision Pipeline for Stock Volatility Tracking (Computer Vision)
   * Description: A pipeline using satellite imagery (OpenCV/PyTorch) to calculate parking lot fullness (e.g., Walmart/Target) or container shipping congestion, converting vision outputs into numerical signals to predict quarterly revenue surprises.
 * LLM-Powered Multi-Agent Financial Sentiment & Signal System
   * Description: An autonomous AI Agent framework (built with LangChain or AutoGen) that streams real-time financial news, SEC 10-K filings, and Reddit feeds to run sentiment analysis, score risk parameters, and generate trade execution signals automatically.
 * Options Pricing & Volatility Surface Generator (C++ / Python)
   * Description: Implements standard options pricing models (Black-Scholes, Monte Carlo simulations, Binomial trees) in C++, wrapping them with a Python UI that plots 3D implied volatility surfaces using real option chain data.
 * Risk Metrics Engine (Value-at-Risk & Expected Shortfall)
   * Description: A Python/C++ risk dashboard that calculates Historical, Parametric, and Monte Carlo Value-at-Risk (VaR) along with Conditional VaR (CVAR) for multi-asset portfolios, incorporating stress-testing scenarios (e.g., 2008 crash, 2020 COVID shock).
Part 2: Investment Banking Projects (Focus: Financial Modeling, AI Automation & Valuation)
 * Autonomous AI Investment Banking Analyst Agent
   * Description: A multi-agent system that ingests an arbitrary public company ticker, scrapes recent earnings reports, performs financial statement extraction, builds a dynamic Discounted Cash Flow (DCF) model in Excel, and auto-generates an M&A pitch deck in PDF format.
 * Interactive Three-Statement Financial & DCF Valuation Engine
   * Description: A web application (built using Python/Streamlit or React/Node.js) that allows users to adjust operational inputs (revenue growth, margins, discount rates) to automatically link a company's Income Statement, Balance Sheet, and Cash Flow Statement to compute enterprise value.
 * LBO (Leveraged Buyout) Model & Sensitivity Calculator
   * Description: An interactive financial tool designed to model a private equity transaction, calculating debt schedules, exit multiples, and IRR (Internal Rate of Return), accompanied by automated sensitivity tables based on purchase price vs. exit leverage.
 * M&A Accretion/Dilution Analysis Engine
   * Description: A program that takes two public companies, combines their financial statements based on customized financing structures (e.g., 50% cash, 50% stock), and calculates whether the deal increases or decreases Earnings Per Share (EPS) for the acquiring firm.
 * Automated Pitch Book Generator for Tech M&A
   * Description: An end-to-end automation tool that accepts target acquisition criteria, queries financial APIs, extracts strategic peer groups, and automatically renders clean, executive-ready presentation slides (PowerPoint/PDF) summarizing transaction metrics.
 * Financial Document Parsing & Due Diligence Agent (Computer Vision / Document AI)
   * Description: An end-to-end computer vision and OCR pipeline (using tools like Donut or LayoutLM) designed to parse complex scanned financial documents, pitch books, tables, and tax filings, directly extracting key deal risk factors into a structured dashboard.
 * Automated Trading Comparable Analysis ("Comps") Builder
   * Description: A Python web scraper and data modeler that takes a target company, identifies its closest sector competitors, pulls real-time EV/EBITDA, P/E, and EV/Revenue multiples, and automatically builds a relative valuation summary table.

   Build an event-driven backtesting engine in Python or C++.

Write a script that ingests, cleans, and structures live or historical tick data via a broker API.

Implement a simple statistical arbitrage or mean-reversion trading strategy with performance metrics.

create a frontend too finally, similar to bloomberg terminal or sorts
