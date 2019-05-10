from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.views import generic
#from django.urls import reverse
from django.http import HttpResponseRedirect, HttpResponse, HttpResponseForbidden
from django.shortcuts import get_object_or_404
from guardian.decorators import permission_required_or_403
from guardian.mixins import LoginRequiredMixin
from guardian.shortcuts import get_perms
from os.path import splitext
from definicion.forms import FileUploadForm
from definicion.models import UserStory, Adjunto, Proyecto
from definicion.views import CreateViewPermissionRequiredMixin, GlobalPermissionRequiredMixin


lang = {'.c': 'clike', '.py': 'python', '.rb': 'ruby', '.css': 'css', '.php': 'php', '.scala': 'scala', '.sql': 'sql',
        '.sh': 'bash', '.js': 'javascript', '.html': 'markup'}


# TODO subir archivo dentro de una nota?
class UploadFileView(LoginRequiredMixin, generic.FormView):
    """
    Visa que permite subir un archivo adjunto
    """
    template_name = 'project/adjunto/upload.html'
    form_class = FileUploadForm
    user_story = None

    def dispatch(self, request, *args, **kwargs):
        """
        Comprobacion de permisos hecha antes de la llamada al dispatch que inicia el proceso de respuesta al request de la url
        :param request: request hecho por el cliente
        :param args: argumentos adicionales posicionales
        :param kwargs: argumentos adicionales en forma de diccionario
        :return: PermissionDenied si el usuario no cuenta con permisos
        """
        self.user_story = get_object_or_404(UserStory, pk=self.kwargs['pk'])
        if 'edit_userstory' in get_perms(request.user, self.user_story.proyecto):
            return super(UploadFileView, self).dispatch(request, *args, **kwargs)
        elif 'edit_my_userstory' in get_perms(self.request.user, self.user_story):
            return super(UploadFileView, self).dispatch(request, *args, **kwargs)
        else:
            raise PermissionDenied()

    def upload_handler(self, attachment, uploaded_file):
        attachment.user_story = self.user_story
        attachment.filename = uploaded_file.name

        if uploaded_file.content_type.startswith('image'):
            attachment.tipo = 'img'
        else:
            _, ext = splitext(uploaded_file.name)
            if ext in lang:
                attachment.lenguaje = lang[ext]
                attachment.tipo = 'src'
            elif uploaded_file.content_type == 'text/plain':
                attachment.tipo = 'text'

        attachment.content_type = uploaded_file.content_type
        attachment.binario = uploaded_file.read()
        attachment.save()

    def form_valid(self, form):
        attachment = form.save(commit=False)
        self.upload_handler(attachment, self.request.FILES['file'])
        return HttpResponseRedirect(attachment.get_absolute_url())


class FileDetail(LoginRequiredMixin, GlobalPermissionRequiredMixin, generic.DetailView):
    model = Adjunto
    template_name = 'project/adjunto/file_view.html'
    context_object_name = 'adjunto'
    permission_required = 'project.view_project'

    def get_permission_object(self):
        """
        Retorna el objeto al cual corresponde el permiso
        """
        return self.get_object().user_story.proyecto


class FileList(LoginRequiredMixin, GlobalPermissionRequiredMixin, generic.ListView):
    """
    Vista que lista los adjuntos del user story
    """
    model = Adjunto
    template_name = 'project/adjunto/file_list.html'
    context_object_name = 'adjuntos'
    permission_required = 'project.view_project'
    user_story = None

    def get_permission_object(self):
        """
        Retorna el objeto al cual corresponde el permiso
        """
        self.user_story = get_object_or_404(UserStory, pk=self.kwargs['pk'])
        return self.user_story.proyecto

    def get_queryset(self):
        return self.user_story.adjunto_set.all()

    def get_context_data(self, **kwargs):
        context = super(FileList, self).get_context_data(**kwargs)
        context['user_story'] = self.user_story
        return context


@login_required
def download_attachment(request, pk):
    """
    Vista que permite la descarga de un archivo adjunto de la base de datos
    :param request: request del cliente
    :param pk: id del adjunto
    :return: respuesta http con el archivo adjunto
    """
    attachment = get_object_or_404(Adjunto, pk=pk)
    if request.user.has_perm('project.view_project', attachment.user_story.proyecto):
        response = HttpResponse(attachment.binario, content_type=attachment.content_type)
        if attachment.tipo == 'img':
            response['Content-Disposition'] = 'filename=%s' % attachment.filename
        else:
            response['Content-Disposition'] = 'attachment; filename=%s' % attachment.filename
        return response
    raise PermissionDenied()