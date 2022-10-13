# py libs
import threading

# carwash libs
from edge_services_camlib import edge_services

class EventSender(threading.Thread):
    
    def __init__(self, logger, cameras_id, message1, message2, event_type):
        self.cameras_id = cameras_id
        self.logger = logger
        self.message1 = message1
        self.message2 = message2
        self.event_type = event_type
        super().__init__()
        pass
        
    # sends the alert directly to the controller, first converts image
    def run(self):
        try:
            if self.event_type == "event":
                edge_services.send_event(f"cam{self.cameras_id}", self.message1)

            if self.event_type == "report":
                edge_services.send_log(self.message2,"report")

        except Exception as e:
            self.logger.info("error sending event: ",str(e))
