class Unsubscribe:

    def __init__(self, sub_srv):
        self._sub_srv = sub_srv

    def __call__(self, sub_id):
        self._sub_srv.deactivate(sub_id)
