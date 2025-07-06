from pprint import pformat


def get_action_tags(istack, stack_tags):
    # cmd lines tags
    cmd_tags = {n.split("=")[0]: n.split("=")[1] for n in istack.cfg.tags}
    tags_cmd = {}
    tags_remove = {}

    # unchanged tags
    tags_default = {}

    # changed tags - same value as corresponding stack param
    tags_changed = {}

    # metadata tags - found inside template Metadata Section
    tags_metadata = {}

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

        # remove tags using cmd --tags with tag value REMOVE
        elif key in cmd_tags and cmd_tags[key] == "REMOVE":
            tags_remove[key] = "REMOVE"
            continue
        # keep current tag value
        else:
            value = current_value

            # tags value cannot be empty
            if len(value) == 0:
                value = "empty"

            tags_default[key] = value

        final_tags.append({"Key": key, "Value": value})

    final_tags_keys = [n["Key"] for n in final_tags]

    upsert_tags_cfg = [
        # Command line tags
        (cmd_tags, tags_cmd),
        # Metadata tags found inside template Metadata Section
        (istack.metadata.get("Tags", {}), tags_metadata),
    ]

    # Add or Update Tags
    for n in upsert_tags_cfg:
        for key, value in n[0].items():
            if key not in tags_remove:
                # Tag must not be removed
                tag = {"Key": key, "Value": value}
                if tag in final_tags:
                    # Tag already exist, skip it
                    pass
                elif key in final_tags_keys:
                    # Tag Key already exist but with different Value, update it
                    loc = final_tags_keys.index(key)
                    tags_changed[key] = "%s => %s" % (
                        final_tags[loc]["Value"],
                        value,
                    )
                    final_tags[loc] = tag
                    tags_default.pop(key, None)
                else:
                    # Tag Key do not exist, add/append it
                    final_tags.append(tag)
                    n[1][key] = value

    # Add LastUpdate Tag with current time
    # Currently disabled:
    # Some resource, like CloudFormation Distribution, take time to be updated.
    # Does it make sense to have a tag with LastUpdateTime even if resource properties are not changed at all ?
    # If a resource is created by CloudFormation i can simply look at Stack LastUpdateTime
    # to have the same information derived by tagging it (i know that with tagging is simpler to do this).
    # final_tags.append({"Key": "LastUpdate", "Value": str(datetime.now())})

    if tags_default:
        istack.mylog(
            "CURRENT - STACK TAGS\n%s\n" % pformat(tags_default, width=1000000)
        )
    if tags_changed:
        istack.mylog(
            "CHANGED - STACK TAGS\n%s\n" % pformat(tags_changed, width=1000000)
        )
    if tags_cmd:
        istack.mylog(
            "COMMAND LINE - STACK TAGS\n%s\n" % pformat(tags_cmd, width=1000000)
        )
    if tags_metadata:
        istack.mylog(
            "METADATA - STACK TAGS\n%s\n" % pformat(tags_metadata, width=1000000)
        )
    if tags_remove:
        istack.mylog("REMOVE - STACK TAGS\n%s\n" % pformat(tags_remove, width=1000000))

    return final_tags
