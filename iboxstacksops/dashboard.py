from . import resources
from .common import *


AlarmCPUHighThreshold = 60
AlarmCPULowThreshold = 30
ScalingPolicyTrackingsCpuBaseLabel = 'ScalingPolicyTrackingsCpu'
ScalingPolicyTrackingsCpuValue = 80

widget_width = {
    'stack': 12,
    'global': 24,
}

widget_height = {
    'stack': 6,
    'global': 6,
}

widget_title = {
    '5xx': '5xx - 4xx',
    'req': 'Requests - Healthy',
    'net': 'NetworkIN - NetworkOUT',
    '5xx_elb': '5xx - 4xx [ELB]',
    '50x_elb': '50x External - 50x Internal [ELB]',
}

widget_map = {
    'req': ['requests', 'healthy'],
    '5xx': ['5xx', '4xx'],
    '5xx_elb': ['5xx_elb', '4xx_elb'],
    '50x_elb': ['500_elb', '502_elb', '503_elb', '504_elb'],
    'net': ['netin', 'netout'],
}


widget_annotations = {}
widget_annotations_type = 'tracking'
widget_label = {}


def get_alarm(res):
    alarms = {}
    cloudwatch = istack.boto3.resource('cloudwatch')
    for a in ['AlarmCPUHigh', 'AlarmCPULow']:
        alarm = cloudwatch.Alarm(res[a])
        alarms[a] = alarm.threshold

    return alarms['AlarmCPUHigh'], alarms['AlarmCPULow']


def get_policy_ec2(res):
    polname = res['ScalingPolicyTrackings1'].split('/')[2]
    AutoScalingGroupName = ('AutoScalingGroupSpotName' if
                            'AutoScalingGroupSpotName' in res else
                            'AutoScalingGroupName')
    client = istack.boto3.client('autoscaling')
    response = client.describe_policies(
        AutoScalingGroupName=res[AutoScalingGroupName],
        PolicyNames=[polname],
    )

    return response['ScalingPolicies'][0]['TargetTrackingConfiguration']


def get_policy_ecs(res):
    resname = '/'.join(
        res['ScalingPolicyTrackings1'].split('/')[2:5]).split(':')[0]
    client = istack.boto3.client('application-autoscaling')
    response = client.describe_scaling_policies(
        PolicyNames=list(istack.cfg.SCALING_POLICY_TRACKINGS_NAMES.keys()),
        ResourceId=resname,
        ServiceNamespace='ecs',
    )

    return response['ScalingPolicies'][0][
        'TargetTrackingScalingPolicyConfiguration']


def get_policy(res):
    if 'AutoScalingGroupName' in res:
        conf = get_policy_ec2(res)
    else:
        conf = get_policy_ecs(res)

    stat = 'Average'
    value = conf['TargetValue']
    if ('CustomizedMetricSpecification' in conf and
            'Statistic' in conf['CustomizedMetricSpecification']):
        stat = conf['CustomizedMetricSpecification']['Statistic']

    return value, f'{ScalingPolicyTrackingsCpuBaseLabel}{stat}'


def resolve_widget_map(name):
    count = 0
    for n in widget_map[name]:
        count += len(metrics[n])

    if count > 0:
        return True


def set_widget_annotations(res):
    global AlarmCPUHighThreshold
    global AlarmCPULowThreshold
    # global ScalingPolicyTrackingsCpuLabel
    global ScalingPolicyTrackingsCpuValue
    global widget_annotations
    global widget_annotations_type

    ScalingPolicyTrackingsCpuLabel = ScalingPolicyTrackingsCpuBaseLabel

    if 'AlarmCPUHigh' and 'AlarmCPULow' in res:
        AlarmCPUHighThreshold, AlarmCPULowThreshold = get_alarm(res)
        widget_annotations_type = 'step'
    if any(k in res for k in istack.cfg.SCALING_POLICY_TRACKINGS_NAMES):
        ScalingPolicyTrackingsCpuValue, ScalingPolicyTrackingsCpuLabel = (
            get_policy(res))
        widget_annotations_type = 'tracking'

    widget_annotations = {
        'tracking': [
            {
                'value': 100
            },
            {
                'label': ScalingPolicyTrackingsCpuLabel,
                'value': ScalingPolicyTrackingsCpuValue,
                'color': '#1f77b4',
            }
        ],
        'step': [
            {
                'label': 'AlarmCPUHighThreshold',
                'value': AlarmCPUHighThreshold,
            },
            {
                'label': 'AlarmCPULowThreshold',
                'value': AlarmCPULowThreshold,
                'color': '#2ca02c',
            }
        ]
    }


