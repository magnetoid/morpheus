from django.urls import path

from plugins.installed.cms import views

app_name = 'cms'

urlpatterns = [
    # CMS Page resolver — must be mounted last so concrete routes win.
    path('p/<slug:slug>/', views.page_view, name='page'),
    path('forms/<slug:key>/submit/', views.form_submit, name='form_submit'),
]
