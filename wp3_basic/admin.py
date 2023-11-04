from django.contrib import admin

from .models import ActiveSession, Wp3_Authentication_Token, User_Action

admin.site.register(ActiveSession)
admin.site.register(Wp3_Authentication_Token)
admin.site.register(User_Action)