def do_label_exist(w_label, w_metrics):
    for index, metric in enumerate(w_metrics):
        if isinstance(metric, dict) and w_label in list(metric.values()):
            return True
        for m in metric:
            if isinstance(m, dict) and w_label in list(m.values()):
                return index

    return None


def do_insert_metrics(label, metric, widget, msg):
    widget_metrics = widget['properties']['metrics']
    if do_label_exist(label, metric):
        label_index = do_label_exist(label, widget_metrics)
        if label_index is None:
            widget_metrics.append(metric)
            out_msg = 'Added'
        else:
            widget_metrics[label_index] = metric
            out_msg = '-- Updated'
        if not istack.cfg.silent:
            print(f'\tMetrics: {msg} {out_msg}')


def get_widget_map_position(wtype, index):
    if wtype == 'stack':
        # even index (left side)
        if (index & 1) == 0:
            return (0, widget_height['stack'] * index)
        # odd index (right side)
        else:
            return (widget_width['stack'], widget_height['stack'] * index)
    # global type
    else:
        return (0, widget_height['global'] * index)


def add_annotations(w, atype):
    if 'annotations' not in w['properties']:
        w['properties']['annotations'] = {}

    annotations = w['properties']['annotations']
    # Vertical
    if atype == 'vertical':
        value_now = datetime.utcnow().strftime('%Y-%m-%dT%X.000Z')
        w_ann_vertical = {
            'label': '',
            'value': value_now,
        }
        if istack.cfg.vertical in ['after', 'before']:
            w_ann_vertical['fill'] = istack.cfg.vertical

        # vertical annotation not present
        if 'vertical' not in annotations:
            annotations['vertical'] = []
        # append only if empty or there is not annotations
        # with value in the same minute
        if (not annotations['vertical'] or
                all(value_now[0:16] not in a['value']
                    for a in annotations['vertical'])):
            annotations['vertical'].append(w_ann_vertical)

    # Horizontal annotations
    annotations['horizontal'] = widget_annotations[widget_annotations_type]

    # Horizontal (ec2-ecs)
    # if atype == 'ecs':
    #    annotations['horizontal'] = widget_annotations['ecs']
    # if atype == 'ec2':
    #    annotations['horizontal'] = widget_annotations['ec2']


def get_widget_base(wtype, wlist, windex, title, w):
    widget = {}
    widget.update({
        'type': 'metric',
        'x': get_widget_map_position(wtype, windex)[0],
        'y': get_widget_map_position(wtype, windex)[1],
        'width': widget_width[wtype],
        'height': widget_height[wtype],
        'properties': {
            'view': 'timeSeries',
            'stacked': False,
            'metrics': [],
            'region': istack.boto3.region_name,
            'title': title,
            'period': 300,
        }
    })

    # If widget already exist get metrics from current one
    if len(wlist) > 0:
        widget['properties']['metrics'] = w[windex]['properties']['metrics']
        # and if exists, annotations too..
        if 'annotations' in w[windex]['properties']:
            widget['properties']['annotations'] = w[windex][
                'properties']['annotations']
        del w[windex]
        out_msg = 'Updated'
    else:
        out_msg = 'Added'

    if istack.cfg.vertical:
        add_annotations(widget, 'vertical')

    w.insert(windex, widget)
    if not istack.cfg.silent:
        print(f'Widget:{title} {out_msg}')

    return widget


