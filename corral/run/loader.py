#!/usr/bin/env python
# -*- coding: utf-8 -*-

import inspect

import six

from .. import conf, db, util, exceptions
from ..core import logger

from .base import Processor, Runner


# =============================================================================
# LOADER CLASSES
# =============================================================================

class LoaderRunner(Runner):

    def validate_target(self, loader_cls):
        if not (inspect.isclass(loader_cls) and
                issubclass(loader_cls, Loader)):
            msg = "loader_cls '{}' must be subclass of 'corral.run.Loader'"
            raise TypeError(msg.format(loader_cls))

    def run(self):
        loader_cls, proc = self.target, self.current_proc
        logger.info("Executing loader '{}' #{}".format(loader_cls, proc+1))
        with db.session_scope() as session, loader_cls(session, proc) as ldr:
            generator = ldr.generate()
            for obj in (generator or []):
                ldr.validate(obj)
                ldr.save(obj)
        logger.info("Done Loader '{}' #{}".format(loader_cls, proc+1))


class Loader(Processor):

    runner_class = LoaderRunner

    @classmethod
    def retrieve_python_path(cls):
        return conf.settings.LOADER


# =============================================================================
# FUNCTIONS
# =============================================================================

def load_loader():
    logger.debug("Loading Loader Class")
    import_string = conf.settings.LOADER
    cls = util.dimport(import_string)
    if not (inspect.isclass(cls) and issubclass(cls, Loader)):
        msg = "LOADER '{}' must be subclass of 'corral.run.Loader'"
        raise exceptions.ImproperlyConfigured(msg.format(import_string))
    return cls


def execute_loader(loader_cls, sync=False):

    if not (inspect.isclass(loader_cls) and issubclass(loader_cls, Loader)):
        msg = "loader_cls '{}' must be subclass of 'corral.run.Loader'"
        raise TypeError(msg.format(loader_cls))

    procs = []
    loader_cls.class_setup()
    for proc in six.moves.range(loader_cls.get_procno()):
        runner = loader_cls.runner_class()
        runner.setup(loader_cls, proc)
        if sync:
            runner.run()
        else:
            db.engine.dispose()
            runner.start()
        procs.append(runner)
    return tuple(procs)
