import argparse
from . import cfg
from .commands import (
    create,
    update,
    delete,
    cancel_update,
    continue_update,
    rollback,
    info,
    parameters,
    resolve,
    show_table,
    log,
    dash,
    ssm_setup,
    ssm_put,
    ssm_show,
    r53,
    replicate,
    stackset,
)


def get_create_parser(subparser, parents=[]):
    parser = subparser.add_parser("create", parents=parents, help="Create Stack")
    parser.add_argument("--Env", help="Environment to use", type=str, required=True)
    parser.add_argument("--EnvRole", help="Stack Role", type=str, required=True)
    parser.add_argument("--EnvApp1Version", help="App Version", type=str, default="")

    return parser


def get_update_parser(subparser, parents=[]):
    parser = subparser.add_parser("update", parents=parents, help="Update Stack")
    parser.add_argument(
        "-P",
        "--policy",
        help="Policy during Stack Update",
        type=str,
        choices=[
            "*",
            "Modify",
            "Delete",
            "Replace",
            "Modify,Delete",
            "Modify,Replace",
            "Delete,Replace",
        ],
    )
    parser.add_argument(
        "-n", "--nochangeset", help="No ChangeSet", required=False, action="store_true"
    )
    parser.add_argument("--dryrun", help="Show changeset and exit", action="store_true")
    parser.add_argument(
        "-T", "--showtags", help="Show tags changes in changeset", action="store_true"
    )
    parser.add_argument(
        "-D",
        "--dashboard",
        help="Update CloudWatch DashBoard",
        choices=["Always", "OnChange", "Generic", "None"],
        default=cfg.dashboard,
    )
    parser.add_argument(
        "--nodetails",
        help="Do not show extra details in changeset",
        action="store_true",
    )

    return parser


def set_dash_parser(subparser, parents=[]):
    parser = subparser.add_parser(
        "dash", parents=parents, help="Create DashBoard for stacks"
    )
    parser.set_defaults(func=dash)

    parser.add_argument(
        "--statistic",
        help="Statistic to use for metrics",
        choices=["Average", "Maximum", "Minimum"],
        default="Average",
    )
    parser.add_argument(
        "--statisticresponse",
        help="Statistic to use for response time metrics",
        choices=["Average", "p99", "p95", "p90", "p50", "p10", "Maximum", "Minimum"],
        default="p95",
    )
    parser.add_argument("--debug", help="Show json Dash", action="store_true")
    parser.add_argument("--silent", help="Silent mode", action="store_true")
    parser.add_argument(
        "--vertical",
        help="Add vertical annotation at creation time, "
        "and optionally specify fill mode",
        nargs="?",
        choices=["before", "after"],
        const=True,
        default=False,
    )


def get_show_parser(subparser, parents=[]):
    parser = subparser.add_parser("show", parents=parents, help="Show Stacks table")

    parser.add_argument(
        "-F", "--fields", nargs="+", type=str, default=cfg.SHOW_TABLE_FIELDS
    )
    parser.add_argument(
        "-O", "--output", type=str, default="text", choices=["text", "html", "bare"]
    )

    return parser


def set_ssm_parser(subparser, parents=[]):
    parser = subparser.add_parser(
        "ssm", parents=[], help="SSM Parameters override for Stack Replicator"
    )

    ssm_parser = parser.add_subparsers(
        title="SSM Command", required=True, dest="command_ssm"
    )
    # setup
    setup_parser = ssm_parser.add_parser("setup", help="Setup Regions", parents=parents)
    setup_parser.set_defaults(func=ssm_setup, no_stacks=True)

    setup_parser.add_argument(
        "-R",
        "--regions",
        help="Regions",
        type=str,
        required=True,
        default=[],
        nargs="+",
    )
    # put
    put_parser = ssm_parser.add_parser("put", help="Put Parameters", parents=parents)
    put_parser.set_defaults(func=ssm_put)

    put_parser.add_argument(
        "-R", "--regions", help="Regions", type=str, default=[], nargs="+"
    )
    # show
    show_parser = ssm_parser.add_parser(
        "show", help="Show Regions Distribution", parents=parents
    )
    show_parser.set_defaults(func=ssm_show, all_stacks=True)


def set_stackset_parser(subparser, parents=[]):
    parser = subparser.add_parser("stackset", parents=[], help="StackSet operations")
    parser.set_defaults(func=stackset)

    stackset_parser = parser.add_subparsers(
        title="Stackset Commands", required=True, dest="command_stackset"
    )

    # update parser
    parser_update = stackset_parser.add_parser(
        "update",
        parents=parents
        + [
            get_stackset_single_parser(),
            get_template_parser(required=False),
        ],
    )

    # info parser
    parser_info = stackset_parser.add_parser(
        "info",
        parents=[
            get_stackset_single_parser(),
            get_template_parser(required=False),
        ],
    )

    # parameters parser
    parser_parameters = stackset_parser.add_parser(
        "parameters",
        parents=[
            get_stackset_single_parser(),
            get_template_parser(required=False),
        ],
    )

    # show parser
    parser_show = get_show_parser(
        stackset_parser,
        [
            get_stackset_single_parser(),
        ],
    )

    # instances parser
    parser_instances = stackset_parser.add_parser(
        "instances",
        parents=[
            get_stackset_single_parser(),
            get_template_parser(required=False),
        ],
    )


