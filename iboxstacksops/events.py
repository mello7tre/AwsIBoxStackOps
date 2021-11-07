from calendar import timegm
from .common import *


# show old and new service tasks during an update
def _show_service_update(istack, event, timedelta):
    # avoid showing current service log if is requested a stack past event
    if timedelta != "0":
        return

    service_logical_resource_id = event.logical_resource_id
    service = task = cluster = deps_before = None
    deployment_task = ""
    deployments_len = pendingCount = 0
    client = istack.boto3.client("ecs")

    try:
        cluster = istack.stack.Resource("ScalableTarget").physical_resource_id.split(
            "/"
        )[1]
        service = istack.stack.Resource(
            service_logical_resource_id
        ).physical_resource_id
    except Exception:
        return

    deps = {
        "PRIMARY": {},
        "ACTIVE": {},
    }
    while task != deployment_task or deployments_len > 1 or pendingCount != 0:
        istack.stack.reload()
        task = istack.stack.Resource("TaskDefinition").physical_resource_id
        response = client.describe_services(
            cluster=cluster,
            services=[service],
        )
        deployments = response["services"][0]["deployments"]
        deployments_len = len(deployments)
        for dep in deployments:
            status = dep["status"]
            for p in [
                "taskDefinition",
                "desiredCount",
                "runningCount",
                "pendingCount",
                "failedTasks",
            ]:
                deps[status][p] = dep[p]

        deployment_task = deps["PRIMARY"]["taskDefinition"]
        desiredCount = deps["PRIMARY"]["desiredCount"]
        runningCount = deps["PRIMARY"]["runningCount"]
        pendingCount = deps["PRIMARY"]["pendingCount"]
        failedTasks = deps["PRIMARY"]["failedTasks"]

        if str(deps) != deps_before:
            deps_before = str(deps)
            for d in ["PRIMARY", "ACTIVE"]:
                if "taskDefinition" in deps[d]:
                    deps[d]["taskDefinition"] = deps[d]["taskDefinition"].split("/")[-1]
            istack.mylog("PRIMARY: %s" % pformat(deps["PRIMARY"], width=1000000))
            istack.mylog("ACTIVE: %s\n" % pformat(deps["ACTIVE"], width=1000000))

            # is update stuck ?
            max_retry = istack.cfg.max_retry_ecs_service_running_count
            if max_retry > 0 and failedTasks >= max_retry:
                istack.last_event_timestamp = event.timestamp
                raise IboxErrorECSService(
                    "ECS Service did not stabilize "
                    f"[{failedTasks} >= {max_retry}] - "
                    "cancelling update [ROLLBACK]"
                )

        time.sleep(5)


# get timestamp from last event available
def get_last_timestamp(istack):
    last_event = list(istack.stack.events.all().limit(1))[0]

    return last_event.timestamp


# show all events after specific timestamp and return last event timestamp
def show(istack, timestamp, timedelta="0"):
    event_iterator = istack.stack.events.all()
    event_list = []
    for event in event_iterator:
        if event.timestamp > timestamp:
            event_list.insert(0, event)
        else:
            break
    for event in event_list:
        logtime = timegm(event.timestamp.timetuple())
        istack.mylog(
            event.logical_resource_id
            + " "
            + event.resource_status
            + " "
            + str(datetime.fromtimestamp(logtime))
            + " "
            + str(event.resource_status_reason)
        )
        if (
            event.resource_type == "AWS::ECS::Service"
            and event.resource_status == "UPDATE_IN_PROGRESS"
            and event.resource_status_reason is None
            and istack.stack.stack_status not in istack.cfg.STACK_COMPLETE_STATUS
        ):
            _show_service_update(istack, event, timedelta)

    if len(event_list) > 0:
        return event_list.pop().timestamp

    return timestamp
