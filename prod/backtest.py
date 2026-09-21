"""
INFY NSE vs INFY NYSE ADR - BACKTEST
=====================================

Strategy:
    India INFY close
        ↓
    convert INR -> USD
        ↓
    compare with INFY ADR
        ↓
    calculate premium / discount
        ↓
    enter relative-value position when deviation > threshold
        ↓
    exit when deviation mean-reverts

NO ORDERS ARE PLACED.

Requirements:
    pip install pandas numpy matplotlib

IBKR TWS / Gateway must be running.

FX input:
    usdinr.csv

CSV format:
    date,usdinr
    2025-01-02,85.75
    2025-01-03,85.82
    ...
"""

from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract

import threading
import time
import pandas as pd
import numpy as np
import matplotlib.pyplot as plt


# ================================================================
# CONFIGURATION
# ================================================================

HOST = "127.0.0.1"
PORT = 7497
CLIENT_ID = 50


# ================================================================
# CONTRACT IDS CONFIRMED FROM YOUR IBKR OUTPUT
# ================================================================

INDIA_CONID = 44652017
US_CONID = 4813460


# ================================================================
# ADR RATIO
# ================================================================

# Infosys:
#
# 1 NYSE ADS = 1 Indian Infosys equity share

ADR_RATIO = 1.0


# ================================================================
# BACKTEST PERIOD
# ================================================================

# IBKR duration.
#
# Examples:
#
# "1 Y"
# "2 Y"
# "5 Y"

BACKTEST_DURATION = "5 Y"


# ================================================================
# STRATEGY PARAMETERS
# ================================================================

# Enter trade when deviation exceeds this.

ENTRY_THRESHOLD = 0.03       # 3%


# Exit when deviation comes back inside this.

EXIT_THRESHOLD = 0.005       # 0.5%


# Maximum holding period.

MAX_HOLD_DAYS = 10


# Estimated round-trip friction.

ROUND_TRIP_COST = 0.005       # 0.50%


# Starting portfolio.

INITIAL_CAPITAL = 100_000


# Fraction allocated to each pair trade.

POSITION_SIZE = 0.10


# ================================================================
# REQUEST IDs
# ================================================================

REQ_INDIA = 1001
REQ_US = 1002


# ================================================================
# IBKR HISTORICAL DATA APP
# ================================================================

class HistoricalDataApp(EWrapper, EClient):

    def __init__(self):

        EClient.__init__(self, self)

        self.india_data = []
        self.us_data = []

        self.india_done = False
        self.us_done = False

        self.connected = False


    # ============================================================
    # CONNECTION
    # ============================================================

    def nextValidId(self, orderId):

        self.connected = True

        print()
        print("=" * 70)
        print("CONNECTED TO IBKR")
        print("=" * 70)

        print(
            "Downloading historical data..."
        )

        self.download_data()


    # ============================================================
    # ERROR HANDLER
    # ============================================================

    def error(self, reqId, errorCode, errorString, advancedOrderRejectJson=""):

        informational = {
            2104,
            2106,
            2107,
            2108,
            2158
        }

        if errorCode in informational:
            print(
                f"IBKR INFO | "
                f"code={errorCode} | "
                f"{errorString}"
            )
            return

        print(
            f"IBKR ERROR | "
            f"request={reqId} | "
            f"code={errorCode} | "
            f"{errorString}"
        )

        if advancedOrderRejectJson:
            print(
                f"Advanced reject: "
                f"{advancedOrderRejectJson}"
            )


    # ============================================================
    # CONTRACTS
    # ============================================================

    def india_contract(self):

        c = Contract()

        c.conId = INDIA_CONID
        c.symbol = "INFY"
        c.secType = "STK"
        c.exchange = "NSE"
        c.currency = "INR"

        return c


    def us_contract(self):

        c = Contract()

        c.conId = US_CONID
        c.symbol = "INFY"
        c.secType = "STK"
        c.exchange = "SMART"
        c.primaryExchange = "NYSE"
        c.currency = "USD"

        return c


    # ============================================================
    # DOWNLOAD
    # ============================================================

    def download_data(self):

        # --------------------------------------------------------
        # INDIA
        # --------------------------------------------------------

        self.reqHistoricalData(
            REQ_INDIA,
            self.india_contract(),

            "",

            BACKTEST_DURATION,

            "1 day",

            "TRADES",

            1,      # Regular trading hours

            1,

            False,

            []
        )


        # --------------------------------------------------------
        # USA
        # --------------------------------------------------------

        self.reqHistoricalData(
            REQ_US,
            self.us_contract(),

            "",

            BACKTEST_DURATION,

            "1 day",

            "TRADES",

            1,

            1,

            False,

            []
        )


    # ============================================================
    # RECEIVE BARS
    # ============================================================

    def historicalData(
        self,
        reqId,
        bar
    ):

        row = {

            "date": bar.date,

            "open": bar.open,

            "high": bar.high,

            "low": bar.low,

            "close": bar.close,

            "volume": bar.volume

        }


        if reqId == REQ_INDIA:

            self.india_data.append(
                row
            )


        elif reqId == REQ_US:

            self.us_data.append(
                row
            )


    # ============================================================
    # FINISHED
    # ============================================================

    def historicalDataEnd(
        self,
        reqId,
        start,
        end
    ):

        if reqId == REQ_INDIA:

            self.india_done = True

            print(
                f"India history received: "
                f"{len(self.india_data)} bars"
            )


        elif reqId == REQ_US:

            self.us_done = True

            print(
                f"US history received: "
                f"{len(self.us_data)} bars"
            )


