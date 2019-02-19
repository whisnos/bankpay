from django import forms


class DeviceLoginForm(forms.Form):
    username = forms.CharField(required=True, error_messages={
        'required': '设备名必填',
    })
    login_token = forms.CharField(required=True, error_messages={
        'required': '登陆码必填',
    })
