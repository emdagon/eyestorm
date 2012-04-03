
from eyestorm.objects import Entity, Collection


class Session(Entity):


    def __init__(self, handler):
        super(Session, self).__init__((handler.application.settings.get(
                                                'sessions_store_collection',
                                                "_eyestorm_sessions")))



class Sessions(Collection):


    def __init__(self):
        super(Sessions, self).__init__("sessions")
