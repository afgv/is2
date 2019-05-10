
from django.contrib.auth.models import AbstractUser
from base64 import b64encode
from django.db import models
from administracion.models import CustomUser
from django.contrib.auth.models import User, Group
from django.core.exceptions import ValidationError
from django.db.models import Q, Sum
from django.db.models.signals import m2m_changed, post_save
from django.shortcuts import get_object_or_404
from django.utils.encoding import force_bytes
from django.utils import timezone
from guardian.shortcuts import assign_perm, remove_perm, get_perms_for_model, get_perms
from django.urls import reverse_lazy
import reversion
from reversion.models import Revision


class Proyecto(models.Model):
    """
    Modelo de Proyecto del sistema.

    """
    nombre=models.CharField(max_length=20, default='', null=False)
    inicio=models.DateField()
    fin=models.DateField()
    descripcion_breve=models.CharField(max_length=100)
    descripcion_detallada=models.TextField(max_length=500)
    creacion = models.DateTimeField(default=timezone.now)
    duracion_sprint = models.PositiveIntegerField(default=30)
    equipo = models.ManyToManyField(CustomUser, through='MiembroEquipo')

    estado_choices = (
        ('EP', 'En Produccion'), ('CO', 'Completado'), ('AP', 'Aprobado'), ('CA', 'Cancelado'), ('IN', 'Inactivo'))
    estado = models.CharField(choices=estado_choices, max_length=2, default='IN')

    class Meta:
        # Los permisos estaran asociados a los proyectos, por lo que todos los permisos de ABM de las entidades
        #dependientes del proyecto, deben crearse como permisos de proyecto
        #en vez de 'add', 'change' y 'delete', los permisos personalizados seran 'create', 'edit' y 'remove' para
        #evitar confusiones con los por defecto.

        permissions = (
            ('list_all_projects', 'listar los proyectos disponibles'),
            ('view_project', 'ver el proyecto'),
            ('aprobar_proyecto', 'aprobar el proyecto'),

            ('create_sprint', 'agregar sprint'),
            ('edit_sprint', 'editar sprint'),
            ('remove_sprint', 'eliminar sprint'),

            ('create_flujo', 'agregar flujo'),
            ('edit_flujo', 'editar flujo'),
            ('remove_flujo', 'eliminar flujo'),

            ('create_userstory', 'agregar userstory'),
            ('edit_userstory', 'editar userstory'),
            ('remove_userstory', 'eliminar userstory'),
            ('prioritize_userstory', 'asignar prioridad a userstories'),
            ('registraractividad_userstory', 'registrar avances en userstories'),
            ('aprobar_userstory', 'aprobar userstories completados'),
            ('cancelar_userstory', 'cancela userstories completados'),

        )

    def get_nombre(self):
        return self.nombre

    def __str__(self):
        return self.get_nombre()

    """
    def get_absolute_url(self):
        return reverse_lazy('project:project_detail', args=[self.pk])"""

    def get_horas_estimadas(self):
        return self.userstory_set.aggregate(total=Sum('tiempo_estimado'))['total']

    def get_horas_trabajadas(self):
        return self.userstory_set.aggregate(total=Sum('tiempo_registrado'))['total']

    def _get_progreso(self):
        us_total = self.userstory_set.count() - self.userstory_set.filter(estado=4).count()
        us_aprobados = self.userstory_set.filter(estado=3).count()
        progreso = float(us_aprobados) / us_total * 100 if us_total > 0 else 0
        return int(progreso)
    progreso = property(_get_progreso)

    def clean(self):
        try:
            if self.inicio > self.fin:
                raise ValidationError({'inicio': 'Fecha de inicio no puede ser mayor '
                                                 'que la fecha de terminacion.'})
        except TypeError:
            pass  # si una de las fechas es null, clean_field() se encarga de lanzar error

