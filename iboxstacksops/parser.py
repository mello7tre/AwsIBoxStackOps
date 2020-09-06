import argparse
from . import cfg
from .commands import (create, update, delete, cancel_update, continue_update,
                       info, parameters, resolve, show_table, log, dash,
                       ssm_setup, ssm_put, ssm_show)


def set_create_parser(subparser, parents=[]):
    parser = subparser.add_parser('create',
                                  parents=parents,
                                  help='Create Stack')
    parser.set_defaults(func=create)

    parser.add_argument('--Env',
                        help='Environment to use',
                        type=str, required=True)
    parser.add_argument('--EnvRole',
                        help='Stack Role',
                        type=str, required=True)
    parser.add_argument('--EnvApp1Version',
                        help='App Version',
                        type=str, default='')


def set_update_parser(subparser, parents=[]):
    parser = subparser.add_parser('update',
                                  parents=parents,
                                  help='Update Stack')
    parser.set_defaults(func=update)
    # used by dashboard update
    parser.set_defaults(
        statistic='Average',
        statisticresponse='p95',
        debug=False,
        silent=True,
        vertical=False)

    parser.add_argument('-P', '--policy',
                        help='Policy during Stack Update',
                        type=str, choices=[
                            '*', 'Modify', 'Delete', 'Replace',
                            'Modify,Delete', 'Modify,Replace',
                            'Delete,Replace'])
    parser.add_argument('-n', '--nochangeset',
                        help='No ChangeSet',
                        required=False, action='store_true')
    parser.add_argument('--dryrun',
                        help='Show changeset and exit',
                        action='store_true')
    parser.add_argument('-T', '--showtags',
                        help='Show tags changes in changeset',
                        action='store_true')
    parser.add_argument('-D', '--dashboard',
                        help='Update CloudWatch DashBoard',
                        choices=[
                            'Always', 'OnChange', 'Generic', 'None'],
                        default='OnChange')
    parser.add_argument('--nodetails',
                        help='Do not show extra details in changeset',
                        action='store_true')


def set_dash_parser(subparser, parents=[]):
    parser = subparser.add_parser('dash',
                                  parents=parents,
                                  help='Create DashBoard for stacks')
    parser.set_defaults(func=dash)

    parser.add_argument(
        '--statistic',
        help='Statistic to use for metrics',
        choices=['Average', 'Maximum', 'Minimum'],
        default='Average'
    )
    parser.add_argument(
        '--statisticresponse',
        help='Statistic to use for response time metrics',
        choices=[
            'Average', 'p99', 'p95', 'p90',
            'p50', 'p10', 'Maximum', 'Minimum'],
        default='p95',
    )
    parser.add_argument('--debug', help='Show json Dash', action='store_true')
    parser.add_argument('--silent', help='Silent mode', action='store_true')
    parser.add_argument(
        '--vertical',
        help='Add vertical annotation at creation time, '
             'and optionally specify fill mode',
        nargs='?',
        choices=['before', 'after'],
        const=True,
        default=False,
    )


def set_show_parser(subparser, parents=[]):
    parser = subparser.add_parser('show',
                                  parents=parents,
                                  help='Show Stacks table')
    parser.set_defaults(func=show_table)
    parser.add_argument('-F', '--fields', nargs='+',
                        type=str, default=cfg.SHOW_TABLE_FIELDS)
    parser.add_argument('-O', '--output',
                        type=str, default='text',
                        choices=['text', 'html', 'bare'])


def set_ssm_parser(subparser, parents=[]):
    parser = subparser.add_parser(
        'ssm',
        parents=[],
        help='SSM Parameters override for Stack Replicator')

    regions_parser = argparse.ArgumentParser(add_help=False)
    regions_parser.add_argument('-R', '--regions',
                                help='Regions', type=str,
                                required=True, default=[], nargs='+')

    ssm_parser = parser.add_subparsers(title='SSM Command',
                                       required=True, dest='command_ssm')

    setup_parser = ssm_parser.add_parser(
        'setup', help='Setup Regions',
        parents=parents + [regions_parser])
    setup_parser.set_defaults(func=ssm_setup)

    put_parser = ssm_parser.add_parser(
        'put', help='Put Parameters',
        parents=parents + [regions_parser])
    put_parser.set_defaults(func=ssm_put)

    show_parser = ssm_parser.add_parser(
        'show', help='Show Regions Distribution',
        parents=parents)
    show_parser.set_defaults(func=ssm_show)


def get_template_parser(required=True):
    parser = argparse.ArgumentParser(add_help=False)

    group = parser.add_mutually_exclusive_group(required=required)
    group.add_argument('--template',
                       help='Template Location',
                       type=str)
    group.add_argument('-v', '--version',
                       help='Stack Env Version',
                       type=str)

    return parser


def get_stack_selection_parser():
    parser = argparse.ArgumentParser(add_help=False)

    parser.add_argument(
        '-s', '--stack', nargs='+',
        help='Stack Names space separated',
        type=str, default=[])
    parser.add_argument(
        '-r', '--role', nargs='+',
        help='Stack Roles space separated',
        type=str, default=[])
    parser.add_argument(
        '-t', '--type', nargs='+',
        help='Stack Types space separated - use ALL for any type',
        type=str, default=[])

    return parser


