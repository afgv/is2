# definicion/urls.py
from django.urls import path
from django.conf.urls import url
from . import views
from django.contrib.auth.decorators import login_required

urlpatterns = [
    #path('crear_proyecto/', login_required(views.CrearProyecto.as_view()), name='crear_proyecto'),
    path('crear_proyecto/', login_required(views.ProjectCreate.as_view()), name='crear_proyecto'),
    path('proyectos/', login_required(views.Proyectos.as_view(),login_url='login'), name='proyectos'),
#    path('miembros',login_required(views.AgregarMiembro,login_url='login'), name='miembros'),
]