def update_widget_stack_properties(widget, res):
    for m in metrics['cpu']:
        do_insert_metrics(widget_label['cpu'], m, widget, 'Cpu')
        do_insert_metrics(widget_label['cpu'] + 'Spot', m, widget, 'Cpu')
        # Always add cpu maximum
        do_insert_metrics('Cpu - Maximum', m, widget, 'Cpu - Maximum')
    for m in metrics['response']:
        do_insert_metrics(widget_label['response'], m, widget, 'Response')
        do_insert_metrics(
            widget_label['response_external'], m, widget, 'Response External')
        do_insert_metrics(
            widget_label['response_internal'], m, widget, 'Response Internal')

    add_annotations(widget, istack.StackType)


def update_widget_5xx_properties(widget, res):
    for m in metrics['5xx']:
        do_insert_metrics(widget_label['5xx'], m, widget, '5xx')
        do_insert_metrics(
            widget_label['5xx_external'], m, widget, '5xx External')
        do_insert_metrics(
            widget_label['5xx_internal'], m, widget, '5xx Internal')

    for m in metrics['4xx']:
        do_insert_metrics(widget_label['4xx'], m, widget, '4xx')
        do_insert_metrics(
            widget_label['4xx_external'], m, widget, '4xx External')
        do_insert_metrics(
            widget_label['4xx_internal'], m, widget, '4xx Internal')


def update_widget_5xx_elb_properties(widget, res):
    for m in metrics['5xx_elb']:
        do_insert_metrics(
            widget_label['5xx_external'], m, widget, '5xx External ELB')
        do_insert_metrics(
            widget_label['5xx_internal'], m, widget, '5xx Internal ELB')

    for m in metrics['4xx_elb']:
        do_insert_metrics(
            widget_label['4xx_external'], m, widget, '4xx External ELB')
        do_insert_metrics(
            widget_label['4xx_internal'], m, widget, '4xx Internal ELB')


def update_widget_50x_elb_properties(widget, res):
    for m in metrics['500_elb']:
        do_insert_metrics(
            widget_label['500_external'], m, widget, '500 External ELB')
        do_insert_metrics(
            widget_label['500_internal'], m, widget, '500 Internal ELB')
    for m in metrics['502_elb']:
        do_insert_metrics(
            widget_label['502_external'], m, widget, '502 External ELB')
        do_insert_metrics(
            widget_label['502_internal'], m, widget, '502 Internal ELB')
    for m in metrics['503_elb']:
        do_insert_metrics(
            widget_label['503_external'], m, widget, '503 External ELB')
        do_insert_metrics(
            widget_label['503_internal'], m, widget, '503 Internal ELB')
    for m in metrics['504_elb']:
        do_insert_metrics(
            widget_label['504_external'], m, widget, '504 External ELB')
        do_insert_metrics(
            widget_label['504_internal'], m, widget, '504 Internal ELB')


def update_widget_req_properties(widget, res):
    for m in metrics['requests']:
        do_insert_metrics(widget_label['req'], m, widget, 'Requests')
        do_insert_metrics(
            widget_label['req_external'], m, widget, 'Requests External')
        do_insert_metrics(
            widget_label['req_internal'], m, widget, 'Requests Internal')

    for m in metrics['healthy']:
        do_insert_metrics(widget_label['healthy'], m, widget, 'Healthy')


def update_widget_network_properties(widget, res):
    for m in metrics['netin']:
        do_insert_metrics(widget_label['netin'], m, widget, 'NetworkIN')

    for m in metrics['netout']:
        do_insert_metrics(widget_label['netout'], m, widget, 'NetworkOUT')


