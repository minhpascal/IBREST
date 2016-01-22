# ibrest
REST API for use with [Interactive Brokers TWS and IB Gateway](https://www.interactivebrokers.com/en/index.php?f=5041&ns=T)

## Summary
By using [Flask-RESTful](http://flask-restful-cn.readthedocs.org/en/0.3.4/) (and therefore [Flask](http://flask.pocoo.org/)), a web-based API is created which then uses [IbPy](https://github.com/blampe/IbPy) to connect to an instance of TWS or IB Gateway, and interact with Interactive Brokers.  This documentation will generally use "TWS" to mean "TWS or IBGateway"

### Better Firewalling
The intent is for this API to run on the same machine with TWS so that TWS can be set to only allow connections from the local host.  This provides a nice security feature, and lets IP access then be controlled by more advanced firewall software (ie to allow wildcards or IP ranges to access this REST API and therefore the TWS instance it interfaces with). 

### Google App Engine
In particular, this new API layer between your algoritm code and the IbPy API code is intended for use on Google App Engine where an algoritm may be operating within the PaaS system, with TWS running on a VM (ie [Brokertron](http://www.brokertron.com/)).  TWS does not support wildcard IP address (which would be a security hole anyways), and GAE uses many IPs when making outbound connections from one's App (making it neigh impossible to list all possible IPs in TWS' whitelist).  However, this project will aim to stay generalized enough so that it can be used outside of GAE.  

## REST API
Each URI endpoint shall:
### Use [IbPyOptional](https://code.google.com/p/ibpy/wiki/IbPyOptional)
To keep code maximally pythonic, this code will rely maximally on the `ib.opt` module.
### Use [IB Java API](https://www.interactivebrokers.com/en/software/api/apiguide/java/java.htm) Names
To help a coder make use of documentation in other project, names will be kept consistent in REST endpoints and parameters according to this convention. For example: `/`