# parse main argumets
def get_parser():
    parser = argparse.ArgumentParser(
        description='Stacks Operations',
        epilog='Note: options for Stack Params must be put at the end!'
    )

    # common parser
    parser.add_argument(
        '--region',
        help='Region', type=str)
    parser.add_argument(
        '--compact',
        help='Display Stacks-Output in compact form',
        action='store_true')
    parser.add_argument(
        '-j', '--jobs',
        help='Max Concurrent jobs - default to number of stacks', type=int)
    parser.add_argument(
        '--pause',
        help='Pause for seconds between jobs - '
             '0 for interactive - valid only for jobs=1',
        type=int)

    # action parser
    action_parser = argparse.ArgumentParser(add_help=False)

    action_parser.add_argument('-y', '--answer_yes',
                               help='Answer YES (No Confirm)',
                               required=False, action='store_true')
    action_parser.add_argument('-w', '--nowait',
                               help='Do not Wait for action to end',
                               required=False, action='store_true')
    action_parser.add_argument('-c', '--slack_channel',
                               help='Slack Channel [_cf_deploy]', nargs='?',
                               const='_cf_deploy', default=False)

    # template parser
    template_parser_create = get_template_parser()
    template_parser_update = get_template_parser(required=False)

    # stack selection parser
    stack_selection_parser = get_stack_selection_parser()

    # stack single parser
    stack_single_parser = argparse.ArgumentParser(add_help=False)
    stack_single_parser.add_argument(
        '-s', '--stack', nargs=1,
        help='Stack Names space separated',
        required=True, type=str, default=[])
    # update create parser
    updcrt_parser = argparse.ArgumentParser(add_help=False)

    updcrt_parser.add_argument('--topics', nargs='+',
                               help='SNS Topics Arn for notification',
                               type=str, default=[])
    updcrt_parser.add_argument('-M', '--max_retry_ecs_service_running_count',
                               help='Max retry numbers when updating ECS '
                                    'service and runningCount is stuck to '
                                    'zero',
                               type=int, default=0)

    # command subparser
    command_subparser = parser.add_subparsers(
        help='Desired Command',
        required=True,
        dest='command')

    # create parser
    set_create_parser(
        command_subparser, [
            action_parser,
            template_parser_create,
            stack_single_parser,
            updcrt_parser,
        ])

    # update parser
    set_update_parser(
        command_subparser, [
            action_parser,
            template_parser_update,
            stack_selection_parser,
            updcrt_parser,
        ])

    # delete parser
    parser_delete = command_subparser.add_parser(
        'delete',
        parents=[
            action_parser,
            stack_single_parser],
        help='Delete Stack (WARNING)')
    parser_delete.set_defaults(func=delete)

    # cancel_update parser
    parser_cancel = command_subparser.add_parser(
        'cancel',
        parents=[
            action_parser,
            stack_selection_parser],
        help='Cancel Update Stack')
    parser_cancel.set_defaults(func=cancel_update)

    # continue_update parser
    parser_continue = command_subparser.add_parser(
        'continue',
        parents=[
            action_parser,
            stack_selection_parser],
        help='Continue Update RollBack')
    parser_continue.set_defaults(func=continue_update)
    parser_continue.add_argument(
        '--resources_to_skip', '-R',
        help='Resource to Skip',
        default=[], nargs='+')

    # info parser
    parser_info = command_subparser.add_parser(
        'info', parents=[stack_selection_parser],
        help='Show Stack Info')
    parser_info.set_defaults(func=info)

    # parameters parser
    parser_parameters = command_subparser.add_parser(
        'parameters', parents=[
            template_parser_update,
            stack_selection_parser],
        help='Show Available Stack Parameters')
    parser_parameters.set_defaults(func=parameters)

    # resolve parser
    parser_resolve = command_subparser.add_parser(
        'resolve', parents=[
            template_parser_update,
            stack_selection_parser],
        help='Resolve Stack template - output in yaml short format')
    parser_resolve.set_defaults(func=resolve)

    # log parser
    parser_log = command_subparser.add_parser(
        'log',
        parents=[
            stack_single_parser],
        help='Show Stack Log')
    parser_log.set_defaults(func=log)
    parser_log.add_argument(
        '-d', '--timedelta',
        help='How many seconds go back in time from stack last event - '
             'use 0 for realtime - if < 30 assume days', default=300)

    # dashboard parser
    set_dash_parser(
        command_subparser, [
            stack_selection_parser,
        ])

    # show parser
    set_show_parser(
        command_subparser, [
            stack_selection_parser,
        ])

    # ssm parser
    set_ssm_parser(
        command_subparser, [
            stack_selection_parser,
        ])

    return parser


def set_cfg(argv):
    parser = get_parser()
    args = parser.parse_known_args(argv)

    cfg.cmd_parsed_args = args[0]

    for n, v in vars(args[0]).items():
        setattr(cfg, n, v)

    cfg.stack_args = args[1]