def update_dashboard(res, dashboard_name):
    cw = istack.boto3.client('cloudwatch')

    if not istack.cfg.silent:
        print(dashboard_name)

    try:
        dashboard_body = cw.get_dashboard(
            DashboardName=dashboard_name)['DashboardBody']
        dash = json.loads(dashboard_body)
    except Exception as e:
        print('DashBoard do not exist, creating one..\n')
        dash = {'widgets': []}

    w = dash['widgets']

    # BEGIN cpu
    # Find the current number of widget stacks,
    # so that the next one is added at the end
    len_stacks = len([n for n in w if n['width'] == widget_width['stack']])

    list_role = [n for n, v in enumerate(w)
                 if v['properties']['title'] == widget_title['role']]
    index_role = list_role[0] if len(list_role) > 0 else len_stacks

    widget = get_widget_base(
        'stack', list_role, index_role, widget_title['role'], w)
    update_widget_stack_properties(widget, res)

    # If metrics are empty delete widget (Ex ecs-alb)
    if len(widget['properties']['metrics']) == 0:
        del w[index_role]

    # BEGIN requests
    list_req = [n for n, v in enumerate(w)
                if v['properties']['title'] == widget_title['req']]
    index_req = list_req[0] if len(list_req) > 0 else len(w)

    if resolve_widget_map('req'):
        widget = get_widget_base(
            'global', list_req, index_req, widget_title['req'], w)
        update_widget_req_properties(widget, res)

    # BEGIN 5xx
    list_5xx = [n for n, v in enumerate(w)
                if v['properties']['title'] == widget_title['5xx']]
    index_5xx = list_5xx[0] if len(list_5xx) > 0 else len(w)

    if resolve_widget_map('5xx'):
        widget = get_widget_base(
            'global', list_5xx, index_5xx, widget_title['5xx'], w)
        update_widget_5xx_properties(widget, res)

    # BEGIN 5xx ELB
    list_5xx_elb = [n for n, v in enumerate(w)
                    if v['properties']['title'] == widget_title['5xx_elb']]
    index_5xx_elb = list_5xx_elb[0] if len(list_5xx_elb) > 0 else len(w)

    if resolve_widget_map('5xx_elb') and 'ServiceName' not in res:
        widget = get_widget_base(
            'global', list_5xx_elb, index_5xx_elb, widget_title['5xx_elb'], w)
        update_widget_5xx_elb_properties(widget, res)

    # BEGIN 50x ELB
    list_50x_elb = [n for n, v in enumerate(w)
                    if v['properties']['title'] == widget_title['50x_elb']]
    index_50x_elb = list_50x_elb[0] if len(list_50x_elb) > 0 else len(w)

    if resolve_widget_map('50x_elb') and 'ServiceName' not in res:
        widget = get_widget_base(
            'global', list_50x_elb, index_50x_elb, widget_title['50x_elb'], w)
        update_widget_50x_elb_properties(widget, res)

    # BEGIN network
    list_net = [n for n, v in enumerate(w)
                if v['properties']['title'] == widget_title['net']]
    index_net = list_net[0] if len(list_net) > 0 else len(w)

    if resolve_widget_map('net'):
        widget = get_widget_base(
            'global', list_net, index_net, widget_title['net'], w)
        update_widget_network_properties(widget, res)

    # END Widgets

    if istack.cfg.debug:
        print(json.dumps(dash, indent=4))
        return

    # Put DashBoard
    out = cw.put_dashboard(
        DashboardName=dashboard_name,
        DashboardBody=json.dumps(dash, separators=(',', ':'))
    )

    if len(out['DashboardValidationMessages']) > 0:
        pprint(out)
    else:
        print('')
        mylog('CloudWatch-DashBoard[' + dashboard_name + '] Updated:')

    return True


def mylog(string):
    print(istack.name + ' # ' + string)


