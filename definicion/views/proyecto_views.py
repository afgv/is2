# -*- coding: utf-8 -*-
from django.contrib.auth.models import User
from django.contrib.sites.shortcuts import get_current_site
from django.forms import CheckboxSelectMultiple, SelectDateWidget
from django.forms import inlineformset_factory
from django.forms.models import modelform_factory
from django.http import HttpResponseRedirect, Http404
from django.shortcuts import render, get_object_or_404
from django.template import RequestContext
from django.template.loader import render_to_string
from django.urls import reverse_lazy
from django.views import generic
from django.views.generic import DetailView
from django.views.generic import detail
from django.views.generic import ListView
from django.views.generic.detail import SingleObjectTemplateResponseMixin
from guardian.mixins import LoginRequiredMixin
from guardian.shortcuts import remove_perm
from guardian.shortcuts import get_perms
from definicion.forms import MiembrosEquipoFormset
from definicion.models import Proyecto
from definicion.models import MiembroEquipo
from definicion.views import GlobalPermissionRequiredMixin, ActiveProjectRequiredMixin
from definicion.views import CreateViewPermissionRequiredMixin


class ProjectList(LoginRequiredMixin, ListView):
    """
    Listado de Proyectos
    """
    model = Proyecto
    context_object_name = 'projects'
    template_name = 'project/proyecto/project_list.html'
    show_cancelled = False

    def get_queryset(self):
        """
        Obtener proyectos del Sistema.

        :return: lista de proyectos
        """
        if self.request.user.has_perm('project.list_all_projects'):
            proyectos = Proyecto.objects
        else:
            proyectos = self.request.user.proyecto_set
        return proyectos.filter(estado='CA') if self.show_cancelled else proyectos.exclude(estado='CA')

class ProjectDetail(LoginRequiredMixin, GlobalPermissionRequiredMixin, DetailView):
    """
    Vista de Detalles de Proyecto
    """
    model = Proyecto
    context_object_name = 'proyecto'
    permission_required = 'project.view_project'
    template_name = 'project/proyecto/project_detail.html'

    def get_context_data(self, **kwargs):
        context = super(ProjectDetail, self).get_context_data(**kwargs)
        context['team'] = self.object.miembroequipo_set.all()
        context['flows'] = self.object.flujo_set.all()
        context['sprints'] = self.object.sprint_set.all()
        context['approved_us'] = self.object.userstory_set.filter(estado=3).count()
        context['active_us'] = self.object.userstory_set.filter(estado=1).count()
        context['pending_us'] = self.object.userstory_set.filter(estado=2).count()
        context['failed_us'] = self.object.userstory_set.filter(estado=4).count()
        return context


class ProjectCreate(LoginRequiredMixin, CreateViewPermissionRequiredMixin, generic.CreateView):
    """
    Permite la creacion de Proyectos
    """
    model = Proyecto
    permission_required = 'project.add_proyecto'
    form_class = modelform_factory(Proyecto,
                                   widgets={'inicio': SelectDateWidget, 'fin': SelectDateWidget},
                                   fields=('nombre', 'inicio', 'fin', 'duracion_sprint',
                                           'descripcion_breve', 'descripcion_detallada'),)
    template_name = 'project/proyecto/project_create.html'
    TeamMemberInlineFormSet = inlineformset_factory(Proyecto, MiembroEquipo, formset=MiembrosEquipoFormset, can_delete=True,
                                                    fields=['usuario', 'roles'],
                                                    extra=3,
                                                    widgets={'roles': CheckboxSelectMultiple})

    def get_context_data(self, **kwargs):
        context = super(ProjectCreate, self).get_context_data(**kwargs)
        context['action'] = 'Crear'
        context['formset'] = self.TeamMemberInlineFormSet(self.request.POST if self.request.method == 'POST' else None)
        return context

    def form_valid(self, form):
        """
        Guarda los miembros de equipo especificados asociados al proyecto.

        :param form: formulario del proyecto
        """

        self.object = form.save()
        formset = self.TeamMemberInlineFormSet(self.request.POST, instance=self.object)
        if formset.is_valid():
            formset.save()
            return HttpResponseRedirect(self.get_success_url())

        return render(self.request, self.get_template_names(), {'form': form, 'formset': formset},
                      context_instance=RequestContext(self.request))


