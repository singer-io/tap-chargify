# Changelog

## 0.0.10
  * Updates schema for subscriptions and changes replication_key [#16](https://github.com/singer-io/tap-chargify/pull/16)

## 0.0.9
 * Fix schema for invoices [#14](https://github.com/singer-io/tap-chargify/pull/14)
 * Yield the price_point object instead of the object that contains price_point [#14](https://github.com/singer-io/tap-chargify/pull/14)

## 0.0.8
 * Change some fields in `subscriptions.json` and `statements.json` to be strings instead of numbers [#12](https://github.com/singer-io/tap-chargify/pull/12)

## 0.0.7
 * Change pagesize from 200 to 100 [#10](https://github.com/singer-io/tap-chargify/pull/10)
 * Update transactions schema, `gateway_transaction_id` is a string [#10](https://github.com/singer-io/tap-chargify/pull/10)

## 0.0.6
 * Add pagination [#8](https://github.com/singer-io/tap-chargify/pull/8)

## 0.0.5
 * Fix schema for subscriptions [#6](https://github.com/singer-io/tap-chargify/pull/6)

## 0.0.4
 * Fixes statements stream bookmark [#4](https://github.com/singer-io/tap-chargify/pull/4)
 * Respects stream selection [#4](https://github.com/singer-io/tap-chargify/pull/4)
 * Fixes transactions and invoices bookmark parsing [#4](https://github.com/singer-io/tap-chargify/pull/4)

## 0.0.3
 * Remove schema_name from metadata generation [#2](https://github.com/singer-io/tap-chargify/pull/2)
