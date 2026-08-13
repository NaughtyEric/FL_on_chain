## Setup

Set up and test the client from the repository root:

```text
python -m venv .venv
.venv\\Scripts\\activate
python -m pip install -e ".[test]"
python -m pytest
```
### Server Setup

Set up and test it together with the client from the repository root (same venv and pytest run):

```text
python -m pytest
```

Launch a server when clients are expected to connect:

```text
python -m fl_server --server-address HOST:PORT --num-rounds N --min-available-clients K
```

Config may also come from the environment (`FL_SERVER_ADDRESS`, `FL_NUM_ROUNDS`, `FL_FRACTION_FIT`, `FL_FRACTION_EVALUATE`, `FL_MIN_AVAILABLE_CLIENTS`, `FL_MIN_FIT_CLIENTS`, `FL_MIN_EVALUATE_CLIENTS`). For TLS, configure `FL_CA_CERT`, `FL_SERVER_CERT`, and `FL_SERVER_KEY` together and validate them; they are passed to `start_server` as `certificates=(ca, cert, key)`. 