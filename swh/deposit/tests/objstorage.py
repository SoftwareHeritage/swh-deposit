# Copyright (C) 2017  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information

from swh.objstorage.exc import ObjNotFoundError
from swh.objstorage import objstorage


class MockObjStorage(objstorage.ObjStorage):
    """Memory objstorage used as mock to simplify reading indexers' outputs.

    """
    state = {}

    def __init__(self, **args):
        pass

    def check_config(self, *, check_write):
        return True

    def __contains__(self, obj_id, *args, **kwargs):
        return obj_id in self.state

    def add(self, content, obj_id=None, check_presence=True, *args, **kwargs):
        if obj_id is None:
            obj_id = objstorage.compute_hash(content)

        if check_presence and obj_id in self:
            # If the object is already present, return immediately.
            return obj_id

        self.state[obj_id] = content

        return obj_id

    def get(self, obj_id, *args, **kwargs):
        if obj_id not in self:
            raise ObjNotFoundError(obj_id)

        return self.state[obj_id]

    def check(self, obj_id, *args, **kwargs):
        return True

    def delete(self, *args, **kwargs):
        return True
