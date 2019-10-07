
#
# Module dependencies.
#

import backoff
import json
import requests
import logging
from requests.auth import HTTPBasicAuth
from singer import utils
from datetime import datetime
from time import mktime


logger = logging.getLogger()


""" Simple wrapper for Chargify. """
class Chargify(object):

  def __init__(self, api_key, subdomain, start_date=None):
    self.api_key = api_key
    self.uri = "https://{subdomain}.chargify.com/".format(subdomain=subdomain)



  def retry_handler(details):
    logger.info("Received 429 -- sleeping for %s seconds",
                details['wait'])

  # 
  # The actual `get` request.
  # 
  
  @backoff.on_exception(backoff.expo,
                        requests.exceptions.HTTPError,
                        on_backoff=retry_handler,
                        max_tries=10)
  def _get(self, path, stream=True, **kwargs):
    uri = "{uri}{path}".format(uri=self.uri, path=path)
    logger.info("GET request to {uri}".format(uri=uri))
    response = requests.get(uri, stream=stream, auth=HTTPBasicAuth(self.api_key, 'x'))
    response.raise_for_status()
    return response

  #
  # The common `get` request.
  #
  
  def get(self, path, **kwargs):
    response = self._get(path, **kwargs)
    return response.json()

  # 
  # Methods to retrieve data per stream/resource.
  # 

  def customers(self, bookmark=None):
    res = self.get("customers.json")
    for i in res:
      yield i["customer"]


  def product_families(self, bookmark=None):
    res = self.get("product_families.json")
    for i in res:
      yield i["product_family"]


  def products(self, bookmark=None):
    res = self.get("product_families.json")
    for i in res:
      res_prod_families = self.get("product_families/{product_family_id}/products.json".format(product_family_id=i["product_family"]["id"]))
      for j in res_prod_families:
        yield j["product"]


  def price_points(self, bookmark=None):
    res = self.get("product_families.json")
    for i in res:
      res_prod_families = self.get("product_families/{product_family_id}/products.json".format(product_family_id=i["product_family"]["id"]))
      for j in res_prod_families:
        res_price_points = self.get("products/{product_id}/price_points.json".format(product_id=j["product"]["id"]))
        for k in res_price_points["price_points"]:
          yield k


  def coupons(self, bookmark=None):
    res = self.get("product_families.json")
    for i in res:
      res_prod_families = self.get("product_families/{product_family_id}/coupons.json".format(product_family_id=i["product_family"]["id"]))
      for j in res_prod_families:
        yield j["coupon"]


  def components(self, bookmark=None):
    res = self.get("product_families.json")
    for i in res:
      res_prod_families = self.get("product_families/{product_family_id}/components.json".format(product_family_id=i["product_family"]["id"]))
      for j in res_prod_families:
        yield j["component"]



  def subscriptions(self, bookmark=None):
    res = self.get("subscriptions.json?start_datetime={start_datetime}&date_field=updated_at".format(start_datetime=bookmark))
    for i in res:
      yield i["subscription"]


  def transactions(self, bookmark=None):
    since_date = utils.strftime(utils.strptime_with_tz(bookmark), '%Y-%m-%d')
    # Need to convert bookmark to date string.
    res = self.get("transactions.json?since_date={since_date}&direction=asc".format(since_date=since_date))
    for i in res:
      yield i["transaction"]


  def statements(self, bookmark=None):
    settled_since = mktime(utils.strptime_with_tz(bookmark).timetuple())
    res = self.get("statements.json?sort=settled_at&direction=asc&settled_since={settled_since}".format(settled_since=settled_since))
    for i in res:
      yield i["statement"]


  def invoices(self, bookmark=None):
    start_date = utils.strftime(utils.strptime_with_tz(bookmark), '%Y-%m-%d')
    res = self.get("invoices.json?start_date={start_date}&direction=asc".format(start_date=start_date))
    for i in res:
      yield i["invoice"]


  def events(self, bookmark=None):
    res = self.get("events.json")
    for i in res:
      yield i["event"]




