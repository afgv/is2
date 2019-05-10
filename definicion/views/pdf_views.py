# -*- coding: utf-8 -*-
import os

import weasyprint as weasyprint
from django import http
from django.contrib.auth.decorators import login_required
from django.core.exceptions import PermissionDenied
from django.utils._os import safe_join
from guardian.decorators import permission_required
from django.contrib.auth.models import User
from django.db.models import Sum
from django.http import HttpResponse
from django.shortcuts import render_to_response, get_object_or_404, render
from django.template.loader import get_template
from django.template import Context, RequestContext
from guardian.shortcuts import get_perms
from definicion.models import Proyecto, Sprint
from definicion.views import get_sprint_burndown
from sgp import settings
import weasyprint



def url_fetcher(url):
    if url.startswith('assets://'):
        url = url[len('assets://'):]
        url = "file://" + safe_join(settings.ASSETS_ROOT, url)
    return weasyprint.default_url_fetcher(url)

import requests
import json

export_url = 'http://127.0.0.1:3003'

def pdf(request):
    project = get_object_or_404(Proyecto, pk=7)
    graficos = get_graficos(project)

    return render(request, 'project/report.html', {'graph': graficos})

def get_graficos(project):
    sprints = project.sprint_set.all()
    graficos = []
    xAxis = "xAxis: {labels: {format: 'Dia {value}'}}"
    yAxis = "yAxis: { title: {text: 'Esfuerzo Restante'}, min: 0, labels: {format: '{value} hs'}}"

    for sprint in sprints:
        burndown = get_sprint_burndown(sprint)
        title = "credits: false, title: {text:'Burndown Chart'}, subtitle: {text: '%s'}" % sprint.nombre
        series = "series:[{name: 'Ideal', data: %s}, {name: 'Real', data: %s}]" % (burndown['ideal'], burndown['real'], )
        infile = "{ %s }" % ",".join([title, xAxis, yAxis, series])
        d = {'infile': infile}
        pdata = json.dumps(d)
        #print pdata
        r = requests.post(export_url, data=pdata, headers={'Content-Type': 'application/json'}, timeout=5)
        graficos.append(r.content)

    return graficos

@login_required
@permission_required('project.view_project', (Proyecto, 'id', 'proyecto_id'))
def reporte_backlog_producto(request, proyecto_id):
    project = get_object_or_404(Proyecto, id=proyecto_id)
    us_set_cancelados = project.userstory_set.filter(estado=4).order_by('sprint__inicio', '-prioridad')
    cancelados_sum = us_set_cancelados.aggregate(sum=Sum('tiempo_estimado'))['sum']
    cancelados_real_sum = us_set_cancelados.aggregate(sum=Sum('tiempo_registrado'))['sum']
    us_set_inactivos = project.userstory_set.filter(estado=0).order_by('sprint__inicio', '-prioridad', 'tiempo_estimado')
    inactivos_sum = us_set_inactivos.aggregate(sum=Sum('tiempo_estimado'))['sum']
    inactivos_real_sum = us_set_inactivos.aggregate(sum=Sum('tiempo_registrado'))['sum']
    us_set_curso = project.userstory_set.filter(estado=1).order_by('sprint__inicio', '-prioridad')
    encurso_sum = us_set_curso.aggregate(sum=Sum('tiempo_estimado'))['sum']
    encurso__real_sum = us_set_curso.aggregate(sum=Sum('tiempo_registrado'))['sum']
    us_set_pendientes = project.userstory_set.filter(estado=2).order_by('sprint__inicio', '-prioridad', 'tiempo_estimado')
    pendientes_sum = us_set_pendientes.aggregate(sum=Sum('tiempo_estimado'))['sum']
    pendientes_real_sum = us_set_pendientes.aggregate(sum=Sum('tiempo_registrado'))['sum']
    us_set_aprobados = project.userstory_set.filter(estado=3).order_by('sprint__inicio', '-prioridad')
    aprobados_sum = us_set_aprobados.aggregate(sum=Sum('tiempo_estimado'))['sum']
    aprobados_real_sum = us_set_aprobados.aggregate(sum=Sum('tiempo_registrado'))['sum']
    proyecto_sum = (cancelados_sum if cancelados_sum else 0) + (inactivos_sum if inactivos_sum else 0) + (encurso_sum if encurso_sum else 0) + (pendientes_sum if pendientes_sum else 0) + (aprobados_sum if aprobados_sum else 0)
    proyecto_sum_real = (cancelados_real_sum if cancelados_real_sum else 0) + (inactivos_real_sum if inactivos_real_sum else 0)+ (encurso__real_sum if encurso__real_sum else 0) + (pendientes_real_sum if pendientes_real_sum else 0) + (aprobados_real_sum if aprobados_real_sum else 0)
    contexto = {'proyecto': project, 'cancelados': us_set_cancelados,
                'inactivos': us_set_inactivos, 'en_curso': us_set_curso, 'pendientes': us_set_pendientes,
                'aprobados': us_set_aprobados, 'sum_inactivos': inactivos_sum, 'sum_inactivos_real': inactivos_real_sum,
                'sum_en_curso': encurso_sum, 'sum_en_curso_real': encurso__real_sum, 'sum_cancelados': cancelados_sum,
                'sum_cancelados_real': cancelados_real_sum, 'sum_aprobados': aprobados_sum, 'sum_aprobados_real': aprobados_real_sum,
                'sum_pendientes': pendientes_sum, 'sum_pendientes_real': pendientes_real_sum, 'sum_proyecto': proyecto_sum,
                'sum_proyecto_real': proyecto_sum_real}
    template = get_template('reportes/backlog_producto.html')
    html = template.render(RequestContext(request, contexto))
    response = HttpResponse(content_type="application/pdf")
    weasyprint.HTML(string=html, base_url=request.build_absolute_uri(), url_fetcher=url_fetcher).write_pdf(response)
    return response