# ================================================================
# LOAD FX
# ================================================================

def load_fx():

    print()
    print(
        "Loading USD/INR history..."
    )

    fx = pd.read_csv(
        "usdinr.csv"
    )


    fx["date"] = pd.to_datetime(
        fx["date"]
    )


    fx = fx.sort_values(
        "date"
    )


    fx = fx.set_index(
        "date"
    )


    return fx


# ================================================================
# PREPARE DATA
# ================================================================

def prepare_data(
    india_rows,
    us_rows,
    fx
):

    india = pd.DataFrame(
        india_rows
    )


    usa = pd.DataFrame(
        us_rows
    )


    # ------------------------------------------------------------
    # DATE
    # ------------------------------------------------------------

    india["date"] = pd.to_datetime(
        india["date"]
    )


    usa["date"] = pd.to_datetime(
        usa["date"]
    )


    # ------------------------------------------------------------
    # KEEP CLOSE
    # ------------------------------------------------------------

    india = india[
        [
            "date",
            "close"
        ]
    ]


    usa = usa[
        [
            "date",
            "close"
        ]
    ]


    india = india.rename(
        columns={
            "close": "india_close"
        }
    )


    usa = usa.rename(
        columns={
            "close": "us_close"
        }
    )


    # ------------------------------------------------------------
    # MERGE INDIA + USA
    # ------------------------------------------------------------

    df = pd.merge(

        india,

        usa,

        on="date",

        how="outer"

    )


    df = df.sort_values(
        "date"
    )


    df = df.set_index(
        "date"
    )


    # ============================================================
    # IMPORTANT:
    #
    # NSE and NYSE have different holidays.
    #
    # We do NOT blindly forward-fill stock prices for long periods.
    # ============================================================

    df = df.join(
        fx,
        how="left"
    )


    # FX can reasonably be forward-filled over weekends /
    # isolated holidays.

    df["usdinr"] = (
        df["usdinr"]
        .ffill(limit=3)
    )


    # Require both stock markets to have an observation.

    df = df.dropna(
        subset=[
            "india_close",
            "us_close",
            "usdinr"
        ]
    )


    return df


# ================================================================
# CALCULATE FAIR VALUE
# ================================================================

def calculate_signal(df):

    # ------------------------------------------------------------
    # INDIA PRICE IN USD
    # ------------------------------------------------------------

    df["fair_value"] = (

        df["india_close"]

        * ADR_RATIO

        / df["usdinr"]

    )


    # ------------------------------------------------------------
    # ADR PREMIUM
    # ------------------------------------------------------------
    #
    # Positive:
    #
    # US ADR expensive relative to India.
    #
    # Negative:
    #
    # US ADR cheap relative to India.
    #
    # ------------------------------------------------------------

    df["premium"] = (

        df["us_close"]

        / df["fair_value"]

    ) - 1


    return df


# ================================================================
# BACKTEST
# ================================================================

