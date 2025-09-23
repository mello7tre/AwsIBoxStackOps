import time
from datetime import datetime
from pprint import pformat
from calendar import timegm
from copy import deepcopy

from . import IboxErrorECSService


# show old and new service tasks during an update
def _show_service_update(istack, event, timedelta):
    # avoid showing current service log if is requested a stack past event
    if timedelta != "0":
        return

    pri_task_def = deps_before = rolloutState = None
    deps_len = 0
    max_retry = istack.cfg.max_retry_ecs_service_running_count
    client = istack.boto3.client("ecs")

    # get the current Stack TaskDefinitions to be deployed
    stack_tasks_defs = [
        res.physical_resource_id
        for res in istack.stack.resource_summaries.all()
        if res.resource_type == "AWS::ECS::TaskDefinition"
    ]

    # get cluster and service from service arn
    try:
        cluster_name = event.physical_resource_id.split("/")[1]
        service_name = event.physical_resource_id.split("/")[2]
    except Exception:
        istack.mylog(
            f"Unable to retrieve Cluster and Service name from event Physical Resource ID: {event.physical_resource_id}\n"
            "skipping Service deployment logging."
        )
        return

    while (
        pri_task_def not in stack_tasks_defs
        or deps_len > 1
        or rolloutState == "IN_PROGRESS"
    ):
        deps = {
            "PRIMARY": {},
            "ACTIVE": {},
            "INACTIVE": {},
            "DRAINING": {},
        }

        service = client.describe_services(
            cluster=cluster_name,
            services=[service_name],
        )["services"][0]

        # dep_task_def = service["taskDefinition"]
        deployments = service["deployments"]
        deps_len = len(deployments)
        last_updatedAt = None

        # find out if service have Deployment Circuit Breaker RollBack enabled
        try:
            circuit_breaker_rollback = service["deploymentConfiguration"][
                "deploymentCircuitBreaker"
            ]["rollback"]
        except Exception:
            circuit_breaker_rollback = False

        for dep in deployments:
            status = dep["status"]
            dep_updatedAt = dep.get("updatedAt")
            if dep_updatedAt and (not last_updatedAt or dep_updatedAt > last_updatedAt):
                last_updatedAt = dep_updatedAt
            for p in [
                "taskDefinition",
                "desiredCount",
                "runningCount",
                "pendingCount",
                "failedTasks",
                "rolloutState",
            ]:
                deps[status][p] = dep.get(p)

        pri_task_def = deps["PRIMARY"]["taskDefinition"]
        failedTasks = deps["PRIMARY"]["failedTasks"]
        rolloutState = deps["PRIMARY"]["rolloutState"]

        if deps != deps_before:
            # deployment have changed process it

            # check for Deployment Circuit Breaker
            if (
                deps_before
                and pri_task_def != deps_before["PRIMARY"]["taskDefinition"]
                and deps_before["PRIMARY"]["failedTasks"] > 0
                and deps_before.get("ACTIVE")
            ):
                # PRIMARY taskDefinition have changed means that:ECS Deployment Circuit Breaker was triggered
                # put PRIAMRY taskDefinition, the previous one, in stack_tasks_defs to avoid loop
                istack.mylog(
                    "Deployment failed! ECS Deployment Circuit Breaker was triggered\n"
                )
                stack_tasks_defs.append(pri_task_def)

            if last_updatedAt:
                istack.mylog(last_updatedAt.strftime("%Y-%m-%d %X"))

            deps_before = deepcopy(deps)

            # log short version of taskDefinitions
            for d in ["PRIMARY", "ACTIVE", "DRAINING"]:
                if "taskDefinition" in deps[d]:
                    deps[d]["taskDefinition"] = deps[d]["taskDefinition"].split("/")[-1]

            istack.mylog("PRIMARY: %s" % pformat(deps["PRIMARY"], width=1000000))
            istack.mylog("ACTIVE: %s" % pformat(deps["ACTIVE"], width=1000000))
            istack.mylog("DRAINING: %s\n" % pformat(deps["DRAINING"], width=1000000))

            # is update stuck ? Do AutoRollback, but skip if ECS Deployment Circuit Breaker is enabled
            if (
                not circuit_breaker_rollback
                and max_retry > 0
                and pri_task_def in stack_tasks_defs
                and failedTasks >= max_retry
            ):
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
        # show service depoyment logging
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
