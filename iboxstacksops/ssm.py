from prettytable import PrettyTable, ALL as ptALL
from . import cfg, i_stack
from .aws import myboto3
from .tools import concurrent_exec
from .log import logger
from .common import *


def _get_ssm_parameter(ssm, param):
    resp = ssm.get_parameter(Name=param)

    return resp["Parameter"]["Value"]


def get_setupped_regions():
    boto3 = myboto3()
    ssm = boto3.client("ssm")

    try:
        rgs = _get_ssm_parameter(ssm, f"{cfg.SSM_BASE_PATH}/regions")
    except Exception:
        return []

    return rgs.split()


def get_by_path(iregion, path):
    stacks_list = tuple(iregion.bdata.keys())
    params = {}

    paginator = iregion.ssm.get_paginator("get_parameters_by_path")
    response_iterator = paginator.paginate(Path=path, Recursive=True)

    for page in response_iterator:
        for p in page["Parameters"]:
            name = p["Name"]
            name = "/".join(name.split("/")[-2:])
            value = p["Value"]

            if "ALL" in iregion.cfg.type or name.startswith(stacks_list):
                params[name] = value

    return params


def put_parameters(iobj, params):
    for p in params:
        resp = iobj.ssm.put_parameter(
            Name=p["name"],
            Description=p["desc"],
            Value=p["value"],
            Type="String",
            Overwrite=True,
            Tier="Standard",
        )


def setup(iregion):
    param = {
        "name": f"{cfg.SSM_BASE_PATH}/regions",
        "desc": "Regions where to replicate",
        "value": " ".join(cfg.regions),
    }

    result = {}
    if len(iregion.bdata) == 0:
        put_parameters(iregion, [param])
        result = cfg.regions
    else:
        stack_data = {}
        for n, _ in iregion.bdata.items():
            s_param = dict(param)
            s_param["name"] = f"{cfg.SSM_BASE_PATH}/{n}/regions"
            stack_data[n] = [s_param]

        result = concurrent_exec("ssm", stack_data, i_stack, region=iregion.name)

    return result


def put(iregion):
    stacks_data = {}
    for s, v in iregion.bdata.items():
        stack = s
        args = v[0]
        parameters = v[1]
        ssm_params = []
        for p, v in vars(args).items():
            if not v:
                continue
            s_param = {
                "name": f"{cfg.SSM_BASE_PATH}/{s}/{p}",
                "desc": parameters[p]["Description"],
                "value": v,
            }
            ssm_params.append(s_param)
        stacks_data[s] = ssm_params

    result = concurrent_exec("ssm", stacks_data, i_stack, region=iregion.name)

    return result


def show(data):
    params_map = {}
    params_keys = []
    table = PrettyTable()
    table.padding_width = 1

    for r, v in data.items():
        params_map[r] = v
        params_keys.extend(list(v.keys()))

    params_keys = sorted(list(set(params_keys)))
    table.add_column("Parameter", params_keys)

    for r, v in params_map.items():
        params_values = []
        for n in params_keys:
            if n in v:
                params_values.append(v[n])
            else:
                params_values.append("")
        table.add_column(r, params_values)

    table.align["Parameter"] = "l"

    return table
