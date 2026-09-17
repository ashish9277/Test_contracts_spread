from ibapi.client import EClient
from ibapi.wrapper import EWrapper
from ibapi.contract import Contract

import threading
import time


class IBKRTest(EWrapper, EClient):

    def __init__(self):
        EClient.__init__(self, self)

    # ============================================================
    # CONNECTION
    # ============================================================

    def nextValidId(self, orderId):
        """
        Called by IBKR after a successful API connection.
        """

        print("\n" + "=" * 70)
        print("CONNECTED TO IBKR")
        print("Next order ID:", orderId)
        print("=" * 70)

        # Start our contract searches.
        self.find_contracts()

    # ============================================================
    # ERROR / INFORMATION MESSAGES
    # ============================================================

    def error(
        self,
        reqId,
        errorTime,
        errorCode,
        errorString,
        advancedOrderRejectJson=""
    ):
        """
        Callback used by the current IBKR API version.

        Some messages such as 2104/2106/2158 are informational
        connectivity messages rather than actual failures.
        """

        print(
            f"\nIBKR MESSAGE"
            f"\nRequest ID : {reqId}"
            f"\nTime       : {errorTime}"
            f"\nCode       : {errorCode}"
            f"\nMessage    : {errorString}"
        )

    # ============================================================
    # CONTRACT DETAILS CALLBACK
    # ============================================================

    def contractDetails(self, reqId, contractDetails):
        """
        Called whenever IBKR finds a contract matching our search.
        """

        c = contractDetails.contract

        print("\n" + "-" * 70)

        if reqId == 1001:
            print("INDIA CONTRACT FOUND")

        elif reqId == 1002:
            print("USA CONTRACT FOUND")

        else:
            print("CONTRACT FOUND")

        print("-" * 70)

        print("Request ID       :", reqId)
        print("Symbol           :", c.symbol)
        print("Local Symbol     :", c.localSymbol)
        print("Security Type    :", c.secType)
        print("Currency         :", c.currency)
        print("Exchange         :", c.exchange)
        print("Primary Exchange :", c.primaryExchange)
        print("conId            :", c.conId)
        print("Trading Class    :", c.tradingClass)

    # ============================================================
    # CONTRACT SEARCH FINISHED
    # ============================================================

    def contractDetailsEnd(self, reqId):

        if reqId == 1001:

            print("\nFinished searching for:")
            print("Infosys India / NSE")

        elif reqId == 1002:

            print("\nFinished searching for:")
            print("Infosys US ADR")

        else:

            print(
                "\nFinished contract search for request:",
                reqId
            )

    # ============================================================
    # FIND INDIA + USA CONTRACTS
    # ============================================================

    def find_contracts(self):

        # --------------------------------------------------------
        # 1. INFOSYS INDIA
        # --------------------------------------------------------

        india = Contract()

        india.symbol = "INFY"
        india.secType = "STK"
        india.exchange = "NSE"
        india.currency = "INR"

        print("\nSearching IBKR for Infosys on NSE...")

        self.reqContractDetails(
            1001,
            india
        )

        # --------------------------------------------------------
        # 2. INFOSYS USA ADR
        # --------------------------------------------------------

        usa = Contract()

        usa.symbol = "INFY"
        usa.secType = "STK"
        usa.exchange = "SMART"
        usa.currency = "USD"

        print("Searching IBKR for INFY US ADR...")

        self.reqContractDetails(
            1002,
            usa
        )


# ================================================================
# START PROGRAM
# ================================================================

app = IBKRTest()


print("=" * 70)
print("IBKR INFY INDIA / USA CONTRACT TEST")
print("=" * 70)

print("\nConnecting to TWS...")

# ---------------------------------------------------------------
# CONNECTION SETTINGS
# ---------------------------------------------------------------
#
# Typical ports:
#
# TWS Paper Trading = 7497
# TWS Live Trading  = 7496
#
# IB Gateway Paper = 4002
# IB Gateway Live  = 4001
#
# Keep the port that worked in your previous connection test.
#
# ---------------------------------------------------------------

app.connect(
    "127.0.0.1",
    7497,
    clientId=22
)


# ================================================================
# START IBKR NETWORK THREAD
# ================================================================

api_thread = threading.Thread(
    target=app.run,
    daemon=True
)

api_thread.start()


# ================================================================
# WAIT FOR IBKR RESPONSE
# ================================================================

print("\nWaiting for IBKR...")

# Give IBKR enough time to return both contract searches.
time.sleep(15)


# ================================================================
# DISCONNECT
# ================================================================

print("\nDisconnecting from IBKR...")

app.disconnect()

print("\n" + "=" * 70)
print("TEST COMPLETE")
print("NO ORDERS WERE SUBMITTED")
print("=" * 70)