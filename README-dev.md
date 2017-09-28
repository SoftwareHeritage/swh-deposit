# Develop on swh-deposit

There are multiple modes to run and test the server locally:
- development-like (automatic reloading when code changes)
- production-like (no reloading)
- integration tests (no side effects)

Except for the tests which are mostly side effects free (except for
the database access), the other modes will need some configuration
files (up to 2) to run properly.

## Development-like environment

Development-like environment needs one configuration file to work
properly.

### Configuration

**`{/etc/softwareheritage | ~/.config/swh | ~/.swh}`/deposit/server.yml**:

``` YAML
# dev option for running the server locally
host: 127.0.0.1
port: 5006

# production
authentication:
  activated: true
  white-list:
    GET:
      - /

# 20 Mib max size
max_upload_size: 20971520

# flags for the service document endpoint
verbose: false
noop: false

# access to the objstorage for storing uploaded archive
objstorage:
  cls: pathslicing
  args:
    root: /home/storage/swh-deposit/uploads
    slicing: 0:1/1:5
```

### Run

Run the local server, using the default configuration file:

``` Shell
make run-dev
```

## Production-like environment

Production-like environment needs two configuration files to work
properly.

This is more close to what's actually running in production.

### Configuration

This expects the same file describes in the previous chapter.  Plus,
an additional private **settings.yml** file containing secret
information that is not in the source code repository.

**`{/etc/softwareheritage | ~/.config/swh | ~/.swh}`/deposit/private.yml**:

``` YAML
secret_key: production-local
db:
  name: swh-deposit-dev
```

A production configuration file would look like:

``` YAML
secret_key: production-secret-key
db:
  name: swh-deposit-dev
  host: db
  port: 5467
  user: user
  password: user-password
```

### Run

``` Shell
make run
```

Note: This expects gunicorn3 package installed on the system

## Tests

To run the tests:
``` Shell
make test
```

As explained, those tests are mostly side-effect free.  The db part is
dealt with by django. The remaining part which patches those
side-effect behavior is dealt with in the
`swh/deposit/tests/__init__.py` module.
