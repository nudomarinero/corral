#!/usr/bin/env python
# -*- coding: utf-8 -*-

# =============================================================================
# IMPORT
# =============================================================================

import sys
import datetime
import codecs

import jinja2

import sadisplay

from . import cli, core, res, setup, run, util, db


# =============================================================================
# FUNCTIONS
# =============================================================================

def models_diagram(fmt="dot"):
    default_models = db.load_default_models()

    parsers = {
        "dot": sadisplay.dot,
        "plantuml": sadisplay.plantuml,
    }
    parser = parsers[fmt]

    models = [
        m for m in util.collect_subclasses(db.Model)
        if sys.modules[m.__module__] != default_models]

    desc = sadisplay.describe(
        models,
        show_methods=True,
        show_properties=True,
        show_indexes=True)

    return parser(desc)


def create_doc(processors, models, doc_formatter=None):

    if doc_formatter is None:
        def doc_formatter(string):
            lines = [s.strip() for s in string.splitlines()]
            return "\n".join(lines)

    path = res.fullpath("doc_template.md")
    with codecs.open(path, encoding="utf8") as fp:
        template = jinja2.Template(fp.read())

    loader, steps, alerts = None, [], []
    for proc in processors:
        if issubclass(proc, run.Loader):
            loader = proc
        elif issubclass(proc, run.Step):
            steps.append(proc)
        elif issubclass(proc, run.Alert):
            alerts.append(proc)

    cli_help = cli.create_parser().main_help_text(0)

    ctx = {
        "doc_formatter": doc_formatter,
        "now": datetime.datetime.now(), "core": core,
        "pipeline_setup": setup.load_pipeline_setup(), "cli_help": cli_help,
        "models": models, "loader": loader, "steps": steps, "alerts": alerts}

    return template.render(**ctx)
