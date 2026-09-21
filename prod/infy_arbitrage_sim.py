"""
INFY INDIA <-> INFY US ADR
IBKR RELATIVE-VALUE SIMULATOR
============================================================

SIMULATION ONLY.

NO ORDERS ARE CREATED OR SUBMITTED.

Confirmed contracts from your IBKR account:
    INFY NSE conId : 44652017
    INFY US conId  : 4813460

Current Infosys ADS ratio:
    1 ADS = 1 Indian equity share

The program:
    1. Connects to IBKR
    2. Resolves INFY NSE
    3. Resolves INFY NYSE ADR
    4. Requests delayed market data
    5. Uses manually supplied USD/INR
    6. Calculates ADR fair value
    7. Calculates premium / discount
    8. Generates simulated signals

There is intentionally:
    NO Order import
    NO placeOrder()
"""


from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract

import threading
import time
from datetime import datetime


# ================================================================
# CONNECTION
# ================================================================

HOST = "127.0.0.1"

# TWS Paper Trading
PORT = 7497

CLIENT_ID = 35


# ================================================================
# FX SETTING
# ================================================================

# Enter the USD/INR rate you want to use for this simulation.
#
# Example:
#
# If 1 USD = 95 INR:
#
MANUAL_USDINR = 95.00
#
# Do NOT leave this at zero.

# MANUAL_USDINR = 0.0


# ================================================================
# INFOSYS ADS RATIO
# ================================================================

# Confirmed:
#
# 1 INFY ADS = 1 Infosys Indian equity share

ADR_RATIO = 1.0


# ================================================================
# STRATEGY PARAMETERS
# ================================================================

# Minimum NET discrepancy before showing a signal.

ENTRY_THRESHOLD = 0.020       # 2.00%


# Placeholder transaction friction estimate.
#
# Later we can break this into:
#
# US commission
# India commission
# bid/ask spread
# FX spread
# ADR fees
# taxes
# borrow fee
# slippage

ESTIMATED_COST_RATE = 0.005    # 0.50%


# Print calculation at most once every 3 seconds.

CALCULATION_INTERVAL = 3.0


# ================================================================
# REQUEST IDs
# ================================================================

REQ_CONTRACT_INDIA = 1001
REQ_CONTRACT_US = 1002

REQ_MARKET_INDIA = 2001
REQ_MARKET_US = 2002


# ================================================================
# APPLICATION
# ================================================================

