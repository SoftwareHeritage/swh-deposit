# Copyright (C) 2017-2018  The Software Heritage developers
# See the AUTHORS file at the top-level directory of this distribution
# License: GNU General Public License version 3, or any later version
# See top-level LICENSE file for more information


def convert_status_detail(status_detail):
    """Given a status_detail dict, transforms it into a human readable string.

    Dict has the following form (all first level keys are optional)::

      {
        'url': {
            'summary': "summary-string",
            'fields': [impacted-fields-list]
        },
        'metadata': [{
            'summary': "summary-string",
            'fields': [impacted-fields-list],
        }],
        'archive': [{
            'summary': "summary-string",
            'fields': [impacted-fields-list],
        }]
      }

    Args:
        status_detail (dict): The status detail dict with the syntax
                              mentioned

    Returns:
        the status detail as inlined string

    """
    if not status_detail:
        return None

    def _str_fields(data):
        fields = data.get("fields")
        if not fields:
            return ""
        return " (%s)" % ", ".join(map(str, fields))

    msg = []
    for key in ["metadata", "archive"]:
        _detail = status_detail.get(key)
        if _detail:
            for data in _detail:
                msg.append("- %s%s\n" % (data["summary"], _str_fields(data)))

    _detail = status_detail.get("url")
    if _detail:
        msg.append("- %s%s\n" % (_detail["summary"], _str_fields(_detail)))

    if not msg:
        return None
    return "".join(msg)