def run_backtest(df):

    capital = INITIAL_CAPITAL

    equity_curve = []

    trades = []


    position = 0

    # position:
    #
    # 0  = flat
    #
    # -1 = short US / long India
    #
    # +1 = long US / short India


    entry_premium = None
    entry_date = None
    entry_capital = None

    days_held = 0


    for date, row in df.iterrows():

        premium = row["premium"]


        # ========================================================
        # NO POSITION
        # ========================================================

        if position == 0:

            # ----------------------------------------------------
            # US ADR expensive
            # ----------------------------------------------------

            if premium >= ENTRY_THRESHOLD:

                position = -1

                entry_premium = premium

                entry_date = date

                entry_capital = (
                    capital
                    * POSITION_SIZE
                )

                days_held = 0


            # ----------------------------------------------------
            # US ADR cheap
            # ----------------------------------------------------

            elif premium <= -ENTRY_THRESHOLD:

                position = 1

                entry_premium = premium

                entry_date = date

                entry_capital = (
                    capital
                    * POSITION_SIZE
                )

                days_held = 0


        # ========================================================
        # POSITION OPEN
        # ========================================================

        else:

            days_held += 1


            # ----------------------------------------------------
            # EXIT CONDITIONS
            # ----------------------------------------------------

            mean_reversion = (

                abs(premium)
                <= EXIT_THRESHOLD

            )


            max_holding = (

                days_held
                >= MAX_HOLD_DAYS

            )


            if (
                mean_reversion
                or
                max_holding
            ):

                # =================================================
                # RETURN FROM SPREAD MOVEMENT
                # =================================================
                #
                # Short premium:
                #
                # profit when premium falls.
                #
                #
                # Long premium:
                #
                # profit when premium rises.
                #
                # =================================================

                if position == -1:

                    gross_return = (

                        entry_premium
                        -
                        premium

                    )


                else:

                    gross_return = (

                        premium
                        -
                        entry_premium

                    )


                # ------------------------------------------------
                # COST
                # ------------------------------------------------

                net_return = (

                    gross_return
                    -
                    ROUND_TRIP_COST

                )


                pnl = (

                    entry_capital
                    *
                    net_return

                )


                capital += pnl


                trades.append({

                    "entry_date":
                        entry_date,

                    "exit_date":
                        date,

                    "direction":
                        (
                            "SHORT_US_LONG_INDIA"
                            if position == -1
                            else
                            "LONG_US_SHORT_INDIA"
                        ),

                    "entry_premium":
                        entry_premium,

                    "exit_premium":
                        premium,

                    "days":
                        days_held,

                    "gross_return":
                        gross_return,

                    "net_return":
                        net_return,

                    "pnl":
                        pnl,

                    "capital":
                        capital

                })


                position = 0

                entry_premium = None
                entry_date = None
                entry_capital = None
                days_held = 0


        equity_curve.append({

            "date":
                date,

            "capital":
                capital

        })


    return (
        pd.DataFrame(trades),
        pd.DataFrame(equity_curve)
    )


# ================================================================
# PERFORMANCE
# ================================================================

def performance_report(
    trades,
    equity
):

    print()
    print("=" * 70)
    print("BACKTEST RESULTS")
    print("=" * 70)


    if len(trades) == 0:

        print(
            "No trades generated."
        )

        return


    total_trades = len(
        trades
    )


    winners = trades[
        trades["pnl"] > 0
    ]


    losers = trades[
        trades["pnl"] <= 0
    ]


    win_rate = (

        len(winners)
        /
        total_trades

    )


    ending_capital = (

        equity[
            "capital"
        ]
        .iloc[-1]

    )


    total_return = (

        ending_capital
        /
        INITIAL_CAPITAL

    ) - 1


    # ------------------------------------------------------------
    # MAX DRAWDOWN
    # ------------------------------------------------------------

    equity["peak"] = (

        equity[
            "capital"
        ]
        .cummax()

    )


    equity["drawdown"] = (

        equity[
            "capital"
        ]

        /
        equity[
            "peak"
        ]

    ) - 1


    max_drawdown = (

        equity[
            "drawdown"
        ]
        .min()

    )


    print(
        f"Starting capital : "
        f"${INITIAL_CAPITAL:,.2f}"
    )


    print(
        f"Ending capital   : "
        f"${ending_capital:,.2f}"
    )


    print(
        f"Total return     : "
        f"{total_return:.2%}"
    )


    print()

    print(
        f"Trades           : "
        f"{total_trades}"
    )


    print(
        f"Winners          : "
        f"{len(winners)}"
    )


    print(
        f"Losers           : "
        f"{len(losers)}"
    )


    print(
        f"Win rate         : "
        f"{win_rate:.2%}"
    )


    print()

    print(
        f"Average trade    : "
        f"{trades['net_return'].mean():.2%}"
    )


    print(
        f"Best trade       : "
        f"{trades['net_return'].max():.2%}"
    )


    print(
        f"Worst trade      : "
        f"{trades['net_return'].min():.2%}"
    )


    print(
        f"Max drawdown     : "
        f"{max_drawdown:.2%}"
    )


    print("=" * 70)


