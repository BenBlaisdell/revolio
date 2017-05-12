from nudge.entity.element import ElementState


class Consume:

    def __init__(self, log, elem_srv):
        self._log = log
        self._elem_srv = elem_srv

    def __call__(self, elem_ids):
        for elem in self._elem_srv.get_elements(elem_ids):
            self._check_state(elem)
            self._elem_srv.mark_consumed(elem)

    def _check_state(self, elem):
        if elem.state != ElementState.Sent:
            self._log.warning('Consuming element {} in state {}'.format(elem.id, elem.state))