def set_replicate_parser(subparser, parents=[]):
    parser = subparser.add_parser(
        "replicate", parents=[], help="Replicate in Regions configured by SSM"
    )
    parser.set_defaults(func=replicate)

    replicate_parser = parser.add_subparsers(
        title="Replicate Command", required=True, dest="command_replicate"
    )

    regions_parser = argparse.ArgumentParser(add_help=False)
    regions_parser.add_argument(
        "-R", "--regions", help="Regions", type=str, default=[], nargs="+"
    )
    regions_parser.add_argument(
        "--no_replicate_current",
        help="No replication in current Region",
        action="store_true",
    )

    # replicate create
    parser_create = get_create_parser(
        replicate_parser,
        parents
        + [
            get_template_parser(),
            get_stack_single_parser(),
            get_create_update_parser(),
            regions_parser,
        ],
    )

    # replicate update
    parser_update = get_update_parser(
        replicate_parser,
        parents
        + [
            get_template_parser(required=False),
            get_stack_selection_parser(),
            get_create_update_parser(),
            regions_parser,
        ],
    )

    # replicate delete
    parser_delete = replicate_parser.add_parser(
        "delete",
        parents=parents + [get_stack_single_parser(), regions_parser],
        help="Delete Stack (WARNING)",
    )

    # replicate show
    parser_show = get_show_parser(
        replicate_parser, [get_stack_selection_parser(), regions_parser]
    )


def set_r53_parser(subparser, parents=[]):
    parser = subparser.add_parser(
        "r53",
        parents=parents,
        help="Create RecordSet Aliases looking at stack R53 resources",
    )
    parser.set_defaults(func=r53)

    parser.add_argument("--dryrun", help="Show changes and exit", action="store_true")
    parser.add_argument(
        "--noorigin", help="Do not create Origin Record", action="store_true"
    )
    parser.add_argument(
        "--suffix",
        help='Suffix to add to RecordSet Name, prepended with "-"',
        default="",
        type=str,
    )


def get_template_parser(required=True):
    parser = argparse.ArgumentParser(add_help=False)

    group = parser.add_mutually_exclusive_group(required=required)
    group.add_argument("--template", help="Template Location", type=str)
    group.add_argument("-v", "--version", help="Stack Env Version", type=str)

    return parser


def get_stack_selection_parser():
    parser = argparse.ArgumentParser(add_help=False)

    parser.add_argument(
        "-s",
        "--stack",
        nargs="+",
        help="Stack Names space separated",
        type=str,
        default=[],
    )
    parser.add_argument(
        "-r",
        "--role",
        nargs="+",
        help="Stack Roles space separated",
        type=str,
        default=[],
    )
    parser.add_argument(
        "-t",
        "--type",
        nargs="+",
        help="Stack Types space separated - use ALL for any type",
        type=str,
        default=[],
    )

    return parser


def get_stack_single_parser():
    parser = argparse.ArgumentParser(add_help=False)

    parser.add_argument(
        "-s",
        "--stack",
        nargs=1,
        help="Stack Names space separated",
        required=True,
        type=str,
        default=[],
    )

    return parser


def get_stackset_single_parser():
    parser = argparse.ArgumentParser(add_help=False)

    parser.add_argument(
        "-s",
        "--stackset",
        nargs=1,
        dest="stack",
        help="StackSet name",
        required=True,
        type=str,
        default=[],
    )

    return parser


def get_create_update_parser():
    parser = argparse.ArgumentParser(add_help=False)

    parser.add_argument(
        "--topics",
        nargs="+",
        help="SNS Topics Arn for notification",
        type=str,
        default=[],
    )
    parser.add_argument(
        "-M",
        "--max_retry_ecs_service_running_count",
        help="Trigger Stack Cancel Update (RollBack) if Service deployment's failedTasks is equals or greater than max_retry",
        type=int,
        default=0,
    )
    parser.add_argument(
        "--disable_rollback",
        help="Preserve the state of previously provisioned "
        "resources when an operation fails",
        action="store_true",
    )

    return parser


