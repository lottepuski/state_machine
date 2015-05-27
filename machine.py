__author__ = 'aravind'

DOCUMENTATION = \
    """
    The syntax of the state machine can be expressed by the following structure:
    {
        "initial": "initial state of the state machine",
        "events" : [
            {
                "action": "name"
                "src" : "src1",
                "dst" : "dst1"
            },
            {
                "action": "name1"
                "src" : ["src1", "src2"]
                "dst" : "dst1"
                "callbacks" : {
                    "on_before": before_handler,
                    "on_event": event_handler,
                    "on_after": after_handler
                }
            },
            {
                "action": "name2"
                "src" : ["src1", "src2"]
                "dst" : ["dst1", "dst3", "dst4"],
                "callbacks" : {
                    "on_before": before_handler,
                    "on_event": event_handler,
                    "on_after": after_handler
                }
            }
        ],
        "callbacks" : {
            "on_before": before_handler,
            "on_event": event_handler,
            "on_after": after_handler
        }
    }

    A note on the callbacks:
    - If an action has a single destination state then the destination is always
      chosen irrespective of the value of the on_event handler (local or global)
    - In case an action has multiple destination states then the on_event callback
     must return the correct destination state
    - on_before and on_after may be used to cancel the transition to the current
     state and terminate the state machine if necessary
    """

EVENTS = "events"
CALLBACKS = "callbacks"
INITIAL = "initial"
ON_EVENT = "on_event"
ON_AFTER = "on_after"
ON_BEFORE = "on_before"
ACTION = "action"
SRC = "src"
DST = "dst"


class TransitionError(Exception):
    def __init__(self, msg):
        self.msg = msg


class Machine(object):
    def __init__(self, desc):
        self.desc = desc
        self.current = None
        self.parse_desc()

    def parse_desc(self):
        if self.desc.has_key(INITIAL):
            self.current = self.desc[INITIAL]
        if self.desc.has_key(CALLBACKS):
            self.register_global_callbacks(self.desc[CALLBACKS])
        for event in self.desc[EVENTS]:
            self.register_event(event)

    def register_global_callbacks(self, global_cb):
        """ Global callbacks are overridden by event specific callbacks
        :return: None
        """
        for name, value in global_cb.iteritems():
            setattr(self, name, value)

    def register_event(self, event):
        setattr(self, event[ACTION], self.build_event(event))

    def build_event(self, event):
        # noinspection PyPep8Naming
        def fn(*args, **kwargs):
            class e(object):
                pass

            e_obj = e()

            src = self.current

            e.src = src
            e.event = event[ACTION]
            for k in kwargs:
                setattr(e, k, kwargs[k])
            setattr(e_obj, 'args', args)
            fn.__name__ = event[ACTION]

            fn_before = self.get_current_or_global(event, ON_BEFORE)
            fn_event = self.get_current_or_global(event, ON_EVENT)
            fn_after = self.get_current_or_global(event, ON_AFTER)
            self.safe_call_fn(fn_before, e_obj)
            dst = self.safe_call_fn(fn_event, e_obj, raise_error=True)
            self.safe_call_fn(fn_after, e_obj)

            self.safe_set_current(dst, event)

        return fn

    def get_current_or_global(self, event, event_type):
        """ Return the event specific callback if it exists
            or return global callback.
        :param event: dictionary with keys : actions, src, dst, [callbacks]
        :param event_type:  callback type, one of : on_before, on_event, on_after
        :return:    callback function
        """
        if event.has_key(CALLBACKS) and event[CALLBACKS].has_key(event_type):
            return event[CALLBACKS][event_type]
        elif hasattr(self, event_type):
            return getattr(self, event_type, None)

    def safe_call_fn(self, fn, e_obj, raise_error=False):
        """ Call function
        :param fn:
        :param e_obj:
        :param raise_error:
        :return:
        """
        if hasattr(fn, '__call__'):
            return fn(e_obj)
        elif raise_error:
            msg = "Callback {} is not callable.\nEvent details: source {}"
            raise TransitionError(msg.format(fn, e_obj))

    def safe_set_current(self, dst, event):
        """ If event[EVENT] is a list then use return value of on_event to
        :param dst:
        :param event:
        :return:
        """
        if isinstance(event[DST], list):
            self.current = dst
        else:
            self.current = event[DST]
