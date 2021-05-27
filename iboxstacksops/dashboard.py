from . import resources
from .common import *


def add_stack(istack):
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

    ScalingPolicyTrackingsCpuBaseLabel = 'ScalingPolicyTrackingsCpu'
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

    def get_widget_annotations(res):
        AlarmCPUHighThreshold = 60
        AlarmCPULowThreshold = 30
        ScalingPolicyTrackingsCpuValue = 80
        ScalingPolicyTrackingsCpuLabel = ScalingPolicyTrackingsCpuBaseLabel
        widget_annotations_type = None

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

        return widget_annotations, widget_annotations_type

    def do_label_exist(w_label, w_metrics):
        for index, metric in enumerate(w_metrics):
            if isinstance(metric, dict) and w_label in list(metric.values()):
                return True
            for m in metric:
                if isinstance(m, dict) and w_label in list(m.values()):
                    return index

        return None

    def do_insert_metrics(m, widget):
        label = m['label']
        metric = m['metric']
        msg = m['name']
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
        annotations['horizontal'] = widget_annotations.get(
            widget_annotations_type, [])

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
            widget['properties']['metrics'] = (w[windex]['properties']
                                               ['metrics'])
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

        for n in ['cpu', 'response']:
            for m in metrics[n]:
                do_insert_metrics(m, widget)

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

            for n in ['requests', 'healthy']:
                for m in metrics[n]:
                    do_insert_metrics(m, widget)

        # BEGIN 5xx
        list_5xx = [n for n, v in enumerate(w)
                    if v['properties']['title'] == widget_title['5xx']]
        index_5xx = list_5xx[0] if len(list_5xx) > 0 else len(w)

        if resolve_widget_map('5xx'):
            widget = get_widget_base(
                'global', list_5xx, index_5xx, widget_title['5xx'], w)

            for n in ['5xx', '4xx']:
                for m in metrics[n]:
                    do_insert_metrics(m, widget)

        # BEGIN 5xx ELB
        list_5xx_elb = [n for n, v in enumerate(w)
                        if v['properties']['title'] == widget_title['5xx_elb']]
        index_5xx_elb = list_5xx_elb[0] if len(list_5xx_elb) > 0 else len(w)

        if resolve_widget_map('5xx_elb') and 'ServiceName' not in res:
            widget = get_widget_base(
                'global', list_5xx_elb, index_5xx_elb,
                widget_title['5xx_elb'], w)

            for n in ['5xx_elb', '4xx_elb']:
                for m in metrics[n]:
                    do_insert_metrics(m, widget)

        # BEGIN 50x ELB
        list_50x_elb = [n for n, v in enumerate(w)
                        if v['properties']['title'] == widget_title['50x_elb']]
        index_50x_elb = list_50x_elb[0] if len(list_50x_elb) > 0 else len(w)

        if resolve_widget_map('50x_elb') and 'ServiceName' not in res:
            widget = get_widget_base(
                'global', list_50x_elb, index_50x_elb,
                widget_title['50x_elb'], w)

            for n in ['500_elb', '502_elb', '503_elb', '504_elb']:
                for m in metrics[n]:
                    do_insert_metrics(m, widget)

        # BEGIN network
        list_net = [n for n, v in enumerate(w)
                    if v['properties']['title'] == widget_title['net']]
        index_net = list_net[0] if len(list_net) > 0 else len(w)

        if resolve_widget_map('net'):
            widget = get_widget_base(
                'global', list_net, index_net, widget_title['net'], w)

            for n in ['netin', 'netout']:
                for m in metrics[n]:
                    do_insert_metrics(m, widget)
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

    def get_metrics(res):
        # update widget_title and widget_label
        widget_title['role'] = f'{istack.EnvRole}.{istack.name}'
        title_role = widget_title['role']

        # Set common variable for ELB Classic and Application used by EC2 stack
        if any(n in res
               for n in ['LoadBalancerNameExternal',
                         'LoadBalancerNameInternal']):
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
            AWS_ELB = None
            Latency = None
            HTTPCode_Backend_5XX = None
            HTTPCode_Backend_4XX = None

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
            label = f'Cpu - {istack.cfg.statistic}'
            metrics['cpu'].append({
                'name': 'Cpu',
                'label': label,
                'metric': [
                    'AWS/ECS',
                    'CPUUtilization',
                    'ServiceName',
                    res['ServiceName'],
                    'ClusterName',
                    res['ClusterName'],
                    {
                        'period': 300,
                        'stat': istack.cfg.statistic,
                        'label': label,
                    }
                ]
            })
            # Always add cpu maximum
            label = 'Cpu - Maximum'
            metrics['cpu'].append({
                'name': 'Cpu - Maximum',
                'label': label,
                'metric': [
                    'AWS/ECS',
                    'CPUUtilization',
                    'ServiceName',
                    res['ServiceName'],
                    'ClusterName',
                    res['ClusterName'],
                    {
                        'period': 300,
                        'stat': 'Maximum',
                        'label': label,
                    }
                ]
            })
            # TargetGroups
            for n, v in res.items():
                if (n.startswith('TargetGroup')
                        and n.endswith(('External', 'Internal'))):
                    if n.endswith('External'):
                        suffix = 'External'
                    else:
                        suffix = 'Internal'

                    tg_name = n.replace('TargetGroup', '')

                    if f'LoadBalancer{suffix}' not in res:
                        continue
                    else:
                        lb_name = f'LoadBalancer{suffix}'

                    # Response Time
                    label = (f'Response {tg_name}'
                             f' - {istack.cfg.statisticresponse}')
                    metrics['response'].append({
                        'name': f'Response {tg_name}',
                        'label': label,
                        'metric': [
                            'AWS/ApplicationELB',
                            'TargetResponseTime',
                            'TargetGroup',
                            res[n],
                            'LoadBalancer',
                            res[lb_name],
                            {
                                'period': 300,
                                'stat': istack.cfg.statisticresponse,
                                'yAxis': 'right',
                                'label': label,
                            }
                        ]
                    })
                    # Healthy
                    label = f'{title_role} - Healthy'
                    metrics['healthy'].append({
                        'name': f'Healthy {tg_name}',
                        'label': label,
                        'metric': [
                            'AWS/ApplicationELB',
                            'HealthyHostCount',
                            'TargetGroup',
                            res[n],
                            'LoadBalancer',
                            res[lb_name],
                            {
                                'label': label,
                                'stat': istack.cfg.statistic,
                                'yAxis': 'right'
                            }
                        ]
                    })
                    # Requests
                    label = f'{title_role} {tg_name} - Requests'
                    metrics['requests'].append({
                        'name': f'Requests {tg_name}',
                        'label': label,
                        'metric': [
                            'AWS/ApplicationELB',
                            'RequestCount',
                            'TargetGroup',
                            res[n],
                            'LoadBalancer',
                            res[lb_name],
                            {
                                'label': label,
                                'stat': 'Sum'
                            }
                        ]
                    })
                    # 5xx
                    label = f'{title_role} {tg_name} - 5xx'
                    metrics['5xx'].append({
                        'name': f'5xx {tg_name}',
                        'label': label,
                        'metric': [
                            'AWS/ApplicationELB',
                            'HTTPCode_Target_5XX_Count',
                            'TargetGroup',
                            res[n],
                            'LoadBalancer',
                            res[lb_name],
                            {
                                'label': label,
                                'stat': 'Sum'
                            }
                        ]
                    })
                    # 4xx
                    label = f'{title_role} {tg_name} - 4xx'
                    metrics['4xx'].append({
                        'name': f'4xx {tg_name}',
                        'label': label,
                        'metric': [
                            'AWS/ApplicationELB',
                            'HTTPCode_Target_4XX_Count',
                            'TargetGroup',
                            res[n],
                            'LoadBalancer',
                            res[lb_name],
                            {
                                'label': label,
                                'stat': 'Sum',
                                'yAxis': 'right'
                            }
                        ]
                    })
        else:
            # EC2
            if all(n in res for n in ['AutoScalingGroupName']):
                # CPU
                label = f'Cpu - {istack.cfg.statistic}'
                metrics['cpu'].append({
                    'name': 'Cpu',
                    'label': label,
                    'metric': [
                        'AWS/EC2',
                        'CPUUtilization',
                        'AutoScalingGroupName',
                        res['AutoScalingGroupName'],
                        {
                            'period': 300,
                            'stat': istack.cfg.statistic,
                            'label': label,
                        }
                    ]
                })
                # Always add cpu maximum
                label = 'Cpu - Maximum'
                metrics['cpu'].append({
                    'name': 'Cpu - Maximum',
                    'label': label,
                    'metric': [
                        'AWS/EC2',
                        'CPUUtilization',
                        'AutoScalingGroupName',
                        res['AutoScalingGroupName'],
                        {
                            'period': 300,
                            'stat': 'Maximum',
                            'label': label,
                        }
                    ]
                })
                # CPU Spot
                if all(n in res for n in ['AutoScalingGroupSpotName']):
                    label = f'Cpu Spot - {istack.cfg.statistic}'
                    metrics['cpu'].append({
                        'name': 'Cpu Spot',
                        'label': label,
                        'metric': [
                            'AWS/EC2',
                            'CPUUtilization',
                            'AutoScalingGroupName',
                            res['AutoScalingGroupSpotName'],
                            {
                                'period': 300,
                                'stat': istack.cfg.statistic,
                                'label': label,
                            }
                        ]
                    })
                # Healthy
                label = f'{title_role} - Healthy'
                metrics['healthy'].append({
                    'name': 'Healthy',
                    'label': label,
                    'metric': [
                        'AWS/AutoScaling',
                        'GroupInServiceInstances',
                        'AutoScalingGroupName',
                        res['AutoScalingGroupName'],
                        {
                            'label': label,
                            'stat': istack.cfg.statistic,
                            'yAxis': 'right'
                        }
                    ]
                })
                # Network
                label = f'{title_role} - NetworkIN'
                metrics['netin'].append({
                    'name': 'NetworkIN',
                    'label': label,
                    'metric': [
                        'AWS/EC2',
                        'NetworkIn',
                        'AutoScalingGroupName',
                        res['AutoScalingGroupName'],
                        {
                            'label': label,
                            'period': 300,
                            'stat': 'Sum'
                        }
                    ]
                })
                label = f'{title_role} - NetworkOUT'
                metrics['netout'].append({
                    'name': 'NetworkOUT',
                    'label': label,
                    'metric': [
                        'AWS/EC2',
                        'NetworkOut',
                        'AutoScalingGroupName',
                        res['AutoScalingGroupName'],
                        {
                            'label': label,
                            'period': 300,
                            'stat': 'Sum',
                            'yAxis': 'right'
                        }
                    ]
                })

            # ELB
            for n in ['External', 'Internal']:
                res_name = locals()[f'LoadBalancerName{n}']

                if res_name in res:
                    # Response
                    label = f'Response {n} - {istack.cfg.statisticresponse}'
                    metrics['response'].append({
                        'name': f'Response {n}',
                        'label': label,
                        'metric': [
                            AWS_ELB,
                            Latency,
                            LoadBalancerName,
                            res[res_name],
                            {
                                'period': 300,
                                'stat': istack.cfg.statisticresponse,
                                'yAxis': 'right',
                                'label': label,
                            }
                        ]
                    })
                    # Requests
                    label = f'{title_role} {n} - Requests'
                    metrics['requests'].append({
                        'name': f'Requests {n}',
                        'label': label,
                        'metric': [
                            AWS_ELB,
                            'RequestCount',
                            LoadBalancerName,
                            res[res_name],
                            {
                                'label': label,
                                'stat': 'Sum'
                            }
                        ]
                    })
                    # 5xx
                    label = f'{title_role} {n} - 5xx'
                    metrics['5xx'].append({
                        'name': f'5xx {n}',
                        'label': label,
                        'metric': [
                            AWS_ELB,
                            HTTPCode_Backend_5XX,
                            LoadBalancerName,
                            res[res_name],
                            {
                                'label': label,
                                'stat': 'Sum'
                            }
                        ]
                    })
                    # 4xx
                    label = f'{title_role} {n} - 4xx'
                    metrics['4xx'].append({
                        'name': f'4xx {n}',
                        'label': label,
                        'metric': [
                            AWS_ELB,
                            HTTPCode_Backend_4XX,
                            LoadBalancerName,
                            res[res_name],
                            {
                                'label': label,
                                'stat': 'Sum',
                                'yAxis': 'right'
                            }
                        ]
                    })
                    # 5xx ELB
                    label = f'{title_role} {n} - 5xx'
                    metrics['5xx_elb'].append({
                        'name': f'5xx {n} ELB',
                        'label': label,
                        'metric': [
                            AWS_ELB,
                            HTTPCode_ELB_5XX,
                            LoadBalancerName,
                            res[res_name],
                            {
                                'label': label,
                                'stat': 'Sum'
                            }
                        ]
                    })
                    # 4xx ELB
                    label = f'{title_role} {n} - 4xx'
                    metrics['4xx_elb'].append({
                        'name': f'4xx {n} ELB',
                        'label': label,
                        'metric': [
                            AWS_ELB,
                            HTTPCode_ELB_4XX,
                            LoadBalancerName,
                            res[res_name],
                            {
                                'label': label,
                                'stat': 'Sum',
                                'yAxis': 'right'
                            }
                        ]
                    })

                    # 50x ELB
                    if f'LoadBalancer{n}' in res:
                        # 500
                        label = f'{title_role} {n} - 500'
                        metrics['500_elb'].append({
                            'name': f'500 {n} ELB',
                            'label': label,
                            'metric': [
                                'AWS/ApplicationELB',
                                'HTTPCode_ELB_500_Count',
                                'LoadBalancer',
                                res[res_name],
                                {
                                    'label': label,
                                    'stat': 'Sum',
                                    'yAxis': ('right' if n == 'Internal'
                                              else 'left')
                                }
                            ]
                        })
                        # 502
                        label = f'{title_role} {n} - 502'
                        metrics['502_elb'].append({
                            'name': f'502 {n} ELB',
                            'label': label,
                            'metric': [
                                'AWS/ApplicationELB',
                                'HTTPCode_ELB_502_Count',
                                'LoadBalancer',
                                res[res_name],
                                {
                                    'label': label,
                                    'stat': 'Sum',
                                    'yAxis': ('right' if n == 'Internal'
                                              else 'left')
                                }
                            ]
                        })
                        # 503
                        label = f'{title_role} {n} - 503'
                        metrics['503_elb'].append({
                            'name': f'503 {n} ELB',
                            'label': label,
                            'metric': [
                                'AWS/ApplicationELB',
                                'HTTPCode_ELB_503_Count',
                                'LoadBalancer',
                                res[res_name],
                                {
                                    'label': label,
                                    'stat': 'Sum',
                                    'yAxis': ('right' if n == 'Internal'
                                              else 'left')
                                }
                            ]
                        })
                        # 504
                        label = f'{title_role} {n} - 504'
                        metrics['504_elb'].append({
                            'name': f'504 {n} ELB',
                            'label': label,
                            'metric': [
                                'AWS/ApplicationELB',
                                'HTTPCode_ELB_504_Count',
                                'LoadBalancer',
                                res[res_name],
                                {
                                    'label': label,
                                    'stat': 'Sum',
                                    'yAxis': ('right' if n == 'Internal'
                                              else 'left')
                                }
                            ]
                        })

        return metrics

    # get stack resources
    res = resources.get(istack, dash=True)

    # get widget annotations and widget_annotations_type for alarms threshold
    # or policy tracking target value
    widget_annotations, widget_annotations_type = get_widget_annotations(res)

    if not istack.cfg.silent:
        pprint(res)

    # get metrics
    metrics = get_metrics(res)

    print('')
    # update dashboards
    update_dashboard(res, istack.cfg.dash_name)


def update(istack):
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

    if (res_changed
            or any(n in istack.changed['outputs'] for n in [
                'ScalingPolicyTrackings',
                'AutoScalingScalingPolicy',
                'ApplicationAutoScalingScalingPolicy'])):
        for dash in response_dash['DashboardEntries']:
            if istack.name in dash['DashboardName']:
                istack.cfg.dash_name = dash['DashboardName']
                add_stack(istack)
