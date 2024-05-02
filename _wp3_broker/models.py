from django.db import models
from lelantos_base.models import Session

TIME_FORMAT="%m/%d/%Y-%H:%M:%S"
# // Deprecated - useful if wifipumpkin improve kali distro
class Wp3_Authentication_Token(models.Model):
    session = models.OneToOneField(Session, on_delete=models.CASCADE)
    token = models.CharField(max_length=2000)
    issued_at = models.DateTimeField()
    
    def __str__(self):
        partial_token=self.token[0:5]
        time_formated=self.issued_at.strftime(TIME_FORMAT)
        return f"token ({partial_token}*...*) for session {self.session.session_id}, issued at {time_formated}"
