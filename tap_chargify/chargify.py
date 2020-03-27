
#
# Module dependencies.
#

import backoff
import json
import requests
import logging
from urllib.parse import urlencode
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
  # The `get` request.
  # 
  
  @backoff.on_exception(backoff.expo,
                        requests.exceptions.HTTPError,
                        on_backoff=retry_handler,
                        max_tries=10)
  def get(self, path, stream=True, **kwargs):
    uri = "{uri}{path}".format(uri=self.uri, path=path)
    has_more = True
    page = 1
    per_page = 100
    while has_more:
      params = {
        "page": page,
        "per_page": per_page
      }
      for key, value in kwargs.items():
        params[key] = value
      final_uri = uri + "?{params}".format(params=urlencode(params))

      logger.info("GET request to {final_uri}".format(final_uri=final_uri))
      response = requests.get(final_uri, stream=stream, auth=HTTPBasicAuth(self.api_key, 'x'))
      response.raise_for_status()

      page += 1
      if len(response.json()) < per_page:
        has_more = False

      yield response.json()

  # 
  # Methods to retrieve data per stream/resource.
  # 

  def customers(self, bookmark=None):
    for i in self.get("customers.json"):
      for j in i:
        yield j["customer"]


  def product_families(self, bookmark=None):
    for i in self.get("product_families.json"):
      for j in i:
        yield j["product_family"]


  def products(self, bookmark=None):
    for i in self.get("product_families.json"):
      for k in i:
        for j in self.get("product_families/{product_family_id}/products.json".format(product_family_id=k["product_family"]["id"])):
          for l in j:
            yield l["product"]


  def price_points(self, bookmark=None):
    for i in self.get("product_families.json"):
      for j in i:
        for k in self.get("product_families/{product_family_id}/products.json".format(product_family_id=j["product_family"]["id"])):
          for l in k:
            for o in self.get("products/{product_id}/price_points.json".format(product_id=l["product"]["id"])):
              for m in o["price_points"]:
                yield m


  def coupons(self, bookmark=None):
    for i in self.get("product_families.json"):
      for k in i:
        for j in self.get("product_families/{product_family_id}/coupons.json".format(product_family_id=k["product_family"]["id"])):
          for l in j:
            yield l["coupon"]


  def components(self, bookmark=None):
    for i in self.get("product_families.json"):
      for k in i:
        for j in self.get("product_families/{product_family_id}/components.json".format(product_family_id=k["product_family"]["id"])):
          for l in j:
            yield l["component"]



  def subscriptions(self, bookmark=None):
    for i in self.get("subscriptions.json", start_datetime=bookmark, date_field="updated_at", direction="asc"):
      for j in i:
        yield j["subscription"]


  def transactions(self, bookmark=None):
    since_date = utils.strptime_with_tz(bookmark).strftime('%Y-%m-%d')
    for i in self.get("transactions.json", since_date=since_date, direction="asc"):
      for j in i:
        yield j["transaction"]


  def statements(self, bookmark=None):
    settled_since = mktime(utils.strptime_with_tz(bookmark).timetuple())
    for i in self.get("statements.json", sort="settled_at", direction="asc", settled_since=settled_since):
      for j in i:
        yield j["statement"]


  def invoices(self, bookmark=None):
    start_date = utils.strptime_with_tz(bookmark).strftime('%Y-%m-%d')
    for i in self.get("invoices.json", start_date=start_date, direction="asc"):
      for j in i:
        yield j["invoice"]


  def events(self, bookmark=None):
    for i in self.get("events.json"):
      for j in i:
        yield j["event"]




