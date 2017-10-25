# Bootstrap swh-deposit on production

As usual, the debian packaged is created and uploaded to the swh
debian repository.  Once the package is installed, we need to do a few
things in regards to the database.

## Prepare the database setup (existence, connection, etc...).

This is defined through the packaged `swh.deposit.settings.production`
module and the expected **/etc/softwareheritage/deposit/private.yml**.

As usual, the expected configuration files are deployed through our
puppet manifest (cf. puppet-environment/swh-site,
puppet-environment/swh-role, puppet-environment/swh-profile)

## Migrate/bootstrap the db schema

``` Shell
sudo django-admin migrate --settings=swh.deposit.settings.production
```

## Load minimum defaults data

``` Shell
sudo django-admin loaddata --settings=swh.deposit.settings.production deposit_data
```

This adds the minimal:
- deposit request type 'archive' and 'metadata'
- 'hal' collection

Note: swh.deposit.fixtures.deposit_data is packaged

## Add client and collection

``` Shell
python3 -m swh.deposit.create_user --platform production \
    --collection <collection-name> \
    --username <client-name> \
    --password <to-define>
```

This adds a user `<client-name>` which can access the collection
`<collection-name>`.  The password will be used for the authentication
access to the deposit api.

Note: This creation procedure needs to be improved.
