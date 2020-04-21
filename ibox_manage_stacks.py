#!/usr/bin/env python3
import json
import logging
import boto3 as base_boto3
import botocore
import argparse
import time
import os
import sys
import concurrent.futures
from pprint import pprint, pformat
from prettytable import PrettyTable, ALL as ptALL

try:
    import ibox_stackops
    have_stackops = True
except ImportError:
    have_stackops = None

logging.basicConfig()
logging.getLogger('botocore').setLevel('CRITICAL')
logger = logging.getLogger('ibox')
logger.setLevel(logging.INFO)

STACK_BASE_DATA = [
    'StackName',
    'Description',
    'StackStatus',
    'CreationTime',
    'LastUpdatedTime',
]

STACK_OUTPUT_DATA = [
    'Env',
    'EnvRole',
    'EnvStackVersion',
    'EnvApp1Version',
    'StackType',
    'UpdateMode',
]

TABLE_FIELDS = [
    'EnvStackVersion',
    'EnvRole',
    'StackName',
    'StackType',
    'UpdateMode',
    'EnvApp1Version',
    'LastUpdatedTime',
]


class IboxError(Exception):
    pass


def get_parser():
    parser = argparse.ArgumentParser(
        description='Manage multiple stack at once')
    parser.add_argument('--region',
                        help='Region', type=str)
    # action subparser
    action_subparser = parser.add_subparsers(help='Desired Action',
                                             dest='action', required=True)

    # common parser
    common_parser = argparse.ArgumentParser(add_help=False)
    common_parser.add_argument('-s', '--stack', nargs='+',
                               help='Stack Names space separated',
                               type=str, default=[])
    common_parser.add_argument('-r', '--role', nargs='+',
                               help='Stack Roles space separated',
                               type=str, default=[])
    common_parser.add_argument('-t', '--type', nargs='+',
                               help='Stack Types space separated - '
                                    'ALL to show all',
                               type=str, default=[])

    # show parser
    parser_show = action_subparser.add_parser('show',
                                              help='Show Stacks summary',
                                              parents=[common_parser])
    parser_show.add_argument('-F', '--fields', nargs='+',
                             type=str, default=TABLE_FIELDS)
    parser_show.add_argument('-O', '--output',
                             type=str, default='text',
                             choices=['text', 'html'])
    parser_show.add_argument('-S', '--show_names',
                             help='Show stack names and exit',
                             action='store_true')
    parser_show.add_argument('-R', '--show_roles',
                             help='Show stack roles and exit',
                             action='store_true')
    parser_show.add_argument('-T', '--show_types',
                             help='Show stack types and exit',
                             action='store_true')

    if have_stackops:
        # update parser
        parser_update = action_subparser.add_parser('update',
                                                    help='Update Stacks'
                                                         'using ibox_stackops',
                                                    parents=[common_parser])
        parser_update.add_argument('--dryrun',
                                   help='Show Command to be excuted',
                                   action='store_true')
        parser_update.add_argument('-j', '--jobs',
                                   help='Max Concurrent jobs', type=int)
        parser_update.add_argument('--pause',
                                   help='Pause for seconds between jobs - '
                                        '0 for interactive - '
                                        'valid only for jobs=1',
                                   type=int)

    return parser


def show_confirm():
    print('')
    answer = input('Enter [y] to continue or any other key to exit: ')
    if not answer or answer[0].lower() != 'y':
        return False
    else:
        return True


def run_stackops(stacks):
    global is_success
    jobs = args.jobs if args.jobs else len(stacks)

    data = {}
    with concurrent.futures.ProcessPoolExecutor(
            max_workers=jobs) as executor:
        future_to_stack = {
            executor.submit(do_stackops, s): s for s in stacks}
        for future in concurrent.futures.as_completed(future_to_stack):
            stack = future_to_stack[future]
            try:
                data[stack] = future.result()
            except Exception as exc:
                is_success = None
                print(f'{stack} generated an exception: {exc}')

    return data


