# Generated by Django 2.2 on 2019-05-06 03:43

from django.conf import settings
from django.db import migrations


class Migration(migrations.Migration):

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
        ('definicion', '0003_agregarproyecto_proyectos'),
    ]

    operations = [
        migrations.RenameModel(
            old_name='Proyectos',
            new_name='CustomProyecto',
        ),
        migrations.RemoveField(
            model_name='crearproyecto',
            name='proyecto_ptr',
        ),
        migrations.DeleteModel(
            name='AgregarProyecto',
        ),
        migrations.DeleteModel(
            name='CrearProyecto',
        ),
    ]
