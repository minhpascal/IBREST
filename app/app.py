#!/usr/bin/python
""" IBREST API Flask app controller file.  This file establishes the routes used for the IBREST API.  More info at:
https://github.com/hamx0r/IBREST

Most of this API takes HTTP requests and translates them to EClientSocket Methods:
https://www.interactivebrokers.com/en/software/api/apiguide/java/java_eclientsocket_methods.htm

The HTTP response is handled by compiling messages from EWrappper Methods into JSON:
https://www.interactivebrokers.com/en/software/api/apiguide/java/java_ewrapper_methods.htm
"""
# Flask imports
from flask import Flask, request #, g
from flask_restful import Resource, Api, reqparse
# IBREST imports
import sync, feeds
import parsers
import globals as g
import logging
import utils


# TODO use gevent to time.sleeps are non blocking
__author__ = 'Jason Haury'

app = Flask(__name__)
api = Api(app)

log = logging.getLogger(__name__)
log = utils.setup_logger(log)

# ---------------------------------------------------------------------
# RESOURCES
# ---------------------------------------------------------------------
class History(Resource):
    """ Resource to handle requests for historical data (15min delayed)
    """

    def get(self):
        """ Uses reqHistoricalData() to start a stream of historical data, then upon getting data in that streatm,
        cancels the stream with cancelHistoricalData() before returning the history
        """
        return utils.make_response(sync.get_history(request.args.copy()))


class Market(Resource):
    """ Resource to handle requests for market data
    """

    def get(self, symbol):
        """
        :return: JSON dict of dicts, with main keys being tickPrice, tickSize and optionComputation.
        """
        # TODO add query string params for Contract, and create feed accordingly
        return utils.make_response(feeds.get_market_data(symbol))


class Order(Resource):
    """ Resource to handle requests for Order
    """

    def get(self):
        """ Retrieves details of open orders using reqAllOpenOrders()
        """
        return utils.make_response(sync.get_open_orders())

    def post(self):
        """ Places an order with placeOrder().  This requires enough args to create a Contract & and Order:
        https://www.interactivebrokers.com/en/software/api/apiguide/java/java_socketclient_properties.htm
        """
        parser = parsers.order_parser.copy()
        for arg in parsers.contract_parser.args:
            parser.add_argument(arg)
        args = parser.parse_args()

        all_args = {k: v for k, v in request.values.iteritems()}
        # update with validated data
        for k, v in args.iteritems():
            all_args[k] = v

        #log.debug('all_args: {}'.format(all_args))
        return utils.make_response(sync.place_order(all_args))

    def delete(self):
        """ Cancels order with cancelOrder()
        """
        parser = reqparse.RequestParser(bundle_errors=True)
        parser.add_argument('orderId', type=int, required=True,
                            help='Order ID to cancel')
        args = parser.parse_args()
        return utils.make_response(sync.cancel_order(args['orderId']))


class PortfolioPositions(Resource):
    """ Resource to handle requests for market data
    """

    def get(self):
        """
        :return: JSON dict of dicts, with main keys being tickPrice, tickSize and optionComputation.
        """
        return utils.make_response(sync.get_portfolio_positions())


