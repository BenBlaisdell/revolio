import datetime as dt


class Elements:

    def __init__(self, elem_srv, log):
        self._elem_srv = elem_srv,
        self._log = log

    def handle_request(self, request):
        self._log.info('Handling request: Subscribe')

        subscription_id = request['SubscriptionId']
        assert isinstance(subscription_id, str)

        # make call
        elems = self(subscription_id=subscription_id)

        # format response
        return {
            'SubscriptionId': subscription_id,
            'Elements': [
                {
                    'Id': elem.id,
                    'Bucket': elem.bucket,
                    'Key': elem.key,
                    'Size': elem.size,
                    'Created': dt.datetime.strftime(elem.created, '%Y-%m-%d %H:%M:%S'),
                }
                for elem in elems
            ],
        }


    def __call__(self, subscription_id):
        self._log.info('Handling call: Elements')
        return self._elem_srv.get_sub_elems_by_id(sub_id=subscription_id)
