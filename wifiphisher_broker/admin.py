from django.contrib import admin

from .models import Credential_Result, Device_Instance, Wifiphisher_Captive_Portal_Session

admin.site.register(Credential_Result)
admin.site.register(Device_Instance)
admin.site.register(Wifiphisher_Captive_Portal_Session)

