#!/usr/bin/env python3
from prettytable import (
    PrettyTable,
    ALL as ptALL,
    FRAME as ptFRAME,
    HEADER as ptHEADER,
    NONE as ptNONE,
)
from . import cfg
from .log import logger
from .common import *


def get(data):
    fields = cfg.fields
    table = PrettyTable()
    table.padding_width = 1
    table.field_names = fields
    for n in data:
        parameter_not_empty = n.get("parameter_not_empty", [])
        table.add_row(
            [
                "Null"
                if (i not in n or not n[i])
                else f"{n[i]} *"
                if i in parameter_not_empty
                else n[i]
                for i in fields
            ]
        )

    table.sortby = fields[0]
    table.reversesort = True
    table.align = "l"

    if cfg.output == "html":
        table.format = True

        return table.get_html_string(fields=fields)

    if cfg.output == "bare":
        table.header = False
        table.border = False
        table.left_padding_width = 0
        table.padding_width = 1

    return table.get_string(fields=fields)
