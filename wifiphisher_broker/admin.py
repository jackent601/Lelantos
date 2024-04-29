from django.contrib import admin

from .models import Wifiphisher_Captive_Portal_Session, Credential_Result, Device_Instance

admin.site.register(Credential_Result)
admin.site.register(Device_Instance)
admin.site.register(Wifiphisher_Captive_Portal_Session)

