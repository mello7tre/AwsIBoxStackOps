def set_changed(istack):
    istack.after["resources"] = get(istack)

    before = istack.before["resources"]
    after = istack.after["resources"]

    changed = {}
    for r, v in before.items():
        if r in after and v != after[r]:
            changed[r] = after[r]

    istack.changed["resources"] = changed


def get(istack, dash=None):
    resources = {}
    res_list = list(istack.cfg.RESOURCES_MAP.keys())

    paginator = istack.client.get_paginator("list_stack_resources")
    response_iterator = paginator.paginate(StackName=istack.name)

    for r in response_iterator:
        for res in r["StackResourceSummaries"]:
            res_lid = res["LogicalResourceId"]
            res_type = res["ResourceType"]
            res_pid = res.get("PhysicalResourceId", "null")

            if res_lid in res_list:
                if res_pid.startswith("arn"):
                    res_pid = res_pid.split(":", 5)[5]
                if res_lid in [
                    "ListenerHttpsExternalRules1",
                    "ListenerHttpsExternalRules2",
                    "ListenerHttpExternalRules1",
                    "ListenerHttpInternalRules1",
                ]:
                    res_pid = "/".join(res_pid.split("/")[1:4])
                if res_lid == "ScalableTarget":
                    res_pid = res_pid.split("/")[1]
                if res_lid in ["Service", "ServiceSpot"]:
                    res_pid_arr = res_pid.split("/")
                    if len(res_pid_arr) == 3:
                        res_pid = res_pid_arr[2]
                    else:
                        res_pid = res_pid_arr[1]
                if res_lid in [
                    "LoadBalancerApplicationExternal",
                    "LoadBalancerApplicationInternal",
                ]:
                    res_pid = "/".join(res_pid.split("/")[1:4])

                if dash and istack.cfg.RESOURCES_MAP[res_lid]:
                    res_lid = istack.cfg.RESOURCES_MAP[res_lid]

                resources[res_lid] = res_pid
            elif res_type in res_list:
                # If RESOURCES_MAP directly include AWS Resource Type,
                # used for AWS::ServiceDiscovery::Service
                if res_pid.startswith("arn"):
                    res_pid = res_pid.split(":", 5)[5]
                resources[res_lid] = res_pid

    return resources
