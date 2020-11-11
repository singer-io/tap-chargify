# tap-chargify

This is a [Singer](https://singer.io) tap that produces JSON-formatted data
following the [Singer
spec](https://github.com/singer-io/getting-started/blob/master/SPEC.md).

This tap:

- Pulls raw data from the [Chargify API](https://reference.chargify.com/v1/basics/introduction)
- Extracts the following resources:
  - [Components](https://reference.chargify.com/v1/components/components-intro)
  - [Coupons](https://reference.chargify.com/v1/coupons-editing/coupons-intro)
  - [Customers](https://reference.chargify.com/v1/customers/customers-intro)
  - [Events](https://reference.chargify.com/v1/events/events-intro)
  - [Invoices](https://reference.chargify.com/v1/invoices-legacy/invoices)
  - [Price points](https://reference.chargify.com/v1/products-price-points/product-price-point-intro)
  - [Product families](https://reference.chargify.com/v1/product-families/product-family-intro)
  - [Products](https://reference.chargify.com/v1/products/products-intro)
  - [Statements](https://reference.chargify.com/v1/statements/statements-intro)
  - [Subscriptions](https://reference.chargify.com/v1/subscriptions/subscriptions-intro)
  - [Transactions](https://reference.chargify.com/v1/transactions/transactions-api)
- Outputs the schema for each resource
- Incrementally pulls data based on the input state

---

## Streams

### [components](https://reference.chargify.com/v1/components/list-components-for-a-product-family)

- **Endpoint**: https://reference.chargify.com/v1/components/list-components-for-a-product-family
- **Primary key field**: id
- **Replication strategy**: FULL_TABLE

### [coupons](https://reference.chargify.com/v1/coupons-editing/list-product-family-coupons)

- **Endpoint**: https://reference.chargify.com/v1/coupons-editing/list-product-family-coupons
- **Primary key field**: id
- **Replication strategy**: FULL_TABLE

### [customers](https://reference.chargify.com/v1/customers/list-customers-for-a-site)

- **Endpoint**: https://reference.chargify.com/v1/customers/list-customers-for-a-site
- **Primary key field**: id
- **Replication strategy**: FULL_TABLE

### [events](https://reference.chargify.com/v1/events/list-events-for-a-site)

- **Endpoint**: https://reference.chargify.com/v1/events/list-events-for-a-site
- **Primary key field**: id
- **Replication strategy**: FULL_TABLE

### [invoices](https://reference.chargify.com/v1/invoices-legacy/list-all-invoices-by-subscription)

- **Endpoint**: https://reference.chargify.com/v1/invoices-legacy/list-all-invoices-by-subscription
- **Primary key field**: id
- **Replication strategy**: INCREMENTAL
- **Bookmark**: due_date

### [price_points](https://reference.chargify.com/v1/products-price-points/read-product-price-points)

- **Endpoint**: https://reference.chargify.com/v1/products-price-points/read-product-price-points
- **Primary key field**: id
- **Replication strategy**: FULL_TABLE

### [product_families](https://reference.chargify.com/v1/product-families/list-product-family-via-site)

- **Endpoint**: https://reference.chargify.com/v1/product-families/list-product-family-via-site
- **Primary key field**: id
- **Replication strategy**: FULL_TABLE

### [products](https://reference.chargify.com/v1/products/list-products)

- **Endpoint**: https://reference.chargify.com/v1/products/list-products
- **Primary key field**: id
- **Replication strategy**: FULL_TABLE

### [statements](https://reference.chargify.com/v1/statements/list-statements-for-a-site)

- **Endpoint**: https://reference.chargify.com/v1/statements/list-statements-for-a-site
- **Primary key field**: id
- **Replication strategy**: FULL_TABLE

### [subscriptions](https://reference.chargify.com/v1/subscriptions/list-subscriptions)

- **Endpoint**: https://reference.chargify.com/v1/subscriptions/list-subscriptions
- **Primary key field**: id
- **Replication strategy**: FULL_TABLE

### [transactions](https://reference.chargify.com/v1/transactions/list-transactions-for-the-site)

- **Endpoint**: https://reference.chargify.com/v1/transactions/list-transactions-for-the-site
- **Primary key field**: id
- **Replication strategy**: INCREMENTAL
- **Bookmark**: created_at

--- 

## Quick Start

1. Install the tap using the following command:

   ```
   > pip install tap-chargify
   ```

2. Create the config file, which is a JSON file named `config.json`. This file should contain the following properties:
   
   - `api_key` - A Chargify API key. Refer to the [Chargify documentation](https://help.chargify.com/integrations/api-keys-chargify-direct.html) for instructions on creating an API key.
   - `start_date` - The date from which the tap should begin replicating data. This value must be an ISO 8601-compliant date.
   - `subdomain` The subdomain of your Chargify site. For example: If the full URL were `https://test.my-chargify-site.com`, this value would be `test`.

   ```json
   {
     "api_key": "xx",
     "start_date": "2018-02-22T02:06:58.147Z",
     "subdomain": "test"
   }
   ```

3. Run the tap in Discovery Mode using the following command:

   ```
   > tap-chargify -c config.json -d
   ```

   See the Singer docs on discovery mode
   [here](https://github.com/singer-io/getting-started/blob/master/docs/DISCOVERY_MODE.md#discovery-mode).

4. Run the tap in Sync Mode using the following command:

   ```
   > tap-chargify -c config.json --catalog catalog-file.json
   ```

## Development

1. Clone this repository. 
2. In the directory, run the following command:

   ```
   > python -m venv tap-chargify
   > make dev
   ```

---

Copyright &copy; 2019 Stitch