# parse main argumets
def get_parser():
    parser = argparse.ArgumentParser(
        description="Stacks Operations",
        epilog="Note: options for Stack Params must be put at the end!",
    )

    # common parser
    parser.add_argument("--region", help="Region", type=str)
    parser.add_argument("--profile", help="AWS Profile", type=str)
    parser.add_argument(
        "--compact", help="Display Stacks-Output in compact form", action="store_true"
    )
    parser.add_argument(
        "-j",
        "--jobs",
        help="Max Concurrent jobs - default to number of stacks",
        type=int,
    )
    parser.add_argument(
        "--pause",
        help="Pause for seconds between jobs - "
        "0 for interactive - valid only for jobs=1",
        type=int,
    )

    # action parser
    action_parser = argparse.ArgumentParser(add_help=False)

    action_parser.add_argument(
        "-y",
        "--answer_yes",
        help="Answer YES (No Confirm)",
        required=False,
        action="store_true",
    )
    action_parser.add_argument(
        "-w",
        "--nowait",
        help="Do not Wait for action to end",
        required=False,
        action="store_true",
    )
    action_parser.add_argument(
        "-c",
        "--slack_channel",
        help=f"Slack Channel [{cfg.SLACK_CHANNEL}]",
        nargs="?",
        const=cfg.SLACK_CHANNEL,
        default=False,
    )

    # template parser
    template_parser_create = get_template_parser()
    template_parser_update = get_template_parser(required=False)

    # stack selection parser
    stack_selection_parser = get_stack_selection_parser()

    # stack single parser
    stack_single_parser = get_stack_single_parser()

    # create update parser
    create_update_parser = get_create_update_parser()

    # command subparser
    command_subparser = parser.add_subparsers(
        help="Desired Command", required=True, dest="command"
    )

    # create parser
    parser_create = get_create_parser(
        command_subparser,
        [
            action_parser,
            template_parser_create,
            stack_single_parser,
            create_update_parser,
        ],
    )
    parser_create.set_defaults(func=create)

    # update parser
    parser_update = get_update_parser(
        command_subparser,
        [
            action_parser,
            template_parser_update,
            stack_selection_parser,
            create_update_parser,
        ],
    )
    parser_update.set_defaults(func=update)

    # delete parser
    parser_delete = command_subparser.add_parser(
        "delete",
        parents=[action_parser, stack_single_parser],
        help="Delete Stack (WARNING)",
    )
    parser_delete.set_defaults(func=delete)

    # cancel_update parser
    parser_cancel = command_subparser.add_parser(
        "cancel",
        parents=[action_parser, stack_selection_parser],
        help="Cancel Update Stack",
    )
    parser_cancel.set_defaults(func=cancel_update)

    # continue_update parser
    parser_continue = command_subparser.add_parser(
        "continue",
        parents=[action_parser, stack_selection_parser],
        help="Continue Update RollBack",
    )
    parser_continue.set_defaults(func=continue_update)
    parser_continue.add_argument(
        "--resources_to_skip", help="Resource to Skip", default=[], nargs="+"
    )

    # roll back parser
    parser_rollback = command_subparser.add_parser(
        "rollback",
        parents=[action_parser, stack_selection_parser],
        help="RollBack to the last known stable state",
    )
    parser_rollback.set_defaults(func=rollback)

    # info parser
    parser_info = command_subparser.add_parser(
        "info", parents=[stack_selection_parser], help="Show Stack Info"
    )
    parser_info.set_defaults(func=info)

    # parameters parser
    parser_parameters = command_subparser.add_parser(
        "parameters",
        parents=[template_parser_update, stack_selection_parser],
        help="Show Available Stack Parameters",
    )
    parser_parameters.set_defaults(func=parameters)

    # resolve parser
    parser_resolve = command_subparser.add_parser(
        "resolve",
        parents=[template_parser_update, stack_selection_parser],
        help="Resolve Stack template - output in yaml short format",
    )
    parser_resolve.set_defaults(func=resolve)

    # log parser
    parser_log = command_subparser.add_parser(
        "log", parents=[stack_single_parser], help="Show Stack Log"
    )
    parser_log.set_defaults(func=log)
    parser_log.add_argument(
        "-d",
        "--timedelta",
        help="How many seconds go back in time from stack last event - "
        "use 0 for realtime - if < 30 assume days",
        default=cfg.timedelta,
    )

    # dashboard parser
    set_dash_parser(
        command_subparser,
        [
            stack_selection_parser,
        ],
    )

    # show parser
    parser_show = get_show_parser(
        command_subparser,
        [
            stack_selection_parser,
        ],
    )
    parser_show.set_defaults(func=show_table, all_stacks=True)

    # stackset parser
    set_stackset_parser(
        command_subparser,
        [
            action_parser,
        ],
    )

    # ssm parser
    set_ssm_parser(
        command_subparser,
        [
            stack_selection_parser,
        ],
    )

    # replicate parser
    set_replicate_parser(
        command_subparser,
        [
            action_parser,
        ],
    )

    # r53 parser
    set_r53_parser(
        command_subparser,
        [
            stack_selection_parser,
        ],
    )

    return parser


def set_cfg(argv):
    parser = get_parser()
    args = parser.parse_known_args(argv)

    for n, v in vars(args[0]).items():
        setattr(cfg, n, v)

    # trick for showing ALL Stacks
    # if nor stack nor role nor type are specified.
    if cfg.all_stacks and not (cfg.stack or cfg.role or cfg.type):
        cfg.type = ["ALL"]

    if not cfg.no_stacks and not (cfg.stack or cfg.role or cfg.type):
        parser.print_help()
        exit(0)

    cfg.stack_args = args[1]
