""" Needs documentation
"""
import os
from ib.opt import ibConnection
__author__ = 'Jason Haury'


# ---------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------
# Use environment variables
_ibgw_host = os.getenv('IBGW_HOST', '127.0.0.1')
_ibgw_port = int(os.getenv('IBGW_PORT', '4001'))  # Use 7496 for TWS
_timeout = 20  # Max loops

# Mutables
_managedAccounts = []
_clientId_pool = {0, 1, 2, 3, 4, 5, 6, 7}
_client_pool = {c: ibConnection(_ibgw_host, _ibgw_host, c) for c in xrange(8)}
_getting_order_id = False
_orderId = 0
_tickerId = 0


# ---------------------------------------------------------------------
# SYNCHRONOUS RESPONSES
# ---------------------------------------------------------------------
# Responses.  Global dicts to use for our responses as updated by Message handlers, keyed by clientId
_portfolio_positions_resp = {c: dict() for c in xrange(8)}
_account_summary_resp = {c: dict(accountSummaryEnd=False) for c in xrange(8)}
_account_update_resp = dict(accountDownloadEnd=False, updateAccountValue=dict(), updatePortfolio=[])
# Track errors keyed in "id" which is the orderId or tickerId (or -1 for connection errors)
_error_resp = dict()
# When getting order info, we want it for all clients, and don't care so much if multiple requests try to populate this
_order_resp = dict(openOrderEnd=False, openOrder=[], orderStatus=[])
# When placing/deleting orders, we care about what orderId is used.  Key off orderId.
_order_resp_by_order = dict()
# Dict of history responses keyed off of reqId (tickerId)
_history_resp = dict()


# ---------------------------------------------------------------------
# FEED RESPONSE BUFFERS
# ---------------------------------------------------------------------
# Globals to use for feed responses
_market_resp = {c: [] for c in xrange(8)}  # market feed