class MiembroEquipo(models.Model):
    """
    Miembros del equipo de un proyecto con un rol específico
    """
    proyecto=models.ForeignKey(Proyecto, null=True, on_delete=models.SET_NULL)
    usuario=models.ForeignKey(CustomUser, null=True, on_delete=models.SET_NULL)
    roles = models.ManyToManyField(Group)

    def __str__(self):
        return self.usuario.username

    def save(self, force_insert=False, force_update=False, using=None,
             update_fields=None):
        super(MiembroEquipo, self).save(force_insert, force_update, using, update_fields)
        # Agregamos el permiso view_proyect al usuario
        assign_perm('view_project', self.usuario, self.proyecto)


    # nota: si se quiere hacer un bulk delete a través de un queryset no hacerlo directamente
    #llamar al delete de cada objeto para remover los permisos
    def delete(self, using=None):
        for role in self.roles.all():
            for perm in role.permissions.all():
                remove_perm(perm.codename, self.usuario, self.proyecto)
        super(MiembroEquipo, self).delete(using)

    class Meta:
        default_permissions = ()
        verbose_name_plural = 'miembros equipo'
        unique_together = ('usuario', 'proyecto')


class Sprint(models.Model):
    """
    Manejo de los sprints del proyecto
    """
    nombre = models.CharField(max_length=20)
    inicio = models.DateTimeField()
    fin = models.DateTimeField()
    proyecto = models.ForeignKey(Proyecto, on_delete=models.SET_NULL, null=True, blank=True)
    #estado = models.BooleanField(default=False)

    class Meta:
        default_permissions = ()
        verbose_name = 'sprint'
        verbose_name_plural = 'sprints'

    def __unicode__(self):
        return self.nombre

    """
    def get_absolute_url(self):
        return reverse_lazy('project:sprint_detail', args=[self.pk])"""




class Flujo(models.Model):
    """
    Administración de los flujos que forman parte de un proyecto.
    Las plantillas de flujo se manejan como Flujos sin proyecto asignado.
    """
    nombre = models.CharField(max_length=20)
    proyecto = models.ForeignKey(Proyecto, on_delete=models.SET_NULL, null=True, blank=True)

    def __unicode__(self):
        return self.nombre

    class Meta:
        verbose_name_plural = 'flujos'
        default_permissions = ()
        permissions = (
            ('add_flow_template', 'agregar plantilla de flujo'),
            ('change_flow_template', 'editar plantilla de flujo'),
            ('delete_flow_template', 'eliminar plantilla de flujo'),
        )

    """
    def get_absolute_url(self):
        return reverse_lazy('project:flujo_detail', args=[self.pk])"""


class Fase(models.Model):
    """
    Las fases representan las distintas etapas de las que se componen un flujo
    """
    name = models.CharField(max_length=20)
    flujo = models.ForeignKey(Flujo, on_delete=models.CASCADE)

    def __unicode__(self):
        return self.name

    class Meta:
        order_with_respect_to = 'flujo'
        verbose_name_plural = 'actividades'


class UserStory(models.Model):
    """
    Manejo de los User Stories. Los User Stories representan a cada
    funcionalidad desde la perspectiva del cliente que debe realizar el sistema.
    """
    proyecto = models.ForeignKey(Proyecto, on_delete=models.SET_NULL, blank=True, null=Fase)
    estado_fase_choices = ((0, 'ToDo'), (1, 'Doing'), (2, 'Done'), )
    estado_choices = ((0, 'Inactivo'), (1, 'En curso'), (2, 'Pendiente Aprobacion'), (3, 'Aprobado'), (4,'Cancelado'),)
    priority_choices = ((0, 'Baja'), (1, 'Media'), (2, 'Alta'))
    nombre = models.CharField(max_length=60)
    descripcion = models.TextField()
    prioridad = models.IntegerField(choices=priority_choices, default=0)
    valor_negocio = models.IntegerField()
    valor_tecnico = models.IntegerField()
    tiempo_estimado = models.PositiveIntegerField()
    tiempo_registrado = models.PositiveIntegerField(default=0)
    ultimo_cambio = models.DateTimeField(default=timezone.now)
    estado = models.IntegerField(choices=estado_choices, default=0)
    estado_fase = models.IntegerField(choices=estado_fase_choices, default=0)
    desarrollador = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True, blank=True)
    sprint = models.ForeignKey(Sprint, null=True, on_delete=models.SET_NULL, blank=True)
    fase = models.ForeignKey(Fase, null=True, on_delete=models.SET_NULL, blank=True)

    def __unicode__(self):
        return self.nombre

    def _get_progreso(self):
        progreso = float(self.tiempo_registrado) / self.tiempo_estimado * 100
        return int(progreso if progreso <= 100 else 100)
    progreso = property(_get_progreso)
    """
    def get_absolute_url(self):
        return reverse_lazy('project:userstory_detail', args=[self.pk])
    """
    def save(self, force_insert=False, force_update=False, using=None, update_fields=None):
        old_developer = None

        if self.pk is not None:
            old_instance = get_object_or_404(UserStory, pk=self.pk)
            old_developer = old_instance.desarrollador
        super(UserStory, self).save(force_insert, force_update, using, update_fields)
        #borramos los permisos del antiguo desarrollador
        if old_developer:
            for perm in get_perms(old_developer, self):
                remove_perm(perm, old_developer, self)
        #copiamos al user story recién creado los permisos de user story
        if self.proyecto and self.desarrollador:
            membership = get_object_or_404(MiembroEquipo, usuario=self.desarrollador, proyecto=self.proyecto)
            permisos_us = get_perms_for_model(UserStory)
            for rol in membership.roles.all():
                for perm in rol.permissions.all():
                    if perm in permisos_us:
                        assign_perm(perm.codename, self.desarrollador, self)

    class Meta:
        verbose_name_plural = 'user stories'
        default_permissions = ()
        permissions = (
            ('edit_my_userstory', 'editar mis userstories'),
            ('registraractividad_my_userstory', 'registrar avances en mis userstories')
        )


