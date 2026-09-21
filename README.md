# Infosys Contract Lookup

This repository contains a small Interactive Brokers (IBKR) API script that
looks up contract metadata for the two Infosys listings used in a potential
cross-market comparison:

- **Infosys India:** symbol `INFY`, security type `STK`, exchange `NSE`, currency `INR`
- **Infosys US ADR:** symbol `INFY`, security type `STK`, exchange `SMART`, currency `USD`

The script prints the contract details returned by IBKR, including the local
symbol, contract ID, primary exchange, and trading class. It does not request
market data and does not submit any orders.

## Requirements

- Python 3
- Interactive Brokers TWS or IB Gateway running locally
- An API-enabled TWS/Gateway session
- The `ibapi` package from the official IBKR API distribution

Install the package from the `PythonClient` directory included with the IBKR
API download, for example:

```bash
python3 -m pip install .
```

## Connection settings

The script connects to `127.0.0.1` using client ID `22` and port `7497`, the
usual TWS paper-trading port. Common alternatives are:

| Application | Account | Port |
| --- | --- | ---: |
| TWS | Paper trading | 7497 |
| TWS | Live trading | 7496 |
| IB Gateway | Paper trading | 4002 |
| IB Gateway | Live trading | 4001 |

Update the `app.connect()` call in `test_unit/test_infy_pair.py` if your local session
uses a different host, port, or client ID. Keep the API session open before
running the script.

## Run

From the repository directory:

```bash
python3 test_unit/test_infy_pair.py
```

The script waits up to 15 seconds for the contract responses, disconnects,
and prints `NO ORDERS WERE SUBMITTED` before exiting.

## Request IDs

- `1001`: Infosys India / NSE
- `1002`: Infosys US ADR / SMART

These IDs make it easy to associate each callback with the lookup that
generated it.

## Simulation script

The `prod/infy_arbitrage_sim.py` script builds on the contract lookup by
requesting delayed market data and calculating an Infosys India versus US ADR
relative-value signal using a manually supplied USD/INR rate. It is a
simulation only: it contains no order imports and never calls `placeOrder()`.

Set `MANUAL_USDINR` near the top of the file before running it. The default
connection uses TWS paper trading on port `7497` with client ID `35`.

```bash
python3 prod/infy_arbitrage_sim.py
```

## Historical backtest

The `prod/backtest.py` script downloads daily historical bars for the Infosys
India share and US ADR through IBKR, joins them with the USD/INR history in
`prod/usdinr.csv`, and simulates entry and exit signals. It does not place
orders. The default configuration uses a five-year period, a 3% entry
threshold, a 0.5% exit threshold, and a 10-day maximum holding period.

Run it from the repository directory with:

```bash
python3 prod/backtest.py
```

The backtest uses these CSV files:

- `prod/usdinr.csv`: USD/INR input data
- `prod/infy_backtest_data.csv`: aligned price and deviation data
- `prod/infy_backtest_trades.csv`: simulated trade records
- `prod/infy_equity_curve.csv`: simulated portfolio values

The historical-data script requires `pandas`, `numpy`, and `matplotlib` in
addition to the IBKR API package.