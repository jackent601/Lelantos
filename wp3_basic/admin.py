from django.contrib import admin

from .models import Session, Wp3_Authentication_Token, User_Action

admin.site.register(Session)
admin.site.register(Wp3_Authentication_Token)
admin.site.register(User_Action)


