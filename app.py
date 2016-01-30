#!/usr/bin/python
""" IBREST API Flask app controller file.  This file establishes the routes used for the IBREST API.  More info at:
https://github.com/hamx0r/IBREST

Most of this API takes HTTP requests and translates them to EClientSocket Methods:
https://www.interactivebrokers.com/en/software/api/apiguide/java/java_eclientsocket_methods.htm

The HTTP response is handled by compiling messages from EWrappper Methods into JSON:
https://www.interactivebrokers.com/en/software/api/apiguide/java/java_ewrapper_methods.htm
"""
# Flask imports
from flask import Flask, request
from flask_restful import Resource, Api, reqparse
# IBREST imports
import sync, feeds

__author__ = 'Jason Haury'

app = Flask(__name__)
api = Api(app)
# Logging shortcut
log = app.logger

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
        return sync.get_history(request.args.copy())



class Market(Resource):
    """ Resource to handle requests for market data
    """
    def get(self, symbol):
        """
        :return: JSON dict of dicts, with main keys being tickPrice, tickSize and optionComputation.
        """
        # TODO add query string params for other Contract
        '''
        parser = reqparse.RequestParser()
        parser.add_argument('rate', type=int, help='Rate to charge for this resource')
        args = parser.parse_args()
        '''
        return feeds.get_market_data(symbol)


class Order(Resource):
    """ Resource to handle requests for Order
    """

    def get(self):
        """ Retrieves details of open orders using reqAllOpenOrders()
        """
        return sync.get_open_orders()

    def post(self):
        """ Places an order with placeOrder().  This requires enough args to create a Contract & and Order:
        https://www.interactivebrokers.com/en/software/api/apiguide/java/java_socketclient_properties.htm
        """
        parser = reqparse.RequestParser()
        # Contract args https://www.interactivebrokers.com/en/software/api/apiguide/java/contract.htm
        parser.add_argument('orderType', type=str, required=True,
                            help='Type of Order to place', choices=['LMT', 'MTL', 'MKT PRT', 'QUOTE', 'STP', 'STP LMT',
                                                                    'TRAIL LIT', 'TRAIL MIT', 'TRAIL', 'TRAIL LIMIT',
                                                                    'MKT', 'MIT', 'MOC', 'MOO', 'PEG MKT', 'REL',
                                                                    'BOX TOP', 'LOC', 'LOO', 'LIT', 'PEG MID', 'VWAP',
                                                                    'GAT', 'GTD', 'GTC', 'IOC', 'OCA', 'VOL'])
        parser.add_argument('secType', type=str, required=False, default='STK',
                            help='Security Type', choices=['STK', 'OPT', 'FUT', 'IND', 'FOP', 'CASH', 'BAG', 'NEWS'])
        parser.add_argument('exchange', type=str, required=False, default='SMART',
                            help='Exchange (ie NASDAQ, SMART)')
        parser.add_argument('currency', type=str, required=False, default='USD',
                            help='Currency used for order (ie USD, GBP))')
        parser.add_argument('symbol', type=str, required=True,
                            help='Stock ticker symbol to order')

        # Order args https://www.interactivebrokers.com/en/software/api/apiguide/java/order.htm
        # Order types https://www.interactivebrokers.com/en/software/api/apiguide/tables/supported_order_types.htm
        parser.add_argument('totalQuantity', type=int, required=True,
                            help='Total Quantity to order')
        parser.add_argument('action', type=str, required=True,
                            help='Must be BUY, SELL or SSHORT')
        parser.add_argument('tif', type=str, required=False,
                            help='Time in force', choices=['DAT', 'GTC', 'IOC', 'GTD'])

        '''
        parser.add_argument('stopPrice', type=int, required=True,
                            help='Stop price (will always sell if lower than this price)')
        parser.add_argument('trailingPercent', type=float,
                            help='Precentage loss to accept for Trailing Stop Loss order')
        '''
        args = parser.parse_args()
        all_args = request.args.copy()
        for k, v in args.iteritems():
            all_args[k] = v
        print all_args
        return sync.place_order(args)

    def delete(self):
        """ Cancels order with cancelOrder()
        """
        parser = reqparse.RequestParser()
        parser.add_argument('orderId', type=int, required=True,
                            help='Order ID to cancel')
        args = parser.parse_args()
        return sync.cancel_order(args['orderId'])


class PortfolioPositions(Resource):
    """ Resource to handle requests for market data
    """

    def get(self):
        """
        :return: JSON dict of dicts, with main keys being tickPrice, tickSize and optionComputation.
        """
        return sync.get_portfolio_positions()


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
        parser.add_argument('tags', type=str, help='CSV list of tags from this set: {}'.format(choices), trim=True,
                            default='')
        parser.add_argument('tag', type=str, action='append', help='Account information you want to see: {error_msg}',
                            trim=True, choices=choices, default=[])
        args = parser.parse_args()
        # Make a master list of tags from all possible arguments
        tags = args['tag'] + args['tags'].split(',')
        if len(tags) == 0:
            # No tags were passed, so throw an error
            return dict(message=dict(tags='Must provide 1 or more `tag` args, and/or a CSV `tags` arg'))
        # Reduce and re-validate
        tags = set(tags)
        if not tags.issubset(choices):
            return dict(message=dict(tags='All tags must be from this set: {}'.format(choices)))
        # re-create CSV list
        tags = ','.join(list(tags))
        log.debug('TAGS: {}'.format(tags))
        return sync.get_account_summary(tags)


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
        return sync.get_account_update(args['acctCode'])

# ---------------------------------------------------------------------
# ROUTING
# ---------------------------------------------------------------------
api.add_resource(History, '/history')
api.add_resource(Market, '/market/<string:symbol>')
api.add_resource(Order, '/order')
api.add_resource(PortfolioPositions, '/account/positions')
api.add_resource(AccountSummary, '/account/summary')
api.add_resource(AccountUpdate, '/account/update')

if __name__ == '__main__':
    import os
    host = os.getenv('IBREST_HOST', '127.0.0.1')
    port = int(os.getenv('IBREST_PORT', '5000'))
    app.run(debug=True, host=host, port=port)

