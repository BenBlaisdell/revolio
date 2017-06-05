import revolio as rv


class GetSubscriptionBatches(rv.Function):

    def __init__(self, ctx, log, batch_srv, db):
        super().__init__(ctx)
        self._log = log
        self._batch_srv = batch_srv
        self._db = db

    def format_request(self, sub_id, *, prev_id=False):
        return {
            'SubscriptionId': sub_id,
            'PreviousBatchId': prev_id,
        }

    def handle_request(self, request):
        self._log.info('Handling request: GetSubscriptionBatches')

        # parse parameters

        sub_id = request['SubscriptionId']
        assert isinstance(sub_id, str)

        prev_id = request.get('PreviousBatchId', None)
        assert isinstance(prev_id, str) or (prev_id is None)

        # make call

        batches = self(
            sub_id=sub_id,
            prev_id=prev_id,
        )

        # format response

        return {
            'BatchIds': [batch.id for batch in batches],
        }

    def __call__(self, sub_id, *, prev_id=None):
        self._log.info('Handling call: GetSubscriptionBatches')
        batches = self._batch_srv.get_subscription_batches(sub_id, prev_id)
        self._db.commit()
        return batches