class INFYSimulator(EWrapper, EClient):

    def __init__(self):

        EClient.__init__(self, self)

        # Contracts

        self.india_contract = None
        self.us_contract = None

        self.india_search_finished = False
        self.us_search_finished = False

        self.market_data_started = False


        # India prices

        self.india_bid = None
        self.india_ask = None
        self.india_last = None
        self.india_close = None


        # US prices

        self.us_bid = None
        self.us_ask = None
        self.us_last = None
        self.us_close = None


        # Data type

        self.data_types = {}


        # Calculation timer

        self.last_calculation = 0


    # ============================================================
    # CONNECTION CALLBACK
    # ============================================================

    def nextValidId(self, orderId):

        print()
        print("=" * 80)
        print("CONNECTED TO IBKR")
        print("=" * 80)

        print(
            "Next valid order ID:",
            orderId
        )

        print()
        print("SIMULATION MODE")
        print("NO ORDERS WILL BE SUBMITTED.")
        print()

        print(
            f"Manual USD/INR reference: "
            f"{MANUAL_USDINR:.4f}"
        )

        print(
            f"INFY ADS ratio: "
            f"{ADR_RATIO:g}:1"
        )

        print()

        self.search_contracts()


    # ============================================================
    # ERROR CALLBACK
    # ============================================================

    def error(
        self,
        reqId,
        errorTime,
        errorCode,
        errorString,
        advancedOrderRejectJson=""
    ):

        informational_codes = {

            2104,
            2106,
            2107,
            2108,
            2158

        }

        if errorCode in informational_codes:

            print(
                f"IBKR INFO | "
                f"code={errorCode} | "
                f"{errorString}"
            )

            return


        print()

        print(
            f"IBKR MESSAGE | "
            f"request={reqId} | "
            f"code={errorCode}"
        )

        print(errorString)


    # ============================================================
    # CONTRACT SEARCH
    # ============================================================

    def search_contracts(self):

        print("=" * 80)
        print("SEARCHING CONTRACTS")
        print("=" * 80)


        # --------------------------------------------------------
        # INFY INDIA
        # --------------------------------------------------------

        india = Contract()

        india.symbol = "INFY"
        india.secType = "STK"
        india.exchange = "NSE"
        india.currency = "INR"

        print()
        print(
            "Searching INFY India..."
        )

        self.reqContractDetails(
            REQ_CONTRACT_INDIA,
            india
        )


        # --------------------------------------------------------
        # INFY USA
        # --------------------------------------------------------

        usa = Contract()

        usa.symbol = "INFY"
        usa.secType = "STK"
        usa.exchange = "SMART"
        usa.currency = "USD"

        print(
            "Searching INFY US ADR..."
        )

        self.reqContractDetails(
            REQ_CONTRACT_US,
            usa
        )


    # ============================================================
    # CONTRACT DETAILS
    # ============================================================

    def contractDetails(
        self,
        reqId,
        contractDetails
    ):

        contract = contractDetails.contract


        # --------------------------------------------------------
        # INDIA
        # --------------------------------------------------------

        if reqId == REQ_CONTRACT_INDIA:

            self.india_contract = contract

            print()
            print("-" * 80)
            print("INDIA CONTRACT FOUND")
            print("-" * 80)

            self.print_contract(contract)


        # --------------------------------------------------------
        # USA
        # --------------------------------------------------------

        elif reqId == REQ_CONTRACT_US:

            self.us_contract = contract

            print()
            print("-" * 80)
            print("US ADR CONTRACT FOUND")
            print("-" * 80)

            self.print_contract(contract)


    # ============================================================
    # PRINT CONTRACT
    # ============================================================

    def print_contract(self, contract):

        print(
            "Symbol           :",
            contract.symbol
        )

        print(
            "Local Symbol     :",
            contract.localSymbol
        )

        print(
            "Security Type    :",
            contract.secType
        )

        print(
            "Currency         :",
            contract.currency
        )

        print(
            "Exchange         :",
            contract.exchange
        )

        print(
            "Primary Exchange :",
            contract.primaryExchange
        )

        print(
            "conId            :",
            contract.conId
        )

        print(
            "Trading Class    :",
            contract.tradingClass
        )


    # ============================================================
    # CONTRACT SEARCH COMPLETE
    # ============================================================

    def contractDetailsEnd(self, reqId):

        if reqId == REQ_CONTRACT_INDIA:

            self.india_search_finished = True

            print()
            print(
                "INFY India search finished."
            )


        elif reqId == REQ_CONTRACT_US:

            self.us_search_finished = True

            print()
            print(
                "INFY US search finished."
            )


        self.check_contracts()


    # ============================================================
    # VERIFY CONTRACTS
    # ============================================================

    def check_contracts(self):

        if not (
            self.india_search_finished
            and
            self.us_search_finished
        ):

            return


        print()
        print("=" * 80)
        print("CONTRACT SEARCH RESULTS")
        print("=" * 80)


        # --------------------------------------------------------
        # INDIA
        # --------------------------------------------------------

        if self.india_contract is None:

            print(
                "FAILED: INFY India"
            )

            return


        print(
            f"OK: INFY India | "
            f"conId={self.india_contract.conId}"
        )


        # --------------------------------------------------------
        # USA
        # --------------------------------------------------------

        if self.us_contract is None:

            print(
                "FAILED: INFY US ADR"
            )

            return


        print(
            f"OK: INFY US ADR | "
            f"conId={self.us_contract.conId}"
        )


        # --------------------------------------------------------
        # FX
        # --------------------------------------------------------

        if MANUAL_USDINR <= 0:

            print()
            print("=" * 80)

            print(
                "CONFIGURATION ERROR"
            )

            print("=" * 80)

            print()

            print(
                "MANUAL_USDINR must be greater than zero."
            )

            print()

            print(
                "Edit MANUAL_USDINR near the top "
                "of the program."
            )

            print()

            print(
                "Example:"
            )

            print()

            print(
                "MANUAL_USDINR = 95.00"
            )

            print()

            return


        print(
            f"OK: USD/INR manual reference = "
            f"{MANUAL_USDINR:.4f}"
        )


        # --------------------------------------------------------
        # START MARKET DATA
        # --------------------------------------------------------

        if not self.market_data_started:

            self.market_data_started = True

            self.start_market_data()


    # ============================================================
    # START MARKET DATA
    # ============================================================

    def start_market_data(self):

        print()
        print("=" * 80)
        print("STARTING MARKET DATA")
        print("=" * 80)

        print()

        print(
            "Requesting delayed market data "
            "where live entitlement is unavailable."
        )


        # --------------------------------------------------------
        # MARKET DATA TYPE
        # --------------------------------------------------------
        #
        # 1 = Live
        # 2 = Frozen
        # 3 = Delayed
        # 4 = Delayed Frozen
        #
        # --------------------------------------------------------

        self.reqMarketDataType(3)


        # --------------------------------------------------------
        # INDIA
        # --------------------------------------------------------

        self.reqMktData(
            REQ_MARKET_INDIA,
            self.india_contract,
            "",
            False,
            False,
            []
        )


        # --------------------------------------------------------
        # USA
        # --------------------------------------------------------

        self.reqMktData(
            REQ_MARKET_US,
            self.us_contract,
            "",
            False,
            False,
            []
        )


        print()

        print(
            "Market data requests submitted."
        )

        print()

        print(
            f"USD/INR = "
            f"{MANUAL_USDINR:.4f} "
            f"[MANUAL SIMULATION INPUT]"
        )

        print()

        print(
            "Waiting for INFY prices..."
        )


    # ============================================================
    # MARKET DATA TYPE CALLBACK
    # ============================================================

    def marketDataType(
        self,
        reqId,
        marketDataType
    ):

        self.data_types[
            reqId
        ] = marketDataType


        names = {

            1: "LIVE",

            2: "FROZEN",

            3: "DELAYED",

            4: "DELAYED-FROZEN"

        }


        name = names.get(
            marketDataType,
            f"UNKNOWN-{marketDataType}"
        )


        if reqId == REQ_MARKET_INDIA:

            instrument = "INFY INDIA"


        elif reqId == REQ_MARKET_US:

            instrument = "INFY US ADR"


        else:

            instrument = str(reqId)


        print(
            f"DATA TYPE | "
            f"{instrument} | "
            f"{name}"
        )


    # ============================================================
    # PRICE CALLBACK
    # ============================================================

    def tickPrice(
        self,
        reqId,
        tickType,
        price,
        attrib
    ):

        if price is None:
            return


        if price <= 0:
            return


        # ========================================================
        # STANDARD TICK TYPES
        # ========================================================
        #
        # 1 = Bid
        # 2 = Ask
        # 4 = Last
        # 9 = Close
        #
        #
        # DELAYED TICK TYPES
        #
        # 66 = Delayed Bid
        # 67 = Delayed Ask
        # 68 = Delayed Last
        # 75 = Delayed Close
        #
        # ========================================================


        # --------------------------------------------------------
        # INDIA
        # --------------------------------------------------------

        if reqId == REQ_MARKET_INDIA:

            if tickType in (1, 66):

                self.india_bid = price


            elif tickType in (2, 67):

                self.india_ask = price


            elif tickType in (4, 68):

                self.india_last = price


            elif tickType in (9, 75):

                self.india_close = price


        # --------------------------------------------------------
        # USA
        # --------------------------------------------------------

        elif reqId == REQ_MARKET_US:

            if tickType in (1, 66):

                self.us_bid = price


            elif tickType in (2, 67):

                self.us_ask = price


            elif tickType in (4, 68):

                self.us_last = price


            elif tickType in (9, 75):

                self.us_close = price


        self.evaluate_strategy()


    # ============================================================
    # INDIA REFERENCE PRICE
    # ============================================================

    def get_india_price(self):

        # Prefer midpoint.

        if (
            self.india_bid is not None
            and
            self.india_ask is not None
        ):

            return (

                self.india_bid
                +
                self.india_ask

            ) / 2


        # Then last.

        if self.india_last is not None:

            return self.india_last


        # Finally close.

        return self.india_close


    # ============================================================
    # DATA TYPE NAME
    # ============================================================

    def get_data_type_name(self, reqId):

        data_type = self.data_types.get(
            reqId
        )


        names = {

            1: "LIVE",

            2: "FROZEN",

            3: "DELAYED",

            4: "DELAYED-FROZEN"

        }


        return names.get(
            data_type,
            "UNKNOWN"
        )


    # ============================================================
    # STRATEGY ENGINE
    # ============================================================

    def evaluate_strategy(self):

        now = time.time()


        # --------------------------------------------------------
        # THROTTLE
        # --------------------------------------------------------

        if (

            now
            -
            self.last_calculation

            < CALCULATION_INTERVAL

        ):

            return


        # --------------------------------------------------------
        # GET PRICES
        # --------------------------------------------------------

        india_price = self.get_india_price()


        if india_price is None:

            return


        if self.us_bid is None:

            return


        if self.us_ask is None:

            return


        self.last_calculation = now


        # ========================================================
        # FAIR VALUE
        # ========================================================
        #
        # INR/share
        #
        # divided by:
        #
        # INR/USD
        #
        # gives:
        #
        # USD/share
        #
        # multiplied by ADS ratio.
        #
        # ========================================================

        fair_value = (

            india_price
            *
            ADR_RATIO

        ) / MANUAL_USDINR


        if fair_value <= 0:

            return


        # ========================================================
        # US ADR EXPENSIVE
        # ========================================================
        #
        # If selling US ADR, assume execution at BID.
        #
        # ========================================================

        gross_sell_edge = (

            self.us_bid
            /
            fair_value

        ) - 1


        net_sell_edge = (

            gross_sell_edge
            -
            ESTIMATED_COST_RATE

        )


        # ========================================================
        # US ADR CHEAP
        # ========================================================
        #
        # If buying US ADR, assume execution at ASK.
        #
        # ========================================================

        gross_buy_edge = (

            fair_value
            /
            self.us_ask

        ) - 1


        net_buy_edge = (

            gross_buy_edge
            -
            ESTIMATED_COST_RATE

        )


        # ========================================================
        # OUTPUT
        # ========================================================

        self.print_dashboard(

            india_price,

            fair_value,

            gross_sell_edge,

            gross_buy_edge,

            net_sell_edge,

            net_buy_edge

        )


    # ============================================================
    # DASHBOARD
    # ============================================================

    def print_dashboard(
        self,
        india_price,
        fair_value,
        gross_sell_edge,
        gross_buy_edge,
        net_sell_edge,
        net_buy_edge
    ):

        print()
        print("=" * 80)

        print(
            "TIME:",
            datetime.now().strftime(
                "%Y-%m-%d %H:%M:%S"
            )
        )

        print("=" * 80)


        # --------------------------------------------------------
        # DATA STATUS
        # --------------------------------------------------------

        print()
        print("DATA STATUS")
        print("-" * 80)


        print(
            f"INFY India : "
            f"{self.get_data_type_name(REQ_MARKET_INDIA)}"
        )


        print(
            f"INFY US    : "
            f"{self.get_data_type_name(REQ_MARKET_US)}"
        )


        print(
            "USD/INR    : MANUAL"
        )


        # --------------------------------------------------------
        # INDIA
        # --------------------------------------------------------

        print()
        print("INDIA")
        print("-" * 80)


        if self.india_bid is not None:

            print(
                f"Bid       : "
                f"₹{self.india_bid:,.2f}"
            )


        if self.india_ask is not None:

            print(
                f"Ask       : "
                f"₹{self.india_ask:,.2f}"
            )


        if self.india_last is not None:

            print(
                f"Last      : "
                f"₹{self.india_last:,.2f}"
            )


        if self.india_close is not None:

            print(
                f"Close     : "
                f"₹{self.india_close:,.2f}"
            )


        print(
            f"Reference : "
            f"₹{india_price:,.2f}"
        )


        # --------------------------------------------------------
        # FX
        # --------------------------------------------------------

        print()
        print("FX")
        print("-" * 80)


        print(
            f"USD/INR   : "
            f"{MANUAL_USDINR:.4f}"
        )


        # --------------------------------------------------------
        # USA
        # --------------------------------------------------------

        print()
        print("USA ADR")
        print("-" * 80)


        print(
            f"Bid       : "
            f"${self.us_bid:.4f}"
        )


        print(
            f"Ask       : "
            f"${self.us_ask:.4f}"
        )


        if self.us_last is not None:

            print(
                f"Last      : "
                f"${self.us_last:.4f}"
            )


        # --------------------------------------------------------
        # FAIR VALUE
        # --------------------------------------------------------

        print()
        print("FAIR VALUE")
        print("-" * 80)


        print(
            f"ADS ratio : "
            f"{ADR_RATIO:g}"
        )


        print(
            f"India converted to USD : "
            f"${fair_value:.4f}"
        )


        # --------------------------------------------------------
        # EDGES
        # --------------------------------------------------------

        print()
        print("STRATEGY")
        print("-" * 80)


        print(
            f"Gross SELL edge : "
            f"{gross_sell_edge:.2%}"
        )


        print(
            f"Net SELL edge   : "
            f"{net_sell_edge:.2%}"
        )


        print(
            f"Gross BUY edge  : "
            f"{gross_buy_edge:.2%}"
        )


        print(
            f"Net BUY edge    : "
            f"{net_buy_edge:.2%}"
        )


        print(
            f"Entry threshold : "
            f"{ENTRY_THRESHOLD:.2%}"
        )


        print(
            f"Cost assumption : "
            f"{ESTIMATED_COST_RATE:.2%}"
        )


        # ========================================================
        # SIGNAL
        # ========================================================

        print()
        print("-" * 80)


        if net_sell_edge >= ENTRY_THRESHOLD:

            print(
                "SIMULATED SIGNAL:"
            )

            print()

            print(
                "US INFY ADR APPEARS EXPENSIVE"
            )

            print()

            print(
                "Hypothetical pair:"
            )

            print(
                "    LONG  INFY NSE"
            )

            print(
                "    SHORT INFY NYSE ADR"
            )


        elif net_buy_edge >= ENTRY_THRESHOLD:

            print(
                "SIMULATED SIGNAL:"
            )

            print()

            print(
                "US INFY ADR APPEARS CHEAP"
            )

            print()

            print(
                "Hypothetical pair:"
            )

            print(
                "    LONG  INFY NYSE ADR"
            )

            print(
                "    SHORT INFY NSE"
            )


        else:

            print(
                "SIMULATED SIGNAL: NO TRADE"
            )


        print()

        print(
            "*** SIMULATION ONLY — NO ORDER SUBMITTED ***"
        )

        print("=" * 80)


