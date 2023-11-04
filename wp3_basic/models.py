from django.db import models
from django.utils import timezone
import datetime
import random
from django.contrib.auth.models import User

MAX_SESSION_ID=9223372036854775807
TIME_FORMAT="%m/%d/%Y-%H:%M:%S"

class Session(models.Model):
    session_id = models.PositiveIntegerField(primary_key=True)
    user = models.ForeignKey(User, on_delete=models.CASCADE)
    start_time = models.DateTimeField()
    end_time = models.DateTimeField(null=True)
    src_ip = models.CharField(max_length=15)
    active = models.BooleanField()
    
    def older_than_x_days(self, x_days):
        return self.start_time <= timezone.now() - datetime.timedelta(days=x_days)
    
    def older_than_one_day(self):
        return self.older_than_x_days(1)
    
    def __str__(self):
        time_formated=self.start_time.strftime(TIME_FORMAT)
        return f"Session ({self.session_id}) started at {time_formated}, from src_ip: {self.src_ip}"
    
def get_new_valid_session_id()->int:
    activeIds=[s.session_id for s in Session.objects.all()]
    trial_id=random.randint(1,MAX_SESSION_ID)
    while trial_id in activeIds:
        trial_id+=1
        trial_id%=MAX_SESSION_ID
    return trial_id
    
class Wp3_Authentication_Token(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    token = models.CharField(max_length=2000)
    issued_at = models.DateTimeField()
    
    def __str__(self):
        partial_token=self.token[0:5]
        time_formated=self.issued_at.strftime(TIME_FORMAT)
        return f"token ({partial_token}*...*) for session {self.session.session_id}, issued at {time_formated}"

class User_Action(models.Model):
    session = models.ForeignKey(Session, on_delete=models.CASCADE)
    placeholder = models.CharField(max_length=2000)
    time_stamp = models.DateTimeField()
    
    def __str__(self):
        time_formated=self.time_stamp.strftime(TIME_FORMAT)
        return f"{self.placeholder} at {time_formated}"
    