# ================================================================
# SAVE RESULTS
# ================================================================

def save_results(
    data,
    trades,
    equity
):

    data.to_csv(
        "infy_backtest_data.csv"
    )


    trades.to_csv(
        "infy_backtest_trades.csv",
        index=False
    )


    equity.to_csv(
        "infy_equity_curve.csv",
        index=False
    )


    print()
    print(
        "Results saved:"
    )

    print(
        "  infy_backtest_data.csv"
    )

    print(
        "  infy_backtest_trades.csv"
    )

    print(
        "  infy_equity_curve.csv"
    )


# ================================================================
# CHART
# ================================================================

def plot_results(
    data,
    equity
):

    # ------------------------------------------------------------
    # PREMIUM
    # ------------------------------------------------------------

    plt.figure(
        figsize=(12, 6)
    )


    plt.plot(
        data.index,
        data["premium"] * 100
    )


    plt.axhline(
        ENTRY_THRESHOLD * 100,
        linestyle="--"
    )


    plt.axhline(
        -ENTRY_THRESHOLD * 100,
        linestyle="--"
    )


    plt.axhline(
        0,
        linestyle=":"
    )


    plt.title(
        "INFY ADR Premium / Discount"
    )


    plt.ylabel(
        "Premium (%)"
    )


    plt.xlabel(
        "Date"
    )


    plt.tight_layout()

    plt.show()


    # ------------------------------------------------------------
    # EQUITY CURVE
    # ------------------------------------------------------------

    plt.figure(
        figsize=(12, 6)
    )


    plt.plot(
        equity["date"],
        equity["capital"]
    )


    plt.title(
        "Backtest Equity Curve"
    )


    plt.ylabel(
        "Portfolio Value ($)"
    )


    plt.xlabel(
        "Date"
    )


    plt.tight_layout()

    plt.show()


# ================================================================
# MAIN
# ================================================================

def main():

    print()
    print("=" * 70)
    print("INFY INDIA / US ADR BACKTEST")
    print("=" * 70)


    # ------------------------------------------------------------
    # FX
    # ------------------------------------------------------------

    fx = load_fx()


    # ------------------------------------------------------------
    # IBKR
    # ------------------------------------------------------------

    app = HistoricalDataApp()


    app.connect(
        HOST,
        PORT,
        clientId=CLIENT_ID
    )


    thread = threading.Thread(
        target=app.run,
        daemon=True
    )


    thread.start()


    # ------------------------------------------------------------
    # WAIT FOR HISTORICAL DATA
    # ------------------------------------------------------------

    timeout = 120

    start = time.time()


    while not (
        app.india_done
        and
        app.us_done
    ):

        if (
            time.time()
            -
            start
            >
            timeout
        ):

            print(
                "Historical data request timed out."
            )

            app.disconnect()

            return


        time.sleep(
            0.5
        )


    app.disconnect()


    # ------------------------------------------------------------
    # DATA
    # ------------------------------------------------------------

    data = prepare_data(

        app.india_data,

        app.us_data,

        fx

    )


    print()
    print(
        f"Matched trading days: "
        f"{len(data)}"
    )


    # ------------------------------------------------------------
    # SIGNAL
    # ------------------------------------------------------------

    data = calculate_signal(
        data
    )


    # ------------------------------------------------------------
    # BACKTEST
    # ------------------------------------------------------------

    trades, equity = run_backtest(
        data
    )


    # ------------------------------------------------------------
    # RESULTS
    # ------------------------------------------------------------

    performance_report(
        trades,
        equity
    )


    # ------------------------------------------------------------
    # SAVE
    # ------------------------------------------------------------

    save_results(
        data,
        trades,
        equity
    )


    # ------------------------------------------------------------
    # CHART
    # ------------------------------------------------------------

    plot_results(
        data,
        equity
    )


if __name__ == "__main__":

    main()