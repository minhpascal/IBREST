""" These globals are used to glue the asyncronous messages together to form a synchronous system.  Each set of globals
are unique to a process, and each process makes use of a single clientId.  Thus, the clientId is set to match the PID.
Furthermore, orderId's can now be auto-incremented by code rather than fetching the nextOrderId before each order
"""
import os
from ib.opt import ibConnection
from handlers import connection_handler, history_handler, order_handler, portfolio_positions_handler, \
    account_summary_handler, account_update_handler, error_handler, market_handler
import logging
import utils
from flask import current_app

__author__ = 'Jason Haury'
log = logging.getLogger(__name__)
log = utils.setup_logger(log)

# ---------------------------------------------------------------------
# CONFIGURATION
# ---------------------------------------------------------------------
# Use environment variables
ibgw_host = os.getenv('IBGW_HOST', '127.0.0.1')
ibgw_port = int(os.getenv('IBGW_PORT', '4001'))  # Use 7496 for TWS
timeout = 20  # Max loops

# Mutables
managedAccounts = []
orderId = 0
tickerId = 0



# ---------------------------------------------------------------------
# CONNECTION
# ---------------------------------------------------------------------
clientId = os.getpid()
client = ibConnection(ibgw_host, ibgw_port, clientId)
# Enable logging if we're in debug mode
client.register(connection_handler, 'ManagedAccounts', 'NextValidId')
client.register(history_handler, 'HistoricalData')
client.register(order_handler, 'OpenOrder', 'OrderStatus', 'OpenOrderEnd')
client.register(portfolio_positions_handler, 'Position', 'PositionEnd')
client.register(account_summary_handler, 'AccountSummary', 'AccountSummaryEnd')
client.register(account_update_handler, 'UpdateAccountTime', 'UpdateAccountValue', 'UpdatePortfolio',
                'AccountDownloadEnd')
client.register(error_handler, 'Error')
# Add handlers for feeds
client.register(market_handler, 'TickSize', 'TickPrice')
client.connect()

def get_client():
    """ Gets the global client and ensures it's still connected
    """
    if current_app.debug is True:
        client.enableLogging()
    log.debug('Attempting connection with client_id {}'.format(clientId))
    # Reconnect if needed
    if not client.isConnected():
        client.connect()
    return client

# ---------------------------------------------------------------------
# SYNCHRONOUS RESPONSES
# ---------------------------------------------------------------------
# Responses.  Global dicts to use for our responses as updated by Message handlers, keyed by clientId
portfolio_positions_resp = dict()
account_summary_resp = dict(accountSummaryEnd=False)
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
market_resp = []  # market feed


