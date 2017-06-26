import json


class PingService:

    def __init__(self):
        pass

    @staticmethod
    def get_ping_data(sub):
        if sub.trigger.custom is not None:
            return json.loads(sub.trigger.custom)

        return PingService.get_default_ping_data(sub.id)

    @staticmethod
    def get_default_ping_data(sub_id):
        return {
            'SubscriptionId': sub_id,
        }