@login_required
@permission_required('project.view_project', (Proyecto, 'id', 'proyecto_id'))
def reporte_equipo_proyecto(request, proyecto_id):
    project = get_object_or_404(Proyecto, id=proyecto_id)
    equipo = project.miembroequipo_set.all()

    us_sets = []
    for miembro in [e.usuario for e in equipo]:
        us_set = miembro.userstory_set.filter(proyecto=project, estado__in=[0,1]).order_by('sprint__inicio', '-prioridad')
        if us_set:
            us_sets.append(us_set)

    contexto = {'proyecto': project, 'equipo': equipo, 'sets': us_sets}
    template = get_template('reportes/equipo_proyecto.html')
    html = template.render(RequestContext(request, contexto))
    response = HttpResponse(content_type="application/pdf")
    weasyprint.HTML(string=html, base_url=request.build_absolute_uri(), url_fetcher=url_fetcher).write_pdf(response)
    return response

@login_required
@permission_required('project.view_project', (Proyecto, 'id', 'proyecto_id'))
def html_reporte_backlog_producto(request, proyecto_id):
    project = get_object_or_404(Proyecto, id=proyecto_id)
    us_set_cancelados = project.userstory_set.filter(estado=4).order_by('sprint__inicio', '-prioridad')
    us_set_inactivos = project.userstory_set.filter(estado=0).order_by('sprint__inicio', '-prioridad')
    us_set_curso = project.userstory_set.filter(estado=1).order_by('sprint__inicio', '-prioridad')
    us_set_pendientes = project.userstory_set.filter(estado=2).order_by('sprint__inicio', '-prioridad')
    us_set_aprobados = project.userstory_set.filter(estado=3).order_by('sprint__inicio', '-prioridad')
    contexto = {'proyecto': project, 'cancelados': us_set_cancelados,
                'inactivos': us_set_inactivos, 'en_curso': us_set_curso, 'pendientes': us_set_pendientes,
                'aprobados': us_set_aprobados}
    template = get_template('reportes/backlog_producto.html')
    html = template.render(RequestContext(request, contexto))
    response = HttpResponse(content_type="application/pdf")
    weasyprint.HTML(string=html, url_fetcher=url_fetcher).write_pdf(response)
    return render_to_response('reportes/backlog_producto.html', contexto)

@login_required
@permission_required('project.view_project', (Proyecto, 'id', 'proyecto_id'))
def reporte_burndown(request, proyecto_id):
    project = get_object_or_404(Proyecto, id=proyecto_id)
    try:
        graficos = get_graficos(project)
    except requests.ConnectionError:
        return render(request, 'reportes/export_error.html', {})
    contexto = {'proyecto': project, 'graph':graficos}
    template = get_template('reportes/burndown.html')
    html = template.render(RequestContext(request, contexto))
    response = HttpResponse(content_type="application/pdf")
    weasyprint.HTML(string=html, base_url=request.build_absolute_uri(), url_fetcher=url_fetcher).write_pdf(response)
    return response

@login_required
def reporte_backlog_sprint(request, sprint_id):

    sprint = get_object_or_404(Sprint, id=sprint_id)
    #Comprobamos el permiso manualmente
    if 'view_project' in get_perms(request.user, sprint.proyecto):
        us_set = sprint.userstory_set.all()
        contexto = {'sprint': sprint, 'user_stories': us_set}
        template = get_template('reportes/backlog_sprint.html')
        html = template.render(RequestContext(request, contexto))
        response = HttpResponse(content_type="application/pdf")
        weasyprint.HTML(string=html, base_url=request.build_absolute_uri(), url_fetcher=url_fetcher).write_pdf(response)
        return response
    else:
        raise PermissionDenied()

@login_required
def reporte_userstories_user(request, user_id):
    usuario = get_object_or_404(User, id=user_id)
    us_pendientes = usuario.userstory_set.filter(estado=0)
    us_encurso = usuario.userstory_set.filter(estado=1)
    us_finalizados = usuario.userstory_set.filter(estado=3)
    contexto = {'usuario': usuario, 'pendientes': us_pendientes,
                'en_curso': us_encurso, 'finalizados':us_finalizados}
    template = get_template('reportes/userstories_user.html')
    html = template.render(RequestContext(request, contexto))
    response = HttpResponse(content_type="application/pdf")
    weasyprint.HTML(string=html, base_url=request.build_absolute_uri(), url_fetcher=url_fetcher).write_pdf(response)
    return response

@login_required
@permission_required('project.view_project', (Proyecto, 'id', 'proyecto_id'))
def reporte_lista_priorizada(request, proyecto_id):
    proyecto = get_object_or_404(Proyecto, id=proyecto_id)
    us_bajo = proyecto.userstory_set.filter(prioridad=0).order_by('sprint__inicio')
    us_medio = proyecto.userstory_set.filter(prioridad=1).order_by('sprint__inicio')
    us_alto = proyecto.userstory_set.filter(prioridad=2).order_by('sprint__inicio')
    contexto = {'proyecto': proyecto, 'bajos': us_bajo,
                'medios': us_medio, 'altos':us_alto}
    template = get_template('reportes/userstories_priorizados.html')
    html = template.render(RequestContext(request, contexto))
    response = HttpResponse(content_type="application/pdf")
    weasyprint.HTML(string=html, base_url=request.build_absolute_uri(), url_fetcher=url_fetcher).write_pdf(response)
    return response