reversion.register(UserStory,
                   fields=['nombre', 'descripcion', 'prioridad', 'valor_negocio', 'valor_tecnico', 'tiempo_estimado'])
#importamos recién acá la señal para que no haya la dependencia circular entre la señal y UserStory
from definicion.signals import add_permissions_team_member
m2m_changed.connect(add_permissions_team_member, sender=MiembroEquipo.roles,
                    dispatch_uid='add_permissions_signal')

class Nota(models.Model):
    """
    Manejo de notas adjuntas relacionadas a un User Story, estás entradas representan
    constancias de los cambios, como cantidad de horas trabajadas, en un user story.
    """
    estado_choices = ((0, 'Inactivo'), (1, 'En curso'), (2, 'Pendiente Aprobacion'), (3, 'Aprobado'), (4,'Cancelado'),)
    mensaje = models.TextField(help_text='Mensaje de descripcion de los avances o motivo de cancelacion', null=True, blank=True)
    fecha = models.DateTimeField(default=timezone.now)
    tiempo_registrado = models.IntegerField(default=0)
    horas_a_registrar = models.IntegerField(default=0)
    desarrollador = models.ForeignKey(CustomUser, on_delete=models.SET_NULL, null=True)
    sprint = models.ForeignKey(Sprint, on_delete=models.SET_NULL, null=True)
    fase = models.ForeignKey(Fase, null=True, on_delete=models.SET_NULL)
    estado = models.IntegerField(choices=estado_choices, default=0)
    estado_fase = models.IntegerField(choices=UserStory.estado_fase_choices, null=True)
    user_story = models.ForeignKey(UserStory, on_delete=models.SET_NULL, null=True)

    def __unicode__(self):
        return '{}({}): {}'.format(self.desarrollador, self.fecha, self.horas_a_registrar)


class Adjunto(models.Model):
    """
    Modelo para la administración de archivos adjuntos a un User Story.
    """
    tipo_choices = [('img', 'Imagen'), ('text', 'Texto'), ('misc', 'Otro'), ('src', 'Codigo')]
    lang_choices = [('clike', 'C'), ('python', 'Python'), ('ruby', 'Ruby'), ('css', 'CSS'), ('php', 'PHP'),
                    ('scala', 'Scala'), ('sql', 'SQL'), ('bash', 'Bash'), ('javascript', 'JavaScript'),
                    ('markup', 'Markup')]
    nombre = models.CharField(max_length=20)
    descripcion = models.TextField()
    filename = models.CharField(max_length=100, null=True, editable=False)
    binario = models.BinaryField(null=True, blank=True)
    content_type = models.CharField(null=True, editable=False, max_length=50)
    creacion = models.DateTimeField(default=timezone.now)
    user_story = models.ForeignKey(UserStory, on_delete=models.SET_NULL, null=True)
    tipo = models.CharField(choices=tipo_choices, default='misc', max_length=10)
    lenguaje = models.CharField(choices=lang_choices, null=True, max_length=10)

    def __unicode__(self):
        return self.nombre

    def img64(self):
        return b64encode(force_bytes(self.binario))

    """
    def get_absolute_url(self):
        return reverse_lazy('project:file_detail', args=[self.pk])

    def get_download_url(self):
        return reverse_lazy('project:download_attachment', args=[self.pk])
    """