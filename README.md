# tap-chargify

This is a [Singer](https://singer.io) tap that produces JSON-formatted data
following the [Singer
spec](https://github.com/singer-io/getting-started/blob/master/SPEC.md).

This tap:

- Pulls raw data from [Chargify](https://chargify.com/developers/)
- Outputs the schema for each resource
- Incrementally pulls data based on the input state

## Quick Start

1. Install

```
$ pip install tap-chargify
```

2. Create the config file

   Create a JSON file called `config.json`. Its contents should look like:

```json
{
  "api_key": "xx",
  "start_date": "2018-02-22T02:06:58.147Z",
  "subdomain": "test"
}
```

4. Run the Tap in Discovery Mode

    tap-chargify -c config.json -d

   See the Singer docs on discovery mode
   [here](https://github.com/singer-io/getting-started/blob/master/docs/DISCOVERY_MODE.md#discovery-mode).

5. Run the Tap in Sync Mode

    tap-chargify -c config.json --catalog catalog-file.json

## Development

First, clone this repo. Then, in the directory:

```
$ python -m venv tap-chargify
$ make dev
```

---

Copyright &copy; 2019 Stitch
