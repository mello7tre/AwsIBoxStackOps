from . import resources
from .common import *

from copy import deepcopy


def add_stack(istack):
    widget_width = {
        "stack": 12,
        "global": 24,
    }

    widget_height = {
        "stack": 6,
        "global": 6,
    }

    widget_title = {
        "5xx": "5xx - 4xx",
        "req": "Requests - Healthy",
        "net": "NetworkIN - NetworkOUT",
        "5xx_elb": "5xx - 4xx [ELB]",
        "50x_elb": "50x External - 50x Internal [ELB]",
    }

    widget_map = {
        "role": ["cpu", "response"],
        "req": ["requests", "healthy"],
        "5xx": ["5xx", "4xx"],
        "5xx_elb": ["5xx_elb", "4xx_elb"],
        "50x_elb": ["500_elb", "502_elb", "503_elb", "504_elb"],
        "net": ["netin", "netout"],
    }

    ScalingPolicyTrackingsCpuBaseLabel = "ScalingPolicyTrackingsCpu"
    widget_label = {}

    def get_alarm(res):
        alarms = {}
        cloudwatch = istack.boto3.resource("cloudwatch")
        for a in ["AlarmCPUHigh", "AlarmCPULow"]:
            alarm = cloudwatch.Alarm(res[a])
            alarms[a] = alarm.threshold

        return alarms["AlarmCPUHigh"], alarms["AlarmCPULow"]

    def get_policy_ec2(res):
        polname = res["ScalingPolicyTrackings1"].split("/")[2]
        AutoScalingGroupName = (
            "AutoScalingGroupSpotName"
            if "AutoScalingGroupSpotName" in res
            else "AutoScalingGroupName"
        )
        client = istack.boto3.client("autoscaling")
        response = client.describe_policies(
            AutoScalingGroupName=res[AutoScalingGroupName],
            PolicyNames=[polname],
        )

        return response["ScalingPolicies"][0]["TargetTrackingConfiguration"]

    def get_policy_ecs(res):
        resname = "/".join(res["ScalingPolicyTrackingsApp"].split("/")[2:5]).split(":")[
            0
        ]
        client = istack.boto3.client("application-autoscaling")
        response = client.describe_scaling_policies(
            PolicyNames=list(istack.cfg.SCALING_POLICY_TRACKINGS_NAMES.keys()),
            ResourceId=resname,
            ServiceNamespace="ecs",
        )

        return response["ScalingPolicies"][0][
            "TargetTrackingScalingPolicyConfiguration"
        ]

    def get_policy(res):
        ret = []
        for n in ["AutoScalingGroupName", "ServiceName"]:
            if n not in res:
                continue
            if n == "AutoScalingGroupName":
                conf = get_policy_ec2(res)
                l_type = "EC2"
                color = "#1f77b4"
            if n == "ServiceName":
                conf = get_policy_ecs(res)
                l_type = "ECS"
                color = "#36dc52"

            stat = "Average"
            value = conf["TargetValue"]
            if (
                "CustomizedMetricSpecification" in conf
                and "Statistic" in conf["CustomizedMetricSpecification"]
            ):
                stat = conf["CustomizedMetricSpecification"]["Statistic"]

            ret.append(
                (
                    value,
                    f"{ScalingPolicyTrackingsCpuBaseLabel}{l_type}{stat}",
                    color,
                )
            )

        return ret

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
        tracking_list = []

        if "AlarmCPUHigh" and "AlarmCPULow" in res:
            AlarmCPUHighThreshold, AlarmCPULowThreshold = get_alarm(res)
            widget_annotations_type = "step"

        if any(k in res for k in istack.cfg.SCALING_POLICY_TRACKINGS_NAMES):
            widget_annotations_type = "tracking"
            tracking_list.append({"value": 100})
            for n in get_policy(res):
                ScalingPolicyTrackingsCpuValue = n[0]
                ScalingPolicyTrackingsCpuLabel = n[1]
                ScalingPolicyTrackingsCpuColor = n[2]
                tracking_list.append(
                    {
                        "label": ScalingPolicyTrackingsCpuLabel,
                        "value": ScalingPolicyTrackingsCpuValue,
                        "color": ScalingPolicyTrackingsCpuColor,
                    }
                )

        widget_annotations = {
            "tracking": tracking_list,
            "step": [
                {
                    "label": "AlarmCPUHighThreshold",
                    "value": AlarmCPUHighThreshold,
                },
                {
                    "label": "AlarmCPULowThreshold",
                    "value": AlarmCPULowThreshold,
                    "color": "#2ca02c",
                },
            ],
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
        label = m["label"]
        metric = m["metric"]
        msg = m["name"]
        widget_metrics = widget["properties"]["metrics"]
        if do_label_exist(label, metric):
            label_index = do_label_exist(label, widget_metrics)
            if label_index is None:
                widget_metrics.append(metric)
                out_msg = "Added"
            else:
                widget_metrics[label_index] = metric
                out_msg = "-- Updated"
            if not istack.cfg.silent:
                print(f"\tMetrics: {msg} {out_msg}")

    def get_widget_map_position(wtype, index):
        if wtype == "stack":
            # even index (left side)
            if (index & 1) == 0:
                return (0, widget_height["stack"] * index)
            # odd index (right side)
            else:
                return (widget_width["stack"], widget_height["stack"] * index)
        # global type
        else:
            return (0, widget_height["global"] * index)

    def add_annotations(w, atype):
        if "annotations" not in w["properties"]:
            w["properties"]["annotations"] = {}

        annotations = w["properties"]["annotations"]
        # Vertical
        if atype == "vertical":
            value_now = datetime.utcnow().strftime("%Y-%m-%dT%X.000Z")
            w_ann_vertical = {
                "label": "",
                "value": value_now,
            }
            if istack.cfg.vertical in ["after", "before"]:
                w_ann_vertical["fill"] = istack.cfg.vertical

            # vertical annotation not present
            if "vertical" not in annotations:
                annotations["vertical"] = []
            # append only if empty or there is not annotations
            # with value in the same minute
            if not annotations["vertical"] or all(
                value_now[0:16] not in a["value"] for a in annotations["vertical"]
            ):
                annotations["vertical"].append(w_ann_vertical)

        # Horizontal annotations
        annotations["horizontal"] = widget_annotations.get(widget_annotations_type, [])

        # Horizontal (ec2-ecs)
        # if atype == 'ecs':
        #    annotations['horizontal'] = widget_annotations['ecs']
        # if atype == 'ec2':
        #    annotations['horizontal'] = widget_annotations['ec2']

    def get_widget_base(wtype, wlist, windex, title, w):
        widget = {}
        widget.update(
            {
                "type": "metric",
                "x": get_widget_map_position(wtype, windex)[0],
                "y": get_widget_map_position(wtype, windex)[1],
                "width": widget_width[wtype],
                "height": widget_height[wtype],
                "properties": {
                    "view": "timeSeries",
                    "stacked": False,
                    "metrics": [],
                    "region": istack.boto3.region_name,
                    "title": title,
                    "period": 300,
                },
            }
        )

        # If widget already exist get metrics from current one
        if len(wlist) > 0:
            widget["properties"]["metrics"] = w[windex]["properties"]["metrics"]
            # and if exists, annotations too..
            if "annotations" in w[windex]["properties"]:
                widget["properties"]["annotations"] = w[windex]["properties"][
                    "annotations"
                ]
            del w[windex]
            out_msg = "Updated"
        else:
            out_msg = "Added"

        if istack.cfg.vertical:
            add_annotations(widget, "vertical")

        w.insert(windex, widget)
        if not istack.cfg.silent:
            print(f"Widget:{title} {out_msg}")

        return widget

    def update_dashboard(res, dashboard_name):
        cw = istack.boto3.client("cloudwatch")

        if not istack.cfg.silent:
            print(dashboard_name)

        try:
            dashboard_body = cw.get_dashboard(DashboardName=dashboard_name)[
                "DashboardBody"
            ]
            dash = json.loads(dashboard_body)
        except Exception as e:
            print("DashBoard do not exist, creating one..\n")
            dash = {"widgets": []}

        w = dash["widgets"]

        # Find the current number of widget stacks,
        # so that the next one is added at the end
        len_stacks = len([n for n in w if n["width"] == widget_width["stack"]])

        # iterate over widget_map keys and populate relative widget
        for wd in widget_map:
            w_list = [
                n
                for n, v in enumerate(w)
                if v["properties"]["title"] == widget_title[wd]
            ]

            if wd == "role":
                w_index = len_stacks
                w_type = "stack"
            else:
                w_index = len(w)
                w_type = "global"

            if len(w_list) > 0:
                w_index = w_list[0]

            if resolve_widget_map(wd):
                # if relative metrics exists
                widget = get_widget_base(w_type, w_list, w_index, widget_title[wd], w)
                if wd == "role":
                    # add horizonatal annotations for role widget
                    add_annotations(widget, None)
                for n in widget_map[wd]:
                    for m in metrics[n]:
                        do_insert_metrics(m, widget)
        # END Widgets

        if istack.cfg.debug:
            print(json.dumps(dash, indent=4))
            return

        # Put DashBoard
        out = cw.put_dashboard(
            DashboardName=dashboard_name,
            DashboardBody=json.dumps(dash, separators=(",", ":")),
        )

        if len(out["DashboardValidationMessages"]) > 0:
            pprint(out)
        else:
            print("")
            mylog("CloudWatch-DashBoard[" + dashboard_name + "] Updated:")

        return True

    def mylog(string):
        print(istack.name + " # " + string)

    def add_spot_metric(metric, index):
        label = metric[index]["label"]
        stat = metric[index]["metric"][6]["stat"]
        metric.insert(
            index,
            {
                "name": metric[index]["name"],
                "label": label,
                "metric": [
                    {
                        "visible": True,
                        "expression": f"cpu{stat}Base + cpu{stat}Spot",
                        "label": label,
                        "id": f"cpu{stat}sum",
                    }
                ],
            },
        )
        i = index + 1
        metric.insert(i + 1, deepcopy(metric[i]))

        metric[i]["label"] += " - Base"
        metric[i]["name"] += " - Base"
        metric[i]["metric"][6].update(
            {"visible": False, "id": f"cpu{stat}Base", "label": metric[i]["label"]}
        )

        metric[i + 1]["label"] += " - Spot"
        metric[i + 1]["name"] += " - Spot"
        metric[i + 1]["metric"][6].update(
            {"visible": False, "id": f"cpu{stat}Spot", "label": metric[i + 1]["label"]}
        )
        metric[i + 1]["metric"][3] = res["ServiceSpotName"]

    def get_metrics(res):
        # update widget_title and widget_label
        widget_title["role"] = f"{istack.EnvRole}.{istack.name}"
        title_role = widget_title["role"]

        # Set common variable for ELB Classic and Application used by EC2 stack
        if any(
            n in res for n in ["LoadBalancerNameExternal", "LoadBalancerNameInternal"]
        ):
            LoadBalancerName = "LoadBalancerName"
            LoadBalancerNameExternal = "LoadBalancerNameExternal"
            LoadBalancerNameInternal = "LoadBalancerNameInternal"
            AWS_ELB = "AWS/ELB"
            Latency = "Latency"
            HTTPCode_Backend_5XX = "HTTPCode_Backend_5XX"
            HTTPCode_Backend_4XX = "HTTPCode_Backend_4XX"
            HTTPCode_ELB_5XX = "HTTPCode_ELB_5XX"
            HTTPCode_ELB_4XX = "HTTPCode_ELB_4XX"
        elif any(n in res for n in ["LoadBalancerExternal", "LoadBalancerInternal"]):
            LoadBalancerName = "LoadBalancer"
            LoadBalancerNameExternal = "LoadBalancerExternal"
            LoadBalancerNameInternal = "LoadBalancerInternal"
            AWS_ELB = "AWS/ApplicationELB"
            Latency = "TargetResponseTime"
            HTTPCode_Backend_5XX = "HTTPCode_Target_5XX_Count"
            HTTPCode_Backend_4XX = "HTTPCode_Target_4XX_Count"
            HTTPCode_ELB_5XX = "HTTPCode_ELB_5XX_Count"
            HTTPCode_ELB_4XX = "HTTPCode_ELB_4XX_Count"
        else:
            LoadBalancerName = None
            LoadBalancerNameExternal = None
            LoadBalancerNameInternal = None
            AWS_ELB = None
            Latency = None
            HTTPCode_Backend_5XX = None
            HTTPCode_Backend_4XX = None

        # build empty metrics dict from widget_map
        metrics = {n: [] for m in widget_map.values() for n in m}

        # Is a MIXED stack with both ECS Service and EC2 ASG?
        if all(n in res for n in ["ServiceName", "AutoScalingGroupName"]):
            IS_MIXED = True
        else:
            IS_MIXED = False

        # ECS
        if all(n in res for n in ["ServiceName", "ClusterName"]):
            L_TYPE = " ECS" if IS_MIXED else ""
            # CPU
            label = f"Cpu{L_TYPE} - {istack.cfg.statistic}"
            metrics["cpu"].append(
                {
                    "name": f"Cpu{L_TYPE}",
                    "label": label,
                    "metric": [
                        "AWS/ECS",
                        "CPUUtilization",
                        "ServiceName",
                        res["ServiceName"],
                        "ClusterName",
                        res["ClusterName"],
                        {
                            "period": 300,
                            "stat": istack.cfg.statistic,
                            "label": label,
                        },
                    ],
                }
            )
            # Always add cpu maximum
            label = f"Cpu{L_TYPE} - Maximum"
            metrics["cpu"].append(
                {
                    "name": f"Cpu{L_TYPE} - Maximum",
                    "label": label,
                    "metric": [
                        "AWS/ECS",
                        "CPUUtilization",
                        "ServiceName",
                        res["ServiceName"],
                        "ClusterName",
                        res["ClusterName"],
                        {
                            "period": 300,
                            "stat": "Maximum",
                            "label": label,
                        },
                    ],
                }
            )

            if "ServiceSpotName" in res:
                for n, v in enumerate(list(metrics["cpu"])):
                    add_spot_metric(metrics["cpu"], n * 3)

            # TargetGroups
            for n, v in res.items():
                if n.startswith("TargetGroup") and n.endswith(("External", "Internal")):
                    if n.endswith("External"):
                        suffix = "External"
                    else:
                        suffix = "Internal"

                    tg_name = n.replace("TargetGroup", "")

                    if f"LoadBalancer{suffix}" not in res:
                        continue
                    else:
                        lb_name = f"LoadBalancer{suffix}"

                    # Response Time
                    label = f"Response {tg_name}" f" - {istack.cfg.statisticresponse}"
                    metrics["response"].append(
                        {
                            "name": f"Response {tg_name}",
                            "label": label,
                            "metric": [
                                "AWS/ApplicationELB",
                                "TargetResponseTime",
                                "TargetGroup",
                                res[n],
                                "LoadBalancer",
                                res[lb_name],
                                {
                                    "period": 300,
                                    "stat": istack.cfg.statisticresponse,
                                    "yAxis": "right",
                                    "label": label,
                                },
                            ],
                        }
                    )
                    # Healthy
                    label = f"{title_role}{L_TYPE} - Healthy"
                    metrics["healthy"].append(
                        {
                            "name": f"Healthy{L_TYPE} {tg_name}",
                            "label": label,
                            "metric": [
                                "AWS/ApplicationELB",
                                "HealthyHostCount",
                                "TargetGroup",
                                res[n],
                                "LoadBalancer",
                                res[lb_name],
                                {
                                    "label": label,
                                    "stat": istack.cfg.statistic,
                                    "yAxis": "right",
                                },
                            ],
                        }
                    )
                    # Requests
                    label = f"{title_role} {tg_name} - Requests"
                    metrics["requests"].append(
                        {
                            "name": f"Requests {tg_name}",
                            "label": label,
                            "metric": [
                                "AWS/ApplicationELB",
                                "RequestCount",
                                "TargetGroup",
                                res[n],
                                "LoadBalancer",
                                res[lb_name],
                                {"label": label, "stat": "Sum"},
                            ],
                        }
                    )
                    # 5xx
                    label = f"{title_role} {tg_name} - 5xx"
                    metrics["5xx"].append(
                        {
                            "name": f"5xx {tg_name}",
                            "label": label,
                            "metric": [
                                "AWS/ApplicationELB",
                                "HTTPCode_Target_5XX_Count",
                                "TargetGroup",
                                res[n],
                                "LoadBalancer",
                                res[lb_name],
                                {"label": label, "stat": "Sum"},
                            ],
                        }
                    )
                    # 4xx
                    label = f"{title_role} {tg_name} - 4xx"
                    metrics["4xx"].append(
                        {
                            "name": f"4xx {tg_name}",
                            "label": label,
                            "metric": [
                                "AWS/ApplicationELB",
                                "HTTPCode_Target_4XX_Count",
                                "TargetGroup",
                                res[n],
                                "LoadBalancer",
                                res[lb_name],
                                {"label": label, "stat": "Sum", "yAxis": "right"},
                            ],
                        }
                    )
        if True:
            # EC2
            if all(n in res for n in ["AutoScalingGroupName"]):
                L_TYPE = " EC2" if IS_MIXED else ""
                # CPU
                label = f"Cpu{L_TYPE} - {istack.cfg.statistic}"
                metrics["cpu"].append(
                    {
                        "name": f"Cpu{L_TYPE}",
                        "label": label,
                        "metric": [
                            "AWS/EC2",
                            "CPUUtilization",
                            "AutoScalingGroupName",
                            res["AutoScalingGroupName"],
                            {
                                "period": 300,
                                "stat": istack.cfg.statistic,
                                "label": label,
                            },
                        ],
                    }
                )
                # Always add cpu maximum
                label = f"Cpu{L_TYPE} - Maximum"
                metrics["cpu"].append(
                    {
                        "name": f"Cpu{L_TYPE} - Maximum",
                        "label": label,
                        "metric": [
                            "AWS/EC2",
                            "CPUUtilization",
                            "AutoScalingGroupName",
                            res["AutoScalingGroupName"],
                            {
                                "period": 300,
                                "stat": "Maximum",
                                "label": label,
                            },
                        ],
                    }
                )
                # CPU Spot
                if all(n in res for n in ["AutoScalingGroupSpotName"]):
                    label = f"Cpu{L_TYPE} Spot - {istack.cfg.statistic}"
                    metrics["cpu"].append(
                        {
                            "name": f"Cpu{L_TYPE} Spot",
                            "label": label,
                            "metric": [
                                "AWS/EC2",
                                "CPUUtilization",
                                "AutoScalingGroupName",
                                res["AutoScalingGroupSpotName"],
                                {
                                    "period": 300,
                                    "stat": istack.cfg.statistic,
                                    "label": label,
                                },
                            ],
                        }
                    )
                # Healthy
                label = f"{title_role}{L_TYPE} - Healthy"
                metrics["healthy"].append(
                    {
                        "name": f"Healthy{L_TYPE}",
                        "label": label,
                        "metric": [
                            "AWS/AutoScaling",
                            "GroupInServiceInstances",
                            "AutoScalingGroupName",
                            res["AutoScalingGroupName"],
                            {
                                "label": label,
                                "stat": istack.cfg.statistic,
                                "yAxis": "right",
                            },
                        ],
                    }
                )
                # Network
                label = f"{title_role} - NetworkIN"
                metrics["netin"].append(
                    {
                        "name": "NetworkIN",
                        "label": label,
                        "metric": [
                            "AWS/EC2",
                            "NetworkIn",
                            "AutoScalingGroupName",
                            res["AutoScalingGroupName"],
                            {"label": label, "period": 300, "stat": "Sum"},
                        ],
                    }
                )
                label = f"{title_role} - NetworkOUT"
                metrics["netout"].append(
                    {
                        "name": "NetworkOUT",
                        "label": label,
                        "metric": [
                            "AWS/EC2",
                            "NetworkOut",
                            "AutoScalingGroupName",
                            res["AutoScalingGroupName"],
                            {
                                "label": label,
                                "period": 300,
                                "stat": "Sum",
                                "yAxis": "right",
                            },
                        ],
                    }
                )

            # ELB
            for n in ["External", "Internal"]:
                res_name = locals()[f"LoadBalancerName{n}"]

                if res_name in res and "ServiceName" not in res:
                    # Response
                    label = f"Response {n} - {istack.cfg.statisticresponse}"
                    metrics["response"].append(
                        {
                            "name": f"Response {n}",
                            "label": label,
                            "metric": [
                                AWS_ELB,
                                Latency,
                                LoadBalancerName,
                                res[res_name],
                                {
                                    "period": 300,
                                    "stat": istack.cfg.statisticresponse,
                                    "yAxis": "right",
                                    "label": label,
                                },
                            ],
                        }
                    )
                    # Requests
                    label = f"{title_role} {n} - Requests"
                    metrics["requests"].append(
                        {
                            "name": f"Requests {n}",
                            "label": label,
                            "metric": [
                                AWS_ELB,
                                "RequestCount",
                                LoadBalancerName,
                                res[res_name],
                                {"label": label, "stat": "Sum"},
                            ],
                        }
                    )
                    # 5xx
                    label = f"{title_role} {n} - 5xx"
                    metrics["5xx"].append(
                        {
                            "name": f"5xx {n}",
                            "label": label,
                            "metric": [
                                AWS_ELB,
                                HTTPCode_Backend_5XX,
                                LoadBalancerName,
                                res[res_name],
                                {"label": label, "stat": "Sum"},
                            ],
                        }
                    )
                    # 4xx
                    label = f"{title_role} {n} - 4xx"
                    metrics["4xx"].append(
                        {
                            "name": f"4xx {n}",
                            "label": label,
                            "metric": [
                                AWS_ELB,
                                HTTPCode_Backend_4XX,
                                LoadBalancerName,
                                res[res_name],
                                {"label": label, "stat": "Sum", "yAxis": "right"},
                            ],
                        }
                    )
                    # 5xx ELB
                    label = f"{title_role} {n} - 5xx"
                    metrics["5xx_elb"].append(
                        {
                            "name": f"5xx {n} ELB",
                            "label": label,
                            "metric": [
                                AWS_ELB,
                                HTTPCode_ELB_5XX,
                                LoadBalancerName,
                                res[res_name],
                                {"label": label, "stat": "Sum"},
                            ],
                        }
                    )
                    # 4xx ELB
                    label = f"{title_role} {n} - 4xx"
                    metrics["4xx_elb"].append(
                        {
                            "name": f"4xx {n} ELB",
                            "label": label,
                            "metric": [
                                AWS_ELB,
                                HTTPCode_ELB_4XX,
                                LoadBalancerName,
                                res[res_name],
                                {"label": label, "stat": "Sum", "yAxis": "right"},
                            ],
                        }
                    )

                    # 50x ELB
                    if f"LoadBalancer{n}" in res:
                        # 500
                        label = f"{title_role} {n} - 500"
                        metrics["500_elb"].append(
                            {
                                "name": f"500 {n} ELB",
                                "label": label,
                                "metric": [
                                    "AWS/ApplicationELB",
                                    "HTTPCode_ELB_500_Count",
                                    "LoadBalancer",
                                    res[res_name],
                                    {
                                        "label": label,
                                        "stat": "Sum",
                                        "yAxis": (
                                            "right" if n == "Internal" else "left"
                                        ),
                                    },
                                ],
                            }
                        )
                        # 502
                        label = f"{title_role} {n} - 502"
                        metrics["502_elb"].append(
                            {
                                "name": f"502 {n} ELB",
                                "label": label,
                                "metric": [
                                    "AWS/ApplicationELB",
                                    "HTTPCode_ELB_502_Count",
                                    "LoadBalancer",
                                    res[res_name],
                                    {
                                        "label": label,
                                        "stat": "Sum",
                                        "yAxis": (
                                            "right" if n == "Internal" else "left"
                                        ),
                                    },
                                ],
                            }
                        )
                        # 503
                        label = f"{title_role} {n} - 503"
                        metrics["503_elb"].append(
                            {
                                "name": f"503 {n} ELB",
                                "label": label,
                                "metric": [
                                    "AWS/ApplicationELB",
                                    "HTTPCode_ELB_503_Count",
                                    "LoadBalancer",
                                    res[res_name],
                                    {
                                        "label": label,
                                        "stat": "Sum",
                                        "yAxis": (
                                            "right" if n == "Internal" else "left"
                                        ),
                                    },
                                ],
                            }
                        )
                        # 504
                        label = f"{title_role} {n} - 504"
                        metrics["504_elb"].append(
                            {
                                "name": f"504 {n} ELB",
                                "label": label,
                                "metric": [
                                    "AWS/ApplicationELB",
                                    "HTTPCode_ELB_504_Count",
                                    "LoadBalancer",
                                    res[res_name],
                                    {
                                        "label": label,
                                        "stat": "Sum",
                                        "yAxis": (
                                            "right" if n == "Internal" else "left"
                                        ),
                                    },
                                ],
                            }
                        )

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

    print("")
    # update dashboards
    update_dashboard(res, istack.cfg.dash_name)


def update(istack):
    cw_client = istack.boto3.client("cloudwatch")
    response_dash = cw_client.list_dashboards(DashboardNamePrefix="_")

    resources.set_changed(istack)
    if istack.cfg.dashboard == "OnChange":
        res_changed = istack.changed["resources"]
        mode = ""
    elif istack.cfg.dashboard in ["Always", "Generic"]:
        res_changed = istack.after["resources"]
        mode = istack.cfg.dashboard
    else:
        return

    if res_changed or any(
        n in istack.changed["outputs"]
        for n in [
            "ScalingPolicyTrackings",
            "AutoScalingScalingPolicy",
            "ApplicationAutoScalingScalingPolicy",
        ]
    ):
        for dash in response_dash["DashboardEntries"]:
            if istack.name in dash["DashboardName"]:
                istack.cfg.dash_name = dash["DashboardName"]
                add_stack(istack)
