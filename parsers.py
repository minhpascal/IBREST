""" Flask-RESTful request parsers which help enforce argument needs for IB types:
 * Order
 * Contract
"""
from flask_restful import reqparse

__author__ = 'Jason Haury'

# ---------------------------------------------------------------------
# ORDER PARSER
# ---------------------------------------------------------------------
# Contains all args used for Order objects:
# https://www.interactivebrokers.com/en/software/api/apiguide/java/order.htm
order_parser = reqparse.RequestParser()
# Order args https://www.interactivebrokers.com/en/software/api/apiguide/java/order.htm
# Order types https://www.interactivebrokers.com/en/software/api/apiguide/tables/supported_order_types.htm
order_parser.add_argument('totalQuantity', type=int, required=True,
                    help='Total Quantity to order')
order_parser.add_argument('action', type=str, required=True,
                    help='Must be BUY, SELL or SSHORT')
order_parser.add_argument('tif', type=str,
                    help='Time in force', choices=['DAT', 'GTC', 'IOC', 'GTD'])

order_parser.add_argument('stopPrice', type=int,
                    help='Stop price (will always sell if lower than this price)')
order_parser.add_argument('trailingPercent', type=float,
                    help='Precentage loss to accept for Trailing Stop Loss order')


# ---------------------------------------------------------------------
# CONTRACT PARSER
# ---------------------------------------------------------------------
# Contains all args used for Contract objects:
# https://www.interactivebrokers.com/en/software/api/apiguide/java/contract.htm
contract_parser = reqparse.RequestParser()
# clientId is handled by sync code
contract_parser.add_argument('orderType', type=str, required=True, help='Type of Order to place',
                             choices=['LMT', 'MTL', 'MKT PRT', 'QUOTE', 'STP', 'STP LMT', 'TRAIL LIT', 'TRAIL MIT',
                                      'TRAIL', 'TRAIL LIMIT', 'MKT', 'MIT', 'MOC', 'MOO', 'PEG MKT', 'REL', 'BOX TOP',
                                      'LOC', 'LOO', 'LIT', 'PEG MID', 'VWAP', 'GAT', 'GTD', 'GTC', 'IOC', 'OCA', 'VOL'])
contract_parser.add_argument('secType', type=str, required=False, default='STK', help='Security Type',
                             choices=['STK', 'OPT', 'FUT', 'IND', 'FOP', 'CASH', 'BAG', 'NEWS'])
contract_parser.add_argument('exchange', type=str, required=False, default='SMART', help='Exchange (ie NASDAQ, SMART)')
contract_parser.add_argument('currency', type=str, required=False, default='USD',
                             help='Currency used for order (ie USD, GBP))')
contract_parser.add_argument('symbol', type=str, required=True, help='Stock ticker symbol to order')
