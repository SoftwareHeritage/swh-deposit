swh-deposit
==============

There are 2 modes.

# Development like

## Configuration

In ~/.config/swh/deposit/server.yml

``` YAML
# dev option
host: 127.0.0.1
port: 5006

# production
authentication: true

# 20 Mib max size
max_upload_size: 20971520

verbose: false
noop: false

objstorage:
  cls: pathslicing
  args:
    root: /home/storage/swh-deposit/uploads
    slicing: 0:1/1:5
```

## Run

Run local server which will use the previous setup.

``` Shell
make run-dev
```

# Production-like

This will run locally a mode similar to that of production.

## Configuration

This expects the same file describes in the previous chapter.  Plus,
an additional private settings.yml file containing secret information
that is not in the source code repository.

In ~/.config/swh/deposit/private.yml, something like:

``` YAML
secret_key: production-local
db:
  name: swh-deposit-dev
```

## Run

``` Shell
make run
```

Note: This expects gunicorn3 package installed on the system.


## Tests

``` Shell
cd swh && python3 -m manage test
```