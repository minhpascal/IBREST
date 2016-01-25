# IBREST
REST API for use with [Interactive Brokers TWS and IB Gateway](https://www.interactivebrokers.com/en/index.php?f=5041&ns=T)

## Summary
By using [Flask-RESTful](http://flask-restful-cn.readthedocs.org/en/0.3.4/) (and therefore [Flask](http://flask.pocoo.org/)), a web-based API is created which then uses [IbPy](https://github.com/blampe/IbPy) to connect to an instance of TWS or IB Gateway, and interact with Interactive Brokers.  This documentation will generally use "TWS" to mean "TWS or IBGateway"

## Intents
### Better Firewalling
This API should run on the same machine with TWS so that TWS can be set to only allow connections from the local host.  This provides a nice security feature, and lets IP access then be controlled by more advanced firewall software (ie to allow wildcards or IP ranges to access this REST API and therefore the TWS instance it interfaces with). 

### Google App Engine
This API layer between your algorithm code and the IbPy API code is intended for use on Google App Engine where an algoritm may be operating within the GAE system, with TWS running on a Compute Engine VM (ie [Brokertron](http://www.brokertron.com/)).  TWS does not support wildcard IP address (which would be a security hole anyways), and GAE uses many IPs when making outbound connections from one's App (making it neigh impossible to list all possible IPs in TWS' whitelist).  However, this project will aim to stay generalized enough so that it can be used outside of GAE.  

For running flask as a Docker container, consider [this tutorial](http://containertutorials.com/docker-compose/flask-simple-app.html) or use this existing [docker-flask image](https://hub.docker.com/r/p0bailey/docker-flask/).

TODO: Consider using following GAE features:
1. [Logging messages to GAE logger](https://cloud.google.com/logging/docs/agent/installation)
2. [Storing IB messages to DataStore](https://cloud.google.com/datastore/docs/getstarted/start_python/)
3. [Using Task Queue to get requests from GAE](https://cloud.google.com/appengine/docs/java/taskqueue/rest/about_auth).  IB allows 8 `client_ids`, which will impose a limit of 8 "simultaneous" tasks at a time with IBREST, unless some kind of task queuing happens (ie [Celery](http://flask.pocoo.org/docs/0.10/patterns/celery/))
 
### Synchronous
The [IB API](https://www.interactivebrokers.com/en/software/api/api.htm) is designed to be _a_synchronous, which adds labor to writing code to interface with it.  As IB message exchanges are pretty fast (a couple seconds at most), it's within time margins for use with HTTP requests (~60sec timeouts).  Thus, the exposed RESTful API opens a user-friendly synchronous interface with IB.

### Pythonic
Use [IbPyOptional](https://code.google.com/p/ibpy/wiki/IbPyOptional) (`ib.opt` module) maximally. 

## REST API
As IBREST is built with IbPy, and IbPy is based on the IB Java API, then IBREST will aim to use maximally similar language as found in those APIs' documentation.  The Java API is broken into two main layers:
1. [EClientSocket](https://www.interactivebrokers.com/en/software/api/apiguide/java/java_eclientsocket_methods.htm) - the connection to TWS for sending messages to IB. 
2. [EWrapper](https://www.interactivebrokers.com/en/software/api/apiguide/java/java_ewrapper_methods.htm) - the message processing logic for messages returned by IB.  Some messages are streamed in at intervals (ie subscriptions) and will not be exposed as a REST URI.  Such are maked `Unexposed data feed` below. 

TODO: Consider creating an RSS feed endpoint for such "Unexposed data feed" data. 

**NOTE:** As noted in [Synchronous], TWS only allows 8 connections (client ID's 0-7, where 0 has some special privileges).  These client ID's are treated as a connection pool.   This means that if 9 orders are placed very quickly, 8 of them will begin execution right away, and 1 will have to wait until a connection is freed (max ~50 sec).  This can be a hazard if placing market orders or if expecting to place many orders per few seconds.  The intent is for only one web app to call this API, and thereby prevent pool exhaustion/TWS overload.  
    
All endpoints return JSON formatted data using keys and values consistent with IbPy and IB Java APIs (case sensitive).

### Endpoint Groups
The documentation for each of these layers contains these sections, after which IBREST will create endpoints groups when applicable:

IB Documentation | REST endpoint
---------------- | -------------
Connection and Server | NA: Handled by Flask configuration
Market Data | /market
Orders | /order
Account and Portfolio | /portfolio
Contract Details | NA: Part of orders responses (TODO: is it?)
Executions | NA: Part of /order responses 
Market Depth | NA: Unexposed data feed
News Bulletins | NA: Unexposed data feed
Financial Advisors | NA: Unexposed data feed
Historical Data | NA: Unexposed data feed
Market Scanners | NA: Unexposed data feed
Real Time Bars| NA: Unexposed data feed
Fundamental Data | NA: Unexposed data feed
Display Groups| NA: Unexposed data feed

 
### Endpoint Details
The endpoints of each implemented group is documented below.  
 
#### GET /market/{tickerId}
A GET request {tickerId}'s market data will generate a `reqMktData()` EClient call, then wait for all appropriate `tick*()` EWrapper messages to return (price, size, optionComputation, etc).  At that point, an EClient `cancelMktData` message will be sent to the server and an HTTP response will be returned.
 
#### GET /order
A GET request retrieves a details for all open orders via `reqAllOpenOrders`.

#### POST /order
A POST request will generate a `placeOrder()` EClient call, then wait for the order to be filled .

#### DELETE /order
A DELETE request will call `cancelOrder()`.

#### GET /portfolio/updates
A GET request to `/portfolio/updates` will use `reqAccountUpdates()` to return messages received from `updateAccountValue/AccountTime()` and `updatePortfolio` EWrapper messages, as triggered by `accountDownloadEnd()`.

#### GET /portfolio/summary
A GET request to `/portfolio/summary` will use `reqAccountSummary()` to return messages received from `updateSummary()` EWrapper message as triggered by `accountSummaryEnd()`.

#### GET /portfolio/positions
A GET request to `/portfolio/positions` will use `reqPostions()` to return messages received from `position()` EWrapper message as triggered by `positionEnd()`.