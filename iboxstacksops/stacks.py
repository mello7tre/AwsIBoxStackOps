from . import cfg, parameters, outputs
from .aws import myboto3
from .log import logger
from .common import *


def get_base_data(stack, stackset=None):
    data = {
        "before": {},
        "after": {},
        "changed": {},
        "parameter_not_empty": [],
    }

    if stackset:
        data["TemplateBody"] = stack["TemplateBody"]
        data["Tags"] = stack["Tags"]
        data["StackSetId"] = stack["StackSetId"]

    stack_outputs = outputs.get(stack)

    data.update(stack_outputs)
    data["before"]["outputs"] = stack_outputs

    stack_parameters = parameters.get(stack)
    if stack_parameters:
        data["c_parameters"] = stack_parameters

        # add parameters too, this way i can show them using show command
        for n, v in data["c_parameters"].items():
            if (
                not n.startswith("Env")
                and n not in ["UpdateMode"]
                and v != ""
                and ",,," not in v
            ):
                data["parameter_not_empty"].append(n)
            if n not in data:
                data[n] = v

    return data


def _get_stack(r, data):
    for s in r["Stacks"]:
        stack_name = s["StackName"]
        stack_data = get_base_data(s)
        stack_role = stack_data.get("EnvRole", None)
        stack_type = stack_data.get("StackType", None)
        if (
            stack_name in cfg.stack
            or stack_role in cfg.role
            or any(t in cfg.type for t in (stack_type.split() if stack_type else []))
            or "ALL" in cfg.type
        ):
            data[stack_name] = stack_data


def _get_stackset(r, data):
    s = r["StackSet"]
    stack_name = s["StackSetName"]
    stack_data = get_base_data(s, stackset=True)
    stack_role = stack_data.get("EnvRole", None)
    stack_type = stack_data.get("StackType", None)
    if (
        stack_name in cfg.stack
        or stack_role in cfg.role
        or any(t in cfg.type for t in (stack_type.split() if stack_type else []))
        or "ALL" in cfg.type
    ):
        data[stack_name] = stack_data


def get(names=[], exit_if_empty=True, obj=None, stackset=None):
    if not obj:
        boto3 = myboto3()
        client = boto3.client("cloudformation")
    else:
        boto3 = getattr(obj, "boto3")
        client = boto3.client("cloudformation")

    logger.info("Getting Stacks Description")
    data = {}

    if not names:
        names = cfg.stack

    if stackset:
        response = client.describe_stack_set(StackSetName=cfg.stack[0])
        _get_stackset(response, data)
    elif not cfg.role and not cfg.type and len(names) < cfg.MAX_SINGLE_STACKS:
        for s in names:
            response = client.describe_stacks(StackName=s)
            _get_stack(response, data)
    else:
        paginator = client.get_paginator("describe_stacks")
        response_iterator = paginator.paginate()
        for r in response_iterator:
            _get_stack(r, data)

    if not data and exit_if_empty:
        logger.warning("No Stacks found!\n")
        exit(0)

    return data
