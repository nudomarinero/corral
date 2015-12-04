#!/usr/bin/env python
# -*- coding: utf-8 -*-

import inspect
import datetime
import collections

from .. import conf, db, util, exceptions
from ..db.default_models import Alerted
from ..core import logger

from .base import Processor, Runner


# =============================================================================
# ALERT CLASSES
# =============================================================================

class AlertRunner(Runner):

    def validate_target(self, alert_cls):
        if not (inspect.isclass(alert_cls) and issubclass(alert_cls, Alert)):
            msg = "alert_cls '{}' must be subclass of 'corral.run.Alert'"
            raise TypeError(msg.format(alert_cls))

    def run(self):
        alert_cls = self.target
        logger.info("Executing alert '{}'".format(alert_cls))
        with db.session_scope() as session, alert_cls(session) as alert:
            for obj in alert.generate():
                alert.validate(obj)

                generator = alert.process(obj) or []
                if not hasattr(generator, "__iter__"):
                    generator = (generator,)
                for proc_obj in generator:
                    alert.validate(proc_obj)
                    alert.save(proc_obj)
        logger.info("Done!")


class Alert(Processor):

    runner_class = AlertRunner

    model = None
    conditions = None

    ordering = None
    offset, limit = None, None

    auto_register = True

    def setup(self):
        map(lambda ep: ep.setup(self), self.alert_to)

    def teardown(self, type, value, traceback):
        map(lambda ep: ep.teardown(), self.alert_to)

    def generate(self):
        if self.model is None or self.conditions is None:
            clsname = type(self).__name__
            raise NotImplementedError(
                "'{}' subclass with a default generate must redefine "
                "'model' and 'conditions' class-attributes".format(clsname))

        query = self.session.query(self.model).filter(*self.conditions)

        if self.auto_register:
            filters = Alerted.alert_to_columns(type(self))
            filters.update(Alerted.model_class_to_column(self.model))
            alerteds = self.session.query(
                Alerted.model_ids).filter_by(**filters)
            if alerteds.count():
                grouped_id = collections.defaultdict(set)
                for d in map(lambda r: Alerted.loads(r[0]), alerteds.all()):
                    for k, v in d.iteritems():
                        grouped_id[k].add(v)
                exclude = []
                for k, v in grouped_id.items():
                    exclude.append(getattr(self.model, k).in_(v))
                query = query.filter(~db.and_(*exclude))

        if self.ordering is not None:
            query = query.order_by(*self.ordering)
        if self.offset is not None:
            query = query.offset(self.offset)
        if self.limit is not None:
            query = query.limit(self.limit)
        return query

    def process(self, obj):
        map(lambda ep: ep.process(obj), self.alert_to)
        if self.auto_register:
            register = Alerted()
            register.alert = type(self)
            register.model = obj
            register.created_at = datetime.datetime.utcnow()
            yield register


# =============================================================================
# FUNCTIONS
# =============================================================================

def load_alerts():
    steps = []
    logger.debug("Loading Alert Classes")
    for import_string in conf.settings.ALERTS:
        cls = util.dimport(import_string)
        if not (inspect.isclass(cls) and issubclass(cls, Alert)):
            msg = "STEP '{}' must be subclass of 'corral.run.Alert'"
            raise exceptions.ImproperlyConfigured(msg.format(import_string))
        steps.append(cls)
    return tuple(steps)


def execute_alert(alert_cls, sync=False):
    if not (inspect.isclass(alert_cls) and issubclass(alert_cls, Alert)):
        msg = "alert_cls '{}' must be subclass of 'corral.run.Alert'"
        raise TypeError(msg.format(alert_cls))

    runner = alert_cls.runner_class()
    runner.set_target(alert_cls)
    if sync:
        runner.run()
    else:
        runner.start()
    return runner
