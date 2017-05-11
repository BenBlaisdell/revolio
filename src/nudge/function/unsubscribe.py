class Unsubscribe:

    def __init__(self, session, sub_srv):
        self._session = session
        self._sub_srv = sub_srv

    def __call__(self, sub_id):
        self._sub_srv.deactivate(sub_id)
        self._session.commit()
