""" Needs documentation
"""
import os
from ib.opt import ibConnection

__author__ = 'Jason Haury'


# ---------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------
# Use environment variables
ibgw_host = os.getenv('IBGW_HOST', '127.0.0.1')
ibgw_port = int(os.getenv('IBGW_PORT', '4001'))  # Use 7496 for TWS
timeout = 20  # Max loops

# Mutables
managedAccounts = []
clientId_pool = [0, 1, 2, 3, 4, 5, 6, 7]  # Round-robbin list of clientId's
client_pool = {c: ibConnection(ibgw_host, ibgw_port, c) for c in xrange(8)}
getting_order_id = False
orderId = 0
tickerId = 0


# ---------------------------------------------------------------------
# SYNCHRONOUS RESPONSES
# ---------------------------------------------------------------------
# Responses.  Global dicts to use for our responses as updated by Message handlers, keyed by clientId
portfolio_positions_resp = {c: dict() for c in xrange(8)}
account_summary_resp = {c: dict(accountSummaryEnd=False) for c in xrange(8)}
account_update_resp = dict(accountDownloadEnd=False, updateAccountValue=dict(), updatePortfolio=[])
# Track errors keyed in "id" which is the orderId or tickerId (or -1 for connection errors)
error_resp = {-1: {"errorCode": 502, "errorMsg": "Couldn't connect to TWS.  Confirm that \"Enable ActiveX and Socket "
                                                 "Clients\" is enabled on the TWS \"Configure->API\" menu.", "id": -1},
              -2: {"errorCode": None, "errorMsg": "Client ID not availabe in time.  Try request later", "id": -2}}
# When getting order info, we want it for all clients, and don't care so much if multiple requests try to populate this
order_resp = dict(openOrderEnd=False, openOrder=[], orderStatus=[])
# When placing/deleting orders, we care about what orderId is used.  Key off orderId.
order_resp_by_order = dict()
# Dict of history responses keyed off of reqId (tickerId)
history_resp = dict()


# ---------------------------------------------------------------------
# FEED RESPONSE BUFFERS
# ---------------------------------------------------------------------
# Globals to use for feed responses
market_resp = {c: [] for c in xrange(8)}  # market feed