class ProjectUpdate(ActiveProjectRequiredMixin, LoginRequiredMixin, GlobalPermissionRequiredMixin, generic.UpdateView):
    """
    Permite la Edicion de Proyectos
    """
    model = Proyecto
    permission_required = 'project.change_proyecto'
    template_name = 'project/proyecto/project_form.html'
    TeamMemberInlineFormSet = inlineformset_factory(Proyecto, MiembroEquipo, formset=MiembrosEquipoFormset, can_delete=True,
                                                    fields=['usuario', 'roles'],
                                                    extra=1,
                                                    widgets={'roles': CheckboxSelectMultiple})
    form_class = modelform_factory(Proyecto,
                                   widgets={'inicio': SelectDateWidget, 'fin': SelectDateWidget},
                                   fields=('nombre', 'inicio', 'fin', 'duracion_sprint',
                                           'descripcion_breve','descripcion_detallada'),
                                   )

    def get_proyecto(self):
        return self.get_object()

    def form_valid(self, form):
        '''
        actualiza los miembros del equipo del proyecto que se hayan especifico

        :param form: formulario de edición del proyecto
        '''
        self.object = form.save()
        formset = self.TeamMemberInlineFormSet(self.request.POST, instance=self.object)
        if formset.is_valid():
            # borramos todos los permisos asociados al usuario en el proyecto antes de volver a asignar los nuevos
            project = self.object
            for form in formset:
                if form.has_changed():  #solo los formularios con cambios efectuados
                    user = form.cleaned_data['usuario']
                    if('usuario' in form.changed_data and 'usuario' in form.initial): #si se cambia el usuario, borrar permisos del usuario anterior
                        original_user = get_object_or_404(User, pk=form.initial['usuario'])
                        for perm in get_perms(original_user, project):
                            remove_perm(perm, original_user, project)
                    else:
                        for perm in get_perms(user, project):
                            remove_perm(perm, user, project)

            formset.save()
            return HttpResponseRedirect(self.get_success_url())

        return render(self.request, self.get_template_names(), {'form': form, 'formset': formset},
                      context_instance=RequestContext(self.request))

    def get_context_data(self, **kwargs):
        '''
        Especifica los datos de contexto a pasar al template
        :param kwargs: Diccionario con parametros con nombres clave
        '''
        context = super(ProjectUpdate, self).get_context_data(**kwargs)
        context['action'] = 'Editar'
        context['formset'] = self.TeamMemberInlineFormSet(self.request.POST if self.request.method == 'POST' else None, instance=self.object)
        return context


class ProjectDelete(ActiveProjectRequiredMixin, LoginRequiredMixin, GlobalPermissionRequiredMixin, generic.DeleteView):
    """
    Vista para la cancelacion de proyectos
    """
    model = Proyecto
    template_name = 'project/proyecto/proyect_delete.html'
    success_url = reverse_lazy('project:project_list')
    permission_required = 'project.delete_proyecto'

    def get_proyecto(self):
        return self.get_object()

    def delete(self, request, *args, **kwargs):
        """
        Llama al metodo delete() del objeto
        y luego redirige a la url exitosa.
        """
        self.object = self.get_object()
        success_url = self.get_success_url()
        if False:
            self.object.delete()
        else:
            self.object.estado = 'CA'
            self.object.save(update_fields=['estado'])
        return HttpResponseRedirect(success_url)

class ApproveProject(ActiveProjectRequiredMixin, LoginRequiredMixin, GlobalPermissionRequiredMixin, SingleObjectTemplateResponseMixin, detail.BaseDetailView):
    """
    Vista de Aprobación o rechazo de User Stories
    """
    model = Proyecto
    template_name = 'project/proyecto/project_approve.html'
    permission_required = 'project.aprobar_proyecto'
    context_object_name = 'proyecto'

    def get_proyecto(self):
        return self.get_object()

    def dispatch(self, request, *args, **kwargs):
        instance = self.get_object()
        if instance.estado == 'CO':
            return super(ApproveProject, self).dispatch(request, *args, **kwargs)
        raise Http404

    def get_success_url(self):
        return reverse_lazy('project:project_detail', kwargs={'pk': self.get_object().id})

    def post(self, request, *args, **kwargs):
        p = self.get_object()
        if self.request.POST.get('rechazar', '') == 'rechazar':
            #TODO Exactamente qué hacer
            pass
            #p.estado = 'EP' #Vuelve al estado en desarrollo
        elif self.request.POST.get('aprobar', '') == 'aprobar':
            p.estado = 'AP' #Aprobado
        p.save()
        '''self.notify(p)'''
        return HttpResponseRedirect(self.get_success_url())
    '''
    def notify(self, proyecto):
        subject = 'Se ha aprobado el Proyecto: {}'.format(proyecto)
        domain = get_current_site(self.request).domain
        message = render_to_string('mail/approved_email.html',
                                   {'proyecto': proyecto, 'us': user_story, 'domain': domain, 'u': self.request.user})
        recipients = [u.email for u in proyecto.equipo.all() if u.has_perm('project.aprobar_userstory', proyecto)]
        if user_story.desarrollador and user_story.desarrollador.email not in recipients:
            recipients.append(user_story.desarrollador.email)
        send_mail(subject, message, 'projectium15@gamil.com', recipients, html_message=message)
    '''