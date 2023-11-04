from django.db import models
from django.utils import timezone
import datetime
import random

MAX_SESSION_ID=9223372036854775807

class ActiveSession(models.Model):
    session_id = models.PositiveIntegerField(primary_key=True)
    start_time = models.DateTimeField()
    src_ip = models.CharField(max_length=15)
    
    def older_than_x_days(self, x_days):
        return self.start_time <= timezone.now() - datetime.timedelta(days=x_days)
    
    def older_than_one_day(self):
        return self.older_than_x_days(1)
    
    def __str__(self):
        return f"Session ({self.session_id}) started at {self.start_time}"
    
def get_new_valid_session_id()->int:
    activeIds=[s.session_id for s in ActiveSession.objects.all()]
    trial_id=random.randint(1,MAX_SESSION_ID)
    while trial_id in activeIds:
        trial_id+=1
        trial_id%=MAX_SESSION_ID
    return trial_id
    
class Wp3_Authentication_Token(models.Model):
    session = models.ForeignKey(ActiveSession, on_delete=models.CASCADE)
    token = models.CharField(max_length=2000)
    issued_at = models.DateTimeField()
    
    def __str__(self):
        partial_token=self.token[0:5]
        return f"token ({partial_token}*...*) for session {self.session.session_id}, issued at {self.issued_at}"

class User_Action(models.Model):
    placeholder = models.CharField(max_length=2000)
    time_stamp = models.DateTimeField()
    
    def __str__(self):
        return f"{self.placeholder} at {self.time_stamp}"
    

