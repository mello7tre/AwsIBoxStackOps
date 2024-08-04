def set_changed(istack):
    istack.after["resources"] = get(istack)

    before = istack.before["resources"]
    after = istack.after["resources"]

    changed = {}
    for r, v in before.items():
        if r in after and v != after[r]:
            changed[r] = after[r]

    istack.changed["resources"] = changed


def get(istack, dash=False, rtypes=None):
    # todo manage dash or not
    resources = {}
    res_list = list(istack.cfg.RESOURCES_MAP.keys())

    paginator = istack.client.get_paginator("list_stack_resources")
    response_iterator = paginator.paginate(StackName=istack.name)

    for r in response_iterator:
        for res in r["StackResourceSummaries"]:
            res_lid = res["LogicalResourceId"]
            res_type = res["ResourceType"]
            res_pid = res.get("PhysicalResourceId")

            if rtypes and res_type not in rtypes:
                continue

            if res_type in res_list:
                # match on ResourceType
                conf = istack.cfg.RESOURCES_MAP[res_type]
                name = conf.get("Name")
                prefix = conf.get("Prefix")
                pid_eval = conf.get("PidEval")

                if dash:
                    if prefix:
                        for n in ["External", "Internal"]:
                            if n in res_lid:
                                name = f"{prefix}{n}"
                    if pid_eval:
                        res_pid = eval(pid_eval)

                    if res_lid in res_list:
                        # match on LogicalResourceId too
                        conf = istack.cfg.RESOURCES_MAP[res_lid]
                        name = conf.get("Name", res_lid)

                    if name:
                        res_lid = name
                    else:
                        # default name for CW metric
                        res_lid = res_type.split("::")[2] + "Name"

                resources[res_lid] = res_pid

    return resources