def do_stackops(stack):
    parser = ibox_stackops.get_parser()
    args_list = []
    if args.region:
        args_list.extend(['-r', args.region])
    args_list += ['--stack', stack, args.action, '-n'] + myargs[1]

    stack_args = parser.parse_known_args(args_list)

    if args.dryrun:
        return args_list

    result = ibox_stackops.main(stack_args)

    return result


def try_to_get(stack, data, name):
    try:
        data[name] = str(stack[name])
    except:
        pass


def get_stack_output(olist):
    outputs = {}

    for n in olist:
        key = n['OutputKey']
        value = (n['OutputValue']
                 if 'OutputValue' in n else None)
        outputs[key] = value

    return outputs


def get_stackdata(stack):
    data = {}
    for d in STACK_BASE_DATA:
        try_to_get(stack, data, d)

    if 'Outputs' in stack:
        outputs = get_stack_output(stack['Outputs'])
        data.update(outputs)
        # for d in STACK_OUTPUT_DATA:
        #     try_to_get(outputs, data, d)

    # ugly fix
    try:
        data['LastUpdatedTime'] = data['LastUpdatedTime'][0:19]
    except:
        pass

    return data


def get_table(data):
    fields = args.fields
    table = PrettyTable()
    table.padding_width = 1
    table.field_names = fields
    for n in data:
        table.add_row(['None' if i not in n else n[i]
                      for i in fields])

    table.sortby = fields[0]
    table.reversesort = True
    table.align = 'l'

    if args.output == 'text':
        out_table = table.get_string(fields=fields)
    else:
        table.format = True
        out_table = table.get_html_string(fields=fields)

    return out_table


def get_data():
    data = []

    paginator = client.get_paginator('describe_stacks')
    response_iterator = paginator.paginate()
    for r in response_iterator:
        for s in r['Stacks']:
            stack_name = s['StackName']
            stack_data = {}
            stack_data = get_stackdata(s)
            stack_role = stack_data.get('EnvRole', None)
            stack_type = stack_data.get('StackType', None)
            if (stack_name in args.stack or
                    stack_role in args.role or
                    stack_type in args.type or
                    'ALL' in args.type):
                data.append(stack_data)

    return data


def do_action_show():
    data = get_data()
    if args.show_names or args.show_roles or args.show_types:
        names = []
        for d in data:
            try:
                if args.show_names:
                    name_type = d['StackName']
                elif args.show_roles:
                    name_type = d['EnvRole']
                else:
                    name_type = d['StackType']
                names.append(name_type)
            except:
                pass

        return ' '.join(names)

    table = get_table(data)

    return table


def do_action_update():
    data = get_data()
    stacks = []
    for d in data:
        stacks.append(d['StackName'])

    if args.jobs == 1:
        name = d['StackName']
        for s in stacks:
            stack_ops = do_stackops(s)
            logger.info(f'{name}: {stack_ops}')
            if args.pause == 0:
                if not show_confirm():
                    exit(0)
            elif args.pause and args.pause > 0:
                time.sleep(args.pause)
    else:
        stack_ops = run_stackops(stacks)
        logger.info(stack_ops)


# main program function
def run(args):
    global boto3
    global client
    global cloudformation

    # set region from parameter if exist
    kwarg_session = {}
    if args.region:
        kwarg_session['region_name'] = args.region
    boto3 = base_boto3.session.Session(**kwarg_session)

    # create boto3 client/resource
    # cloudformation = boto3.resource('cloudformation')
    client = boto3.client('cloudformation')

    if args.action == 'show':
        return do_action_show()
    if args.action == 'update':
        return do_action_update()

    return True


def main(myargs):
    global args

    args = myargs
    try:
        result = run(args)
        return result
    except IboxError as e:
        logging.error(e.args[0])


if __name__ == "__main__":
    global myargs

    parser = get_parser()
    # -get cmd args as argparse objects
    myargs = parser.parse_known_args(sys.argv[1:])
    result = main(myargs[0])
    if not result:
        exit(1)
    else:
        print(result)
