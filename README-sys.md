How to bootstrap swh-deposit in production
====================================================

Once the package is installed, we need to do a few things:

- prepare the db setup (existence, connection, etc...).

This is defined through the packaged `swh.deposit.settings.production`
module and the expected $SWH_CONFIG_PATH/deposit/private.yml.

This is all done at the puppet level (cf. puppet-environment/swh-site,
puppet-environment/swh-profile)

- migrate/bootstrap the db schema:

``` Shell
sudo django-admin migrate --settings=swh.deposit.settings.production
```

- load minimum defaults data:

``` Shell
sudo django-admin loaddata --settings=swh.deposit.settings.production deposit_data
```

This adds the minimal:
- deposit request type 'archive' and 'metadata'
- 'hal' collection

Note: swh.deposit.fixtures.deposit_data is packaged

- add a client:

``` Shell
python3 -m swh.deposit.create_user --platform production \
    --collection hal \
    --username hal \
    --password <to-define>
```

This adds a user 'hal' which can access the collection 'hal'.  The
password will be used for the authentication access to the deposit
api.

Note: This needs to be improved.
