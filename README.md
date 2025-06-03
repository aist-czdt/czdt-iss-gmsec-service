# CZDT-ISS-GMSEC-SERVICE

This repo contains the integration between CZDT's ISS and CMSS and ISS and MAAP. 

Docker compose is used to coordinate the four services described below.

## Services

### Heartbeat
The `iss_hb` container will periodically publish an overall ISS status message to
CMSS. The heartbeat status is an aggregation of the three components of ISS:
`MAAP` for ingest status, `SDAP` for analysis status, and `Titiler` for OGC status.

### Directive Messages

The `iss_listener` container will await for `DIRECTIVE-REQUEST` messages from CMSS. The
requests can be one of `SUBMIT-JOB` or `JOB-STATUS`. The listener will then parse the request
message and interact with `MAAP` accordingly. In both request types, the listener will respond
via `DIRECTIVE-RESPONSE` messages containing a `JOB-ID` and a `JOB-STATUS`.

### Publisher

The `iss_publisher` container will send `LOG` and `PROD` messages to CMSS as needed. `LOG`
messages will consist of general ISS notifications deemed relevant to CZDT as a whole. `PROD`
messages will be sent to notify CZDT of the availability of new products. Both `LOG` and `PROD`
messages can be triggered via a wrapper API (see the API section for more details), meaning
at the culmination of a MAAP ingest job, the MAAP workflow can trigger the sending of a `PROD`
message.

### API

The `iss_api` container will receive requests from MAAP, or elsewhere within the ISS, and make use
of Docker networking to pass request data to the `iss_publisher` container for message 
construction and publishing. Currently supports `/health` for the health of the API, `/log` for
publishing `LOG` messages, and `/product` for `PROD` messages.

*EXAMPLE LOG MESSAGE JSON*
```
{
    "level":"INFO",
    "msg_body":"test log message"
}
```

*EXAMPLE PROD MESSAGE JSON*
```
{
    "collection":"MUR25-JPL-L4-GLOB-v04.2",
    "ogc":"http://titiler.url/stac/collections/gpw_v4/items", 
    "uris": [
        "s3://czdt-sdap-ard-zarr/gpw_v4/src/file1.zarr", 
        "s3://czdt-sdap-ard-zarr/gpw_v4/src/file2.zarr"
    ]
}
```

## Build

The `czdt/iss` image has multiple dependencies:

### External Dependencies
#### `message-spec` repo
Sibling to this repo (e.g. `../message-spec/`). It gets mounted to the container at runtime and contains the GMSEC message templates, etc. Requires SMCE / CZDT auth to access.
```bash
git clone https://git.smce.nasa.gov/czdt-dev/message-spec.git
```
#### `GMSEC_API` (GMSEC_API-5.2-Ubuntu20.04_x86_64.tar.gz) 
Installed during Docker build
#### `ActiveMQ` client library (activemq-cpp-3.9.5.tar.gz)
Installed during Docker build

### Auth files
#### `truststore.pem` 
Used for authentication to the CZDT messagebus. See `auth/truststore.example.pem`.
#### `.env` 
Contains MAAP API token. See `auth/example.env`.

### Config file
#### `config/config-prod.xml`
Needs `server` and various heartbeat URLs filled in. See `config/config-prod.example.xml`

```bash
docker compose up --build
```

Docker compose will build two images:
- `czdt/iss` for handling GMSEC integration
- `czdt/api` for handling ISS API

And stand up four containers from the two images:
- `iss_listener` for receiving and handling directive messages
- `iss_hb` for sending heartbeat messages
- `iss_publisher` for sending LOG and PRODUCT messages
- `iss_api` for accepting external requests from MAAP to trigger message sending in `iss_publisher`

## Development

1. Clone the repo

2. Run `dev.setup.sh`
```bash
chmod +x dev.setup.sh
./dev.setup.sh
```

3. (Optional) Add gmsec to IDE paths for import resolution. Example in VSCode `settings.json`:
```
{
    "python.analysis.extraPaths": [
        "./.venv/GMSEC_API/bin/lib/GMSECAPI5"
    ]
}
```

## Tests

There are two sets of sets: 
- FastAPI used in the `iss_api` container 
- gmsec_service logic

Tests can be run via `pytest`.
