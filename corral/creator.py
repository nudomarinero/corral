#!/usr/bin/env python
# -*- coding: utf-8 -*-

import keyword
import string
import codecs
import datetime
import os
import re
import glob

import six

from . import core
from .exceptions import ValidationError


# =============================================================================
# CONSTANTS
# =============================================================================

KEYWORDS = frozenset(keyword.kwlist)

BUILTINS = frozenset(dir(six.moves.builtins))

FORBIDEN_WORDS = frozenset(
    ("True", "False", "None", "corral", "__builtins__", "builtins",
    "models", "tests", "command", "migrations", "in_corral.py", "in_corral",
    "settings", "load", "steps", "__init__"))

IDENTIFIER = re.compile(r"^[^\d\W]\w*\Z", re.UNICODE)

PATH = os.path.abspath(os.path.dirname(__file__))

PIPELINE_TEMPLATE_PATH = os.path.join(PATH, "template")

PIPELINE_TEMPLATE_GLOB = os.path.join(PIPELINE_TEMPLATE_PATH, "*.py")

TEMPLATES = [
    (os.path.basename(fn), fn)
    for fn in glob.glob(PIPELINE_TEMPLATE_GLOB)
    if os.path.basename(fn) != "in_corral.py"]

IN_CORRAL_TEMPLATE = os.path.join(PIPELINE_TEMPLATE_PATH, "in_corral.py")


# =============================================================================
# LOGGER
# =============================================================================

logger = core.logger


# =============================================================================
# FUNCTIONS
# =============================================================================

def validate_name(name):
    msg = "'{}' is a {}"
    if name in KEYWORDS:
        raise ValidationError(msg.format(name, "keyword"))
    elif name in BUILTINS:
        raise ValidationError(msg.format(name, "builtin"))
    elif name in FORBIDEN_WORDS:
        raise ValidationError(msg.format(name, "forbiden word"))
    elif not re.match(IDENTIFIER, name):
        raise ValidationError("Invalid identifier '{}'".format(name))


def create_pipeline(path):
    fpath = os.path.abspath(path)
    basename = os.path.basename(path)

    validate_name(basename)

    if os.path.isdir(fpath):
        raise ValidationError("directory '{}' already exists".format(fpath))

    logger.info("Creating pipelin in '{}'...".format(fpath))
    os.makedirs(fpath)

    context = {
        "project_name": basename,
        "timestamp": datetime.datetime.now().isoformat(),
        "version": core.get_version()}

    for tpl_name, tpl_path in TEMPLATES:
        logger.info("Creating file '{}'...".format(tpl_name))
        with codecs.open(tpl_path, encoding="utf-8") as fp:
            tpl = string.Template(fp.read())

        src = tpl.safe_substitute(context)
        path = os.path.join(fpath, tpl_name)
        with codecs.open(path, "w", encoding="utf-8") as fp:
            fp.write(src)

    logger.info("Creating manager...")
    with codecs.open(IN_CORRAL_TEMPLATE, encoding="utf-8") as fp:
        tpl = string.Template(fp.read())

    src = tpl.safe_substitute(context)
    path = os.path.join(fpath, "..", "in_corral.py")
    with codecs.open(path, "w", encoding="utf-8") as fp:
        fp.write(src)

    logger.info("Success!")
