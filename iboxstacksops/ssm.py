#!/usr/bin/env python3
SSM_PATH = '/ibox'


def get_args():
    parser = argparse.ArgumentParser(
        description='SSM Parameters override for Stack Replicator',
        epilog='Note: options for Stack Params must be put at the end!')

    # common args

    # subparser
    subparsers = parser.add_subparsers(help='Desired Action',
                                       dest='action', required=True)

    # setup parser
    parser_setup = subparsers.add_parser('setup',
                                         help='Setup Regions')

    parser_setup.add_argument('-r', '--regions',
                              help='Regions', type=str,
                              required=True, default=[], nargs='+')

    parser_setup.add_argument('-s', '--stack',
                              help='Stack Name', type=str)

    # putshow parser args - common to put and show
    parser_putshow = argparse.ArgumentParser(add_help=False)

    parser_putshow.add_argument('-s', '--stack',
                                help='Stack Name', required=True, type=str)

    # put parser
    parser_put = subparsers.add_parser('put',
                                       help='Put Parameters - '
                                            'leave empty for a list',
                                       parents=[parser_putshow])

    parser_put.add_argument('-r', '--regions',
                            help='Regions', type=str,
                            required=True, default=[], nargs='+')

    parser_put.add_argument('-R', '--EnvRole',
                            help='Stack Role', type=str,
                            required=True if fargs.version and
                            'EnvRole' not in istack.c_parameters else False)

    template_version_group = parser_put.add_mutually_exclusive_group(
        required=False if istack.stack else True)
    template_version_group.add_argument('-t', '--template',
                                        help='Template Location',
                                        type=str)
    if 'BucketAppRepository' in istack.exports:
        template_version_group.add_argument('-v', '--version',
                                            help='Stack Env Version',
                                            type=str)

    # show parser
    parser_show = subparsers.add_parser('show',
                                        help='Show Regions Distribution',
                                        parents=[parser_putshow])

    # args[0] contain know arguments args[1] the unkown remaining ones
    args = parser.parse_known_args()
    return args


def put_ssm_parameter(param):
    resp = ssm.put_parameter(Name=param['name'],
                             Description=param['desc'],
                             Value=param['value'],
                             Type='String',
                             Overwrite=True,
                             Tier='Standard')


def get_ssm_parameter(param):
    resp = ssm.get_parameter(Name=param)

    return resp['Parameter']['Value']


def get_ssm_parameters_by_path(path):
    params = {}
    paginator = ssm.get_paginator('get_parameters_by_path')
    response_iterator = paginator.paginate(Path=path)

    for page in response_iterator:
        for p in page['Parameters']:
            name = p['Name']
            name = name.split('/')[3]
            value = p['Value']

            params[name] = value

    return params


def set_region(region):
    global ssm

    kwarg_session = {}
    kwarg_session['region_name'] = region
    myboto3 = boto3.session.Session(**kwarg_session)
    ssm = myboto3.client('ssm')


def do_action_setup():
    param = {}
    if fargs.stack:
        param['name'] = f'{SSM_PATH}/{fargs.stack}/regions'
    else:
        param['name'] = f'{SSM_PATH}/regions'

    param['desc'] = 'Regions where to replicate'
    param['value'] = ' '.join(fargs.regions)

    for r in fargs.regions:
        set_region(r)
        put_ssm_parameter(param)


def get_setupped_regions():
    set_region(current_region)
    try:
        rgs = get_ssm_parameter(f'{SSM_PATH}/{fargs.stack}/regions')
    except Exception as e:
        rgs = get_ssm_parameter(f'{SSM_PATH}/regions')

    return rgs.split()


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


def do_action_show():
    regions = get_setupped_regions()
    params_map = {}
    params_keys = []
    first_column = None
    table = PrettyTable()
    table.padding_width = 1

    for r in regions:
        set_region(r)
        params_map[r] = get_ssm_parameters_by_path(
            f'{SSM_PATH}/{fargs.stack}')
        params_keys.extend(list(params_map[r].keys()))

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
    print(table)