# ================================================================
# MAIN
# ================================================================

def main():

    print()
    print("=" * 80)
    print("INFY INDIA / USA ADR SIMULATOR")
    print("=" * 80)

    print()

    print(
        "NO ORDERS WILL BE PLACED."
    )

    print()


    # ------------------------------------------------------------
    # Validate FX before connecting.
    # ------------------------------------------------------------

    if MANUAL_USDINR <= 0:

        print("=" * 80)
        print("CONFIGURATION REQUIRED")
        print("=" * 80)

        print()

        print(
            "Set MANUAL_USDINR near the top "
            "of this file before running."
        )

        print()

        print(
            "For example:"
        )

        print()

        print(
            "MANUAL_USDINR = 95.00"
        )

        print()

        return


    # ------------------------------------------------------------
    # CREATE APP
    # ------------------------------------------------------------

    app = INFYSimulator()


    # ------------------------------------------------------------
    # CONNECT
    # ------------------------------------------------------------

    print(
        f"Connecting to "
        f"{HOST}:{PORT}..."
    )


    app.connect(

        HOST,

        PORT,

        clientId=CLIENT_ID

    )


    # ------------------------------------------------------------
    # NETWORK THREAD
    # ------------------------------------------------------------

    api_thread = threading.Thread(

        target=app.run,

        daemon=True

    )


    api_thread.start()


    # ------------------------------------------------------------
    # KEEP RUNNING
    # ------------------------------------------------------------

    try:

        while app.isConnected():

            time.sleep(1)


    except KeyboardInterrupt:

        print()

        print(
            "Stopping simulator..."
        )


    finally:

        # --------------------------------------------------------
        # CANCEL MARKET DATA
        # --------------------------------------------------------

        if app.market_data_started:

            try:

                app.cancelMktData(
                    REQ_MARKET_INDIA
                )

                app.cancelMktData(
                    REQ_MARKET_US
                )

            except Exception:

                pass


        # --------------------------------------------------------
        # DISCONNECT
        # --------------------------------------------------------

        app.disconnect()


        print()
        print("=" * 80)

        print(
            "SIMULATOR STOPPED"
        )

        print(
            "NO REAL ORDERS WERE SUBMITTED."
        )

        print("=" * 80)


# ================================================================
# RUN
# ================================================================

if __name__ == "__main__":

    main()