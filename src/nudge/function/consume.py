from nudge.entity.element import Element


class Consume:

    def __init__(self, log, elem_srv, session):
        self._log = log
        self._elem_srv = elem_srv
        self._session = session

    def __call__(self, elem_ids):
        for elem in self._elem_srv.get_elements(elem_ids):
            self._check_state(elem)
            elem.state = Element.State.Consumed

        self._session.commit()

    def _check_state(self, elem):
        if elem.state != Element.State.Sent:
            self._log.warning('Consuming element {} in state {}'.format(elem.id, elem.state))
