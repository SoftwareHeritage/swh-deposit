#!/usr/bin/env python3

# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

import click
import os


AUTHORIZED_PLATFORMS = ['development', 'production']


@click.command(
    help='Create a user with some needed information (password, collection)')
@click.option('--platform', default='development',
              help='development or production platform')
@click.option('--username', required=True, help="User's name")
@click.option('--password', required=True, help="Desired user's password.")
@click.option('--firstname', default='', help="User's first name")
@click.option('--lastname', default='', help="User's last name")
@click.option('--email', default='', help="User's email")
@click.option('--collection', help="User's collection")
def main(platform, username, password, firstname, lastname, email, collection):

    if platform not in AUTHORIZED_PLATFORMS:
        raise ValueError('Platform should either be one of %s' %
                         AUTHORIZED_PLATFORMS)

    # setup
    os.environ.setdefault("DJANGO_SETTINGS_MODULE",
                          "swh.deposit.settings.%s" % platform)
    import django
    django.setup()

    from swh.deposit.models import DepositClient, DepositCollection

    try:
        collection = DepositCollection.objects.get(name=collection)
    except DepositCollection.DoesNotExist:
        raise ValueError(
            'Collection %s does not exist, skipping' % collection)

    # user create/update
    try:
        user = DepositClient.objects.get(username=username)
        print('User %s exists, updating information.' % user)
        user.set_password(password)
    except DepositClient.DoesNotExist:
        print('Create new user %s' % username)
        user = DepositClient.objects.create_user(
            username=username,
            password=password)

    user.collections = [collection.id]
    user.first_name = firstname
    user.last_name = lastname
    user.email = email
    user.is_active = True
    user.save()

    print('Information registered for user %s' % user)


if __name__ == '__main__':
    main()