class AccountSummary(Resource):
    """ Resource to handle requests for account summary information
    """

    def get(self):
        """
        One may either provide a CSV string of `tags` desired, or else provide duplicate query string `tag` values
        which the API will then put together in a CSV list as needed by IbPy
        :return: JSON dict of dicts
        """
        choices = {"AccountType", "NetLiquidation", "TotalCashValue", "SettledCash", "AccruedCash", "BuyingPower",
                   "EquityWithLoanValue", "PreviousDayEquityWithLoanValue", "GrossPositionValue", "RegTEquity",
                   "RegTMargin", "SMA", "InitMarginReq", "MaintMarginReq", "AvailableFunds", "ExcessLiquidity",
                   "Cushion", "FullInitMarginReq", "FullMaintMarginReq", "FullAvailableFunds", "FullExcessLiquidity",
                   "LookAheadNextChange", "LookAheadInitMarginReq", "LookAheadMaintMarginReq",
                   "LookAheadAvailableFunds", "LookAheadExcessLiquidity", "HighestSeverity", "DayTradesRemaining",
                   "Leverage"}
        parser = reqparse.RequestParser(bundle_errors=True)
        parser.add_argument('tags', type=str, help='CSV list of tags from this set: {}'.format(choices), trim=True)
        parser.add_argument('tag', type=str, action='append', help='Account information you want to see: {error_msg}',
                            trim=True, choices=choices, default=[])
        args = parser.parse_args()
        # Make a master list of tags from all possible arguments
        tags = args['tag']
        tags += args['tags'].split(',') if args['tags'] is not None else []
        if len(tags) == 0:
            # No tags were passed, so throw an error
            return dict(message=dict(tags='Must provide 1 or more `tag` args, and/or a CSV `tags` arg')), 400
        # Reduce and re-validate
        tags = set(tags)
        if not tags.issubset(choices):
            return dict(message=dict(tags='All tags must be from this set: {}'.format(choices))), 400
        # re-create CSV list
        tags = ','.join(list(tags))
        #debug('TAGS: {}'.format(tags))
        return utils.make_response(sync.get_account_summary(tags))


class AccountUpdate(Resource):
    """ Resource to handle requests for account update information.
    """

    def get(self):
        """
        This endpoint does _not_ subscribe to account info (hence "Update" instead of "Updates" - use feed for that),
        but only gets latest info for given acctCode.
        :return: JSON dict of dicts
        """
        parser = reqparse.RequestParser()
        parser.add_argument('acctCode', type=str, help='Account number/code', trim=True, required=True)
        args = parser.parse_args()
        return utils.make_response(sync.get_account_update(args['acctCode']))


class ClientStates(Resource):
    """ Explore what the connection states are for each client
    """

    def get(self):
        resp = dict(connected=dict(), available=dict())
        for id, client in g.client_pool.iteritems():
            resp['connected'][id] = client.isConnected() if client is not None else None
        resp['available'] = g.clientId_pool
        return utils.make_response(resp)


class Test(Resource):
    def get(self):
        resp = ""
        for k, v in  request.environ.iteritems():
            resp += "{}: {}".format(str(k), str(v))
        print request.environ.items()
        return resp
# ---------------------------------------------------------------------
# ROUTING
# ---------------------------------------------------------------------
api.add_resource(History, '/history')
api.add_resource(Market, '/market/<string:symbol>')
api.add_resource(Order, '/order')
api.add_resource(PortfolioPositions, '/account/positions')
api.add_resource(AccountSummary, '/account/summary')
api.add_resource(AccountUpdate, '/account/update')
api.add_resource(ClientStates, '/clients')
api.add_resource(Test, '/test')

if __name__ == '__main__':
    import os
    import connection
    host = os.getenv('IBREST_HOST', '127.0.0.1')
    port = int(os.getenv('IBREST_PORT', '5000'))
    context = ('ibrest.crt', 'ibrest.key')
    # Set up globals in flask.g object
    '''
    for attr in dir(globals):
        if attr[:2] != '__':
            setattr(g, attr, getattr(globals, attr))
    '''
    log.debug('Setting up IBREST at {}:{}'.format(host, port))
    log.debug('Using IB GW clients at: {}:{}'.format(g.client_pool[0].host, g.client_pool[0].port))
    # Connect to all clients in our pool
    for c in xrange(len(g.clientId_pool)+1):  # +1 for Order client
        client = g.client_pool[c]
        connection.setup_client(client)
        client.connect()
        g.client_pool[c] = client


    # TODO We _could_ run 8 processes and tie each to a different client ID, and then remove client locks as a global
    app.run(debug=False, host=host, port=port, ssl_context=context, threaded=True)
    #app.run(debug=False, host=host, port=port,  threaded=True)