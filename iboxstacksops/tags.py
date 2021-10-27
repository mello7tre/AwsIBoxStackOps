from .common import *


def get_action_tags(istack, stack_tags):
    # unchanged tags
    tags_default = {}

    # changed tags - same value as corresponding stack param
    tags_changed = {}
    final_tags = []

    for tag in stack_tags:
        key = tag["Key"]
        current_value = tag["Value"]

        # Skip LastUpdate and EnvApp1Version Tag
        if key in ["LastUpdate", "EnvApp1Version"]:
            continue

        # check if key exist as cfg param/attr too
        try:
            cfg_value = getattr(istack.cfg, key)
            in_cfg = True if cfg_value is not None else None
        except Exception:
            in_cfg = None

        # current value differ from cmd arg
        if in_cfg and current_value != cfg_value:
            value = cfg_value

            # tags value cannot be empty
            if len(value) == 0:
                value = "empty"

            tags_changed[key] = "%s => %s" % (current_value, value)

        # keep current tag value
        else:
            value = current_value

            # tags value cannot be empty
            if len(value) == 0:
                value = "empty"

            tags_default[key] = value

        final_tags.append({"Key": key, "Value": value})

    # Add LastUpdate Tag with current time
    # Currently disabled:
    # Some resource, like CloudFormation Distribution, take time to be updated.
    # Does it make sense to have a tag with LastUpdateTime even if resource properties are not changed at all ?
    # If a resource is created by CloudFormation i can simply look at Stack LastUpdateTime
    # to have the same information derived by tagging it (i know that with tagging is simpler to do this).
    # final_tags.append({"Key": "LastUpdate", "Value": str(datetime.now())})

    if len(tags_default) > 0:
        istack.mylog(
            "DEFAULT - STACK TAGS\n%s\n" % pformat(tags_default, width=1000000)
        )
    if len(tags_changed) > 0:
        istack.mylog(
            "CHANGED - STACK TAGS\n%s\n" % pformat(tags_changed, width=1000000)
        )

    return final_tags
