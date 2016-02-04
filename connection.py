""" Needs documentation
"""
import time
from app import log
import globals
from handlers import connection_handler, history_handler, order_handler, portfolio_positions_handler, \
    account_summary_handler, account_update_handler, error_handler, market_handler
__author__ = 'Jason Haury'


def get_client(client_id=None):
    """ Creates a client connection to be used with orders
    """
    # TODO keep clients open and use this function to re-connect if needed.  Close_client() will simply return clients to pool
    if client_id is None:
        # Get client ID from our pool list in memory
        log.debug('Current clients available: {}'.format(_clientId_pool))
        timeout = globals._timeout
        while len(globals._clientId_pool) == 0 and timeout > 0:
            log.debug('Waiting for clientId to become available...({})'.format(timeout))
            time.sleep(0.5)
            timeout -= 1
        try:
            client_id = globals._clientId_pool.pop()
        except KeyError:
            client_id = None
    else:
        # A client ID was specified, so wait for it to become available if it's not already
        # First, make sure our client_id is valid
        if client_id not in range(8):
            # TODO create exception types and better error JSON responses
            return
        if client_id in globals._clientId_pool:
            globals._clientId_pool.remove(client_id)

    if client_id is None:
        return

    log.info('Attempting connection with client_id {}'.format(client_id))
    client = globals._client_pool[client_id]

    # Add synchronous response handlers
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
    # Enable logging if we're in debug mode
    # if current_app.debug is True:
    # client.registerAll(generic_handler)
    # client.enableLogging()
    if not client.isConnected():
        client.connect()
    return client
    """
    # Wait a bit to ensure we got messages back confirming we're connected and _order_id is updated.
    timeout = _timeout
    while client.isConnected() is False and timeout > 0:
        time.sleep(0.25)
        timeout -= 1
    log.debug('Waiting for messages to settle...')

    log.debug('Returning client...')
    return client
    """

def close_client(client):
    """ Put clientId back into pool but don't close connection
    """
    client_id = client.clientId
    # Add our client_id back into our pool
    globals._clientId_pool.add(client_id)
    return client_id