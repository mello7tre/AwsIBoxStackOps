from prettytable import PrettyTable, ALL as ptALL
from . import cfg, i_stack
from .aws import myboto3
from .tools import concurrent_exec
from .log import logger
from .common import *


def _get_ssm_parameter(ssm, param):
    resp = ssm.get_parameter(Name=param)

    return resp['Parameter']['Value']


def get_setupped_regions(stack=None):
    boto3 = myboto3()
    ssm = boto3.client('ssm')
    
    try:
        rgs = _get_ssm_parameter(ssm, f'{cfg.SSM_BASE_PATH}/{stack}/regions')
    except Exception as e:
        rgs = _get_ssm_parameter(ssm, f'{cfg.SSM_BASE_PATH}/regions')

    return rgs.split()


def get_by_path(iregion, path):
    params = {}
    paginator = iregion.ssm.get_paginator('get_parameters_by_path')
    response_iterator = paginator.paginate(Path=path, Recursive=True)

    for page in response_iterator:
        for p in page['Parameters']:
            name = p['Name']
            name = '/'.join(name.split('/')[-2:])
            value = p['Value']

            params[name] = value

    return params


def put_parameter(iobj, param):
    resp = iobj.ssm.put_parameter(
        Name=param['name'], Description=param['desc'],
        Value=param['value'], Type='String',
        Overwrite=True, Tier='Standard')


def setup(iregion):
    param = {
        'name': f'{cfg.SSM_BASE_PATH}/regions',
        'desc': 'Regions where to replicate',
        'value': ' '.join(cfg.regions)
    }

    result = {}
    if len(iregion.bdata) == 0:
        put_parameter(iregion, param)
        result = cfg.regions
    else:
        stack_data = {}
        for n,_ in iregion.bdata.items():
            s_param = dict(param)
            s_param['name'] = f'{cfg.SSM_BASE_PATH}/{n}/regions'
            stack_data[n] = s_param
        
        result = concurrent_exec('ssm', stack_data, region=iregion.name)

    return result


def put(iregion):
    for p, v in vars(cfg.stack_parsed_args).items():
        if not v:
            continue
        stack_data = {}
        for n,_ in iregion.bdata.items():
            s_param = {
                'name': f'{cfg.SSM_BASE_PATH}/{n}/{p}',
                'desc': getattr(cfg, p).help,
                'value': v,
            }
            stack_data[n] = s_param

        result = concurrent_exec('ssm', stack_data, region=iregion.name)


def show(data):
    params_map = {}
    params_keys = []
    table = PrettyTable()
    table.padding_width = 1

    for r, v in data.items():
        params_map[r] = v
        params_keys.extend(list(v.keys()))

    params_keys = sorted(list(set(params_keys)))
    table.add_column('Parameter', params_keys)

    for r, v in params_map.items():
        params_values = []
        for n in params_keys:
            if n in v:
                params_values.append(v[n])
            else:
                params_values.append('')
        table.add_column(r, params_values)

    table.align['Parameter'] = 'l'
    
    return table


"""
def do_action_put():
    get_parameters_from_template()
    regions = get_setupped_regions()
    params = []

    for n, v in vars(istack.p_args).items():
        if not v:
            continue
        param = {}
        param['name'] = f'{cfg.SSM_BASE_PATH}/{fargs.stack}/{n}'
        param['desc'] = istack.parameters[n]['Description']
        param['value'] = v

        params.append(param)

    # check if is passed as param a list of regions
    # and use them, but only for regions that do alredy exist
    # in ssm regions parameter.
    if fargs.regions:
        rgs = []
        for r in fargs.regions:
            if r in regions:
                rgs.append(r)
        regions = rgs

    for r in regions:
        logger.info(f'Inserting SSM Parameters in {r}')
        set_region(r)
        for p in params:
            put_ssm_parameter(p)
"""



