# definicion/views.py
from django.core.exceptions import PermissionDenied
from guardian.mixins import PermissionRequiredMixin

from definicion.models import Proyecto
from django.urls import reverse_lazy
from django.views import generic
from definicion.forms import ProyectoCreationForm
from django.shortcuts import render
from django.http.response import HttpResponseRedirect
from django.contrib.auth import login
from django.contrib.auth.decorators import login_required
from django.utils.decorators import method_decorator
from django.views.generic import TemplateView

class GlobalPermissionRequiredMixin(PermissionRequiredMixin):
    '''
    Mixin que permite requerir un permiso
    '''
    accept_global_perms = True
    return_403 = True
    raise_exception = True


class CreateViewPermissionRequiredMixin(GlobalPermissionRequiredMixin):
    '''
    Mixin que permite requerir un permiso
    '''

    def get_object(self):
        return None


class ActiveProjectRequiredMixin(object):
    proyecto = None

    def get_proyecto(self):
        return self.proyecto

    def dispatch(self, request, *args, **kwargs):
        proyecto = self.get_proyecto()
        if proyecto.estado != 'AP':
            return super(ActiveProjectRequiredMixin, self).dispatch(request, *args, **kwargs)
        raise PermissionDenied()

"""
@login_required()
def home(request):
    """ """
    Vista para la pantalla principal.
    """ """
    context = {}
    context['users_count'] = User.objects.count()
    context['proyects'] = Proyecto.objects.all()
    context['plantillas_count'] = Flujo.objects.filter(proyecto=None).count()
    context['us_count'] = request.user.userstory_set.count()

    return render(request, 'project/home.html', context)
"""

def get_selected_perms(POST):
    """
    Obtener los permisos marcados en el formulario

    :param POST: diccionario con los datos del formulario
    :return: lista de permisos
    """
    current_list = POST.getlist('perms_proyecto')
    current_list.extend(POST.getlist('perms_userstory'))
    current_list.extend(POST.getlist('perms_flujo'))
    current_list.extend(POST.getlist('perms_sprint'))
    return current_list

@method_decorator(login_required, name='dispatch')
class CrearProyecto(generic.CreateView):

    form_class = ProyectoCreationForm
    success_url = reverse_lazy('proyectos')
    template_name = 'definicion/crear_proyecto.html'


    def form_valid(self, form):
        login(self.request, form.get_user())
        return super(CrearProyecto, self).form_valid(form)

@method_decorator(login_required, name='dispatch')
class Proyectos(TemplateView):

    model = Proyecto
    template_name = 'definicion/proyectos.html'
    context_object_name = 'proyectos'
"""
class AgregarMiembros(generic.CreateView):

    form_class = AgregarMiembro
    template_name = 'definicion/miembros.html'
    context_object_name = 'miembros'
"""