def set_vars_for_metrics(res):
    global widget_title
    global widget_label
    global LoadBalancerName
    global LoadBalancerNameExternal
    global LoadBalancerNameInternal
    global AWS_ELB
    global Latency
    global HTTPCode_Backend_5XX
    global HTTPCode_Backend_4XX
    global metrics

    # update widget_title and widget_label
    widget_title['role'] = f'{istack.EnvRole}.{istack.name}'
    title_role = widget_title['role']

    widget_label['cpu'] = f'Cpu - {istack.cfg.statistic}'
    widget_label['response'] = f'Response - {istack.cfg.statisticresponse}'
    widget_label['response_external'] = (
        f'Response External - {istack.cfg.statisticresponse}')
    widget_label['response_internal'] = (
        f'Response Internal - {istack.cfg.statisticresponse}')
    widget_label['5xx'] = f'{title_role} 5xx'
    widget_label['4xx'] = f'{title_role} 4xx'
    widget_label['500_elb'] = f'{title_role} 500'
    widget_label['502_elb'] = f'{title_role} 502'
    widget_label['503_elb'] = f'{title_role} 503'
    widget_label['504_elb'] = f'{title_role} 504'
    widget_label['5xx_external'] = f'{title_role} External - 5xx'
    widget_label['4xx_external'] = f'{title_role} External - 4xx'
    widget_label['5xx_internal'] = f'{title_role} Internal - 5xx'
    widget_label['4xx_internal'] = f'{title_role} Internal - 4xx'
    widget_label['500_external'] = f'{title_role} External - 500'
    widget_label['500_internal'] = f'{title_role} Internal - 500'
    widget_label['502_external'] = f'{title_role} External - 502'
    widget_label['502_internal'] = f'{title_role} Internal - 502'
    widget_label['503_external'] = f'{title_role} External - 503'
    widget_label['503_internal'] = f'{title_role} Internal - 503'
    widget_label['504_external'] = f'{title_role} External - 504'
    widget_label['504_internal'] = f'{title_role} Internal - 504'
    widget_label['req'] = f'{title_role} - Requests'
    widget_label['healthy'] = f'{title_role} - Healthy'
    widget_label['req_external'] = f'{title_role} External - Requests'
    widget_label['req_internal'] = f'{title_role} Internal - Requests'
    widget_label['netin'] = f'{title_role} - NetworkIN'
    widget_label['netout'] = f'{title_role} - NetworkOUT'

    # Set common variable for ELB Classic and Application used by EC2 stack
    if any(n in res
           for n in ['LoadBalancerNameExternal', 'LoadBalancerNameInternal']):
        LoadBalancerName = 'LoadBalancerName'
        LoadBalancerNameExternal = 'LoadBalancerNameExternal'
        LoadBalancerNameInternal = 'LoadBalancerNameInternal'
        AWS_ELB = 'AWS/ELB'
        Latency = 'Latency'
        HTTPCode_Backend_5XX = 'HTTPCode_Backend_5XX'
        HTTPCode_Backend_4XX = 'HTTPCode_Backend_4XX'
        HTTPCode_ELB_5XX = 'HTTPCode_ELB_5XX'
        HTTPCode_ELB_4XX = 'HTTPCode_ELB_4XX'
    elif any(n in res
             for n in ['LoadBalancerExternal', 'LoadBalancerInternal']):
        LoadBalancerName = 'LoadBalancer'
        LoadBalancerNameExternal = 'LoadBalancerExternal'
        LoadBalancerNameInternal = 'LoadBalancerInternal'
        AWS_ELB = 'AWS/ApplicationELB'
        Latency = 'TargetResponseTime'
        HTTPCode_Backend_5XX = 'HTTPCode_Target_5XX_Count'
        HTTPCode_Backend_4XX = 'HTTPCode_Target_4XX_Count'
        HTTPCode_ELB_5XX = 'HTTPCode_ELB_5XX_Count'
        HTTPCode_ELB_4XX = 'HTTPCode_ELB_4XX_Count'
    else:
        LoadBalancerName = None
        LoadBalancerNameExternal = None
        LoadBalancerNameInternal = None

    metrics = {
        'cpu': [],
        'response': [],
        '5xx': [],
        '4xx': [],
        '5xx_elb': [],
        '4xx_elb': [],
        '500_elb': [],
        '502_elb': [],
        '503_elb': [],
        '504_elb': [],
        'requests': [],
        'healthy': [],
        'netin': [],
        'netout': []
    }

    # ECS
    if all(n in res for n in ['ServiceName', 'ClusterName']):
        # CPU
        metrics['cpu'].append([
            'AWS/ECS',
            'CPUUtilization',
            'ServiceName',
            res['ServiceName'],
            'ClusterName',
            res['ClusterName'],
            {
                'period': 300,
                'stat': istack.cfg.statistic,
                'label': widget_label['cpu']
            }
        ])
        # Always add cpu maximum
        metrics['cpu'].append([
            'AWS/ECS',
            'CPUUtilization',
            'ServiceName',
            res['ServiceName'],
            'ClusterName',
            res['ClusterName'],
            {
                'period': 300,
                'stat': 'Maximum',
                'label': 'Cpu - Maximum'
            }
        ])
        # TargetGroupExternal
        if all(n in res
                for n in ['TargetGroupExternal', 'LoadBalancerExternal']):
            # Response Time
            metrics['response'].append([
                'AWS/ApplicationELB',
                'TargetResponseTime',
                'TargetGroup',
                res['TargetGroupExternal'],
                'LoadBalancer',
                res['LoadBalancerExternal'],
                {
                    'period': 300,
                    'stat': istack.cfg.statisticresponse,
                    'yAxis': 'right',
                    'label': widget_label['response_external']
                }
            ])
            # Healthy
            metrics['healthy'].append([
                'AWS/ApplicationELB',
                'HealthyHostCount',
                'TargetGroup',
                res['TargetGroupExternal'],
                'LoadBalancer',
                res['LoadBalancerExternal'],
                {
                    'label': widget_label['healthy'],
                    'stat': istack.cfg.statistic,
                    'yAxis': 'right'
                }
            ])
            # Requests
            metrics['requests'].append([
                'AWS/ApplicationELB',
                'RequestCount',
                'TargetGroup',
                res['TargetGroupExternal'],
                'LoadBalancer',
                res['LoadBalancerExternal'],
                {
                    'label': widget_label['req_external'],
                    'stat': 'Sum'
                }
            ])
            # 5xx
            metrics['5xx'].append([
                'AWS/ApplicationELB',
                'HTTPCode_Target_5XX_Count',
                'TargetGroup',
                res['TargetGroupExternal'],
                'LoadBalancer',
                res['LoadBalancerExternal'],
                {
                    'label': widget_label['5xx_external'],
                    'stat': 'Sum'
                }
            ])
            # 4xx
            metrics['4xx'].append([
                'AWS/ApplicationELB',
                'HTTPCode_Target_4XX_Count',
                'TargetGroup',
                res['TargetGroupExternal'],
                'LoadBalancer',
                res['LoadBalancerExternal'],
                {
                    'label': widget_label['4xx_external'],
                    'stat': 'Sum',
                    'yAxis': 'right'
                }
            ])
        # TargetGroupInternal
        if all(n in res
                for n in ['TargetGroupInternal', 'LoadBalancerInternal']):
            # Response Time
            metrics['response'].append([
                'AWS/ApplicationELB',
                'TargetResponseTime',
                'TargetGroup',
                res['TargetGroupInternal'],
                'LoadBalancer',
                res['LoadBalancerInternal'],
                {
                    'period': 300,
                    'stat': istack.cfg.statisticresponse,
                    'yAxis': 'right',
                    'label': widget_label['response_internal']
                }
            ])
            # Healthy
            metrics['healthy'].append([
                'AWS/ApplicationELB',
                'HealthyHostCount',
                'TargetGroup',
                res['TargetGroupInternal'],
                'LoadBalancer',
                res['LoadBalancerInternal'],
                {
                    'label': widget_label['healthy'],
                    'stat': istack.cfg.statistic,
                    'yAxis': 'right'
                }
            ])
            # Requests
            metrics['requests'].append([
                'AWS/ApplicationELB',
                'RequestCount',
                'TargetGroup',
                res['TargetGroupInternal'],
                'LoadBalancer',
                res['LoadBalancerInternal'],
                {
                    'label': widget_label['req_internal'],
                    'stat': 'Sum'
                }
            ])
            # 5xx
            metrics['5xx'].append([
                'AWS/ApplicationELB',
                'HTTPCode_Target_5XX_Count',
                'TargetGroup',
                res['TargetGroupInternal'],
                'LoadBalancer',
                res['LoadBalancerInternal'],
                {
                    'label': widget_label['5xx_internal'],
                    'stat': 'Sum'
                }
            ])
            # 4xx
            metrics['4xx'].append([
                'AWS/ApplicationELB',
                'HTTPCode_Target_4XX_Count',
                'TargetGroup',
                res['TargetGroupInternal'],
                'LoadBalancer',
                res['LoadBalancerInternal'],
                {
                    'label': widget_label['4xx_internal'],
                    'stat': 'Sum',
                    'yAxis': 'right'
                }
            ])

        return

    # EC2
    if all(n in res for n in ['AutoScalingGroupName']):
        # CPU
        metrics['cpu'].append([
            'AWS/EC2',
            'CPUUtilization',
            'AutoScalingGroupName',
            res['AutoScalingGroupName'],
            {
                'period': 300,
                'stat': istack.cfg.statistic,
                'label': widget_label['cpu']
            }
        ])
        # Always add cpu maximum
        metrics['cpu'].append([
            'AWS/EC2',
            'CPUUtilization',
            'AutoScalingGroupName',
            res['AutoScalingGroupName'],
            {
                'period': 300,
                'stat': 'Maximum',
                'label': 'Cpu - Maximum'
            }
        ])
        # CPU Spot
        if all(n in res for n in ['AutoScalingGroupSpotName']):
            metrics['cpu'].append([
                'AWS/EC2',
                'CPUUtilization',
                'AutoScalingGroupName',
                res['AutoScalingGroupSpotName'],
                {
                    'period': 300,
                    'stat': istack.cfg.statistic,
                    'label': widget_label['cpu'] + 'Spot'
                }
            ])
        # Healthy
        metrics['healthy'].append([
            'AWS/AutoScaling',
            'GroupInServiceInstances',
            'AutoScalingGroupName',
            res['AutoScalingGroupName'],
            {
                'label': widget_label['healthy'],
                'stat': istack.cfg.statistic,
                'yAxis': 'right'
            }
        ])
        # Network
        metrics['netin'].append([
            'AWS/EC2',
            'NetworkIn',
            'AutoScalingGroupName',
            res['AutoScalingGroupName'],
            {
                'label': widget_label['netin'],
                'period': 300,
                'stat': 'Sum'
            }
        ])
        metrics['netout'].append([
            'AWS/EC2',
            'NetworkOut',
            'AutoScalingGroupName',
            res['AutoScalingGroupName'],
            {
                'label': widget_label['netout'],
                'period': 300,
                'stat': 'Sum',
                'yAxis': 'right'
            }
        ])

    # ELB
    for n in ['External', 'Internal']:
        res_name = globals()[f'LoadBalancerName{n}']
        label = n.lower()

        if res_name in res:
            # Response
            metrics['response'].append([
                AWS_ELB,
                Latency,
                LoadBalancerName,
                res[res_name],
                {
                    'period': 300,
                    'stat': istack.cfg.statisticresponse,
                    'yAxis': 'right',
                    'label': widget_label[f'response_{label}']
                }
            ])
            # Requests
            metrics['requests'].append([
                AWS_ELB,
                'RequestCount',
                LoadBalancerName,
                res[res_name],
                {
                    'label': widget_label[f'req_{label}'],
                    'stat': 'Sum'
                }
            ])
            # 5xx
            metrics['5xx'].append([
                AWS_ELB,
                HTTPCode_Backend_5XX,
                LoadBalancerName,
                res[res_name],
                {
                    'label': widget_label[f'5xx_{label}'],
                    'stat': 'Sum'
                }
            ])
            # 4xx
            metrics['4xx'].append([
                AWS_ELB,
                HTTPCode_Backend_4XX,
                LoadBalancerName,
                res[res_name],
                {
                    'label': widget_label[f'4xx_{label}'],
                    'stat': 'Sum',
                    'yAxis': 'right'
                }
            ])
            # 5xx ELB
            metrics['5xx_elb'].append([
                AWS_ELB,
                HTTPCode_ELB_5XX,
                LoadBalancerName,
                res[res_name],
                {
                    'label': widget_label[f'5xx_{label}'],
                    'stat': 'Sum'
                }
            ])
            # 4xx ELB
            metrics['4xx_elb'].append([
                AWS_ELB,
                HTTPCode_ELB_4XX,
                LoadBalancerName,
                res[res_name],
                {
                    'label': widget_label[f'4xx_{label}'],
                    'stat': 'Sum',
                    'yAxis': 'right'
                }
            ])

            # 50x ELB
            if f'LoadBalancer{n}' in res:
                # 500
                metrics['500_elb'].append([
                    'AWS/ApplicationELB',
                    'HTTPCode_ELB_500_Count',
                    'LoadBalancer',
                    res[res_name],
                    {
                        'label': widget_label[f'500_{label}'],
                        'stat': 'Sum',
                        'yAxis': 'right' if n == 'Internal' else 'left',
                    }
                ])
                # 502
                metrics['502_elb'].append([
                    'AWS/ApplicationELB',
                    'HTTPCode_ELB_502_Count',
                    'LoadBalancer',
                    res[res_name],
                    {
                        'label': widget_label[f'502_{label}'],
                        'stat': 'Sum',
                        'yAxis': 'right' if n == 'Internal' else 'left',
                    }
                ])
                # 503
                metrics['503_elb'].append([
                    'AWS/ApplicationELB',
                    'HTTPCode_ELB_503_Count',
                    'LoadBalancer',
                    res[res_name],
                    {
                        'label': widget_label[f'503_{label}'],
                        'stat': 'Sum',
                        'yAxis': 'right' if n == 'Internal' else 'left',
                    }
                ])
                # 504
                metrics['504_elb'].append([
                    'AWS/ApplicationELB',
                    'HTTPCode_ELB_504_Count',
                    'LoadBalancer',
                    res[res_name],
                    {
                        'label': widget_label[f'504_{label}'],
                        'stat': 'Sum',
                        'yAxis': 'right' if n == 'Internal' else 'left',
                    }
                ])


def add_stack(obj):
    global istack
    istack = obj

    # get stack resources
    res = resources.get(istack, dash=True)
    # set widget annotations for alarms threshold
    # or policy tracking target value
    set_widget_annotations(res)
    if not istack.cfg.silent:
        pprint(res)
    # set global vars used later for metrics
    set_vars_for_metrics(res)
    print('')
    # update dashboards
    update_dashboard(res, istack.cfg.dash_name)


def update(obj):
    global istack
    istack = obj

    cw_client = istack.boto3.client('cloudwatch')
    response_dash = cw_client.list_dashboards(DashboardNamePrefix='_')

    resources.set_changed(istack)
    if istack.cfg.dashboard == 'OnChange':
        res_changed = istack.changed['resources']
        mode = ''
    elif istack.cfg.dashboard in ['Always', 'Generic']:
        res_changed = istack.after['resources']
        mode = istack.cfg.dashboard
    else:
        return

    if (not res_changed and
            'ScalingPolicyTrackings' not in istack.changed['outputs']):
        return

    for dash in response_dash['DashboardEntries']:
        if istack.name in dash['DashboardName']:
            add_stack(istack)
