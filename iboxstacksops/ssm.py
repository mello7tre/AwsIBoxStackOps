from prettytable import PrettyTable, ALL as ptALL
from . import cfg, istack
from .aws import myboto3
from .log import logger
from .common import *

SSM_PATH = '/ibox'


def _get_ssm_parameter(ssm, param):
    resp = ssm.get_parameter(Name=param)

    return resp['Parameter']['Value']


def get_setupped_regions(stack=None):
    boto3 = myboto3()
    ssm = boto3.client('ssm')
    
    try:
        rgs = _get_ssm_parameter(ssm, f'{SSM_PATH}/{stack}/regions')
    except Exception as e:
        rgs = _get_ssm_parameter(ssm, f'{SSM_PATH}/regions')

    return rgs.split()


def get_ssm_parameters_by_path(iregion, path):
    params = {}
    paginator = iregion.ssm.get_paginator('get_parameters_by_path')
    response_iterator = paginator.paginate(Path=path)

    for page in response_iterator:
        for p in page['Parameters']:
            name = p['Name']
            name = '/'.join(name.split('/')[-2:])
            value = p['Value']

            params[name] = value

    return params


def put_ssm_parameter(iobj, param):
    resp = iobj.ssm.put_parameter(
        Name=param['name'], Description=param['desc'],
        Value=param['value'], Type='String',
        Overwrite=True, Tier='Standard')

    #logger.info(f'{iregion.name} replicate in:\n{cfg.regions}')


def setup(iregion):
    param = {
        'name': f'{SSM_PATH}/regions',
        'desc': 'Regions where to replicate',
        'value': ' '.join(cfg.regions)
    }

    if len(iregion.bdata) == 0:
        put_ssm_parameter(iregion, param)
        resp = cfg.regions
    else:
        resp = {}
        for n,_ in iregion.bdata.items():
            param['name'] = f'{SSM_PATH}/{n}/regions'
            stack = istack.ibox_stack(n, {}, iregion.name)
            stack.ssm(put_ssm_parameter, param)
            resp[n] = cfg.regions

    return resp


def get(iregion):
    return get_ssm_parameters_by_path(iregion, SSM_PATH)


def show(data):
    params_map = {}
    params_keys = []
    first_column = None
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
        param['name'] = f'{SSM_PATH}/{fargs.stack}/{n}'
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



