import revolio as rv

from nudge.core.entity import Element


class Consume(rv.Function):

    def __init__(self, ctx, log, elem_srv, db):
        super().__init__(ctx)
        self._log = log
        self._elem_srv = elem_srv
        self._db = db

    def format_request(self, elem_ids):
        return {
            'ElementIds': elem_ids,
        }

    def handle_request(self, request):
        self._log.info('Handling request: Consume')

        # parse parameters

        element_ids = request['ElementIds']
        assert isinstance(element_ids, list)

        # make call

        self(element_ids)

        # format response

        return {'Message': 'Success'}

    def __call__(self, elem_ids):
        self._log.info('Handling call: Consume')

        for elem in self._elem_srv.get_elements(elem_ids):
            self._check_state(elem)
            elem.state = Element.State.Consumed

        self._db.commit()

    def _check_state(self, elem):
        if elem.state != Element.State.Batched:
            self._log.warning('Consuming element {} in state {}'.format(elem.id, elem.state))
