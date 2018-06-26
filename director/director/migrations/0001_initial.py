# Generated by Django 2.0.5 on 2018-06-20 03:23

import director.models
from django.conf import settings
from django.db import migrations, models
import django.db.models.deletion
import django.utils.timezone
import uuid


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        migrations.swappable_dependency(settings.AUTH_USER_MODEL),
    ]

    operations = [
        migrations.CreateModel(
            name='Checkout',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('key', models.TextField(default=director.models.new_checkout_key, unique=True)),
                ('dirty', models.BooleanField(default=False)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='Cluster',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('host', models.TextField(unique=True)),
            ],
        ),
        migrations.CreateModel(
            name='Message',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('time', models.DateTimeField(default=django.utils.timezone.now)),
                ('level', models.IntegerField(default=2)),
                ('message', models.TextField()),
                ('checkout', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='director.Checkout')),
            ],
        ),
        migrations.CreateModel(
            name='Project',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('address', models.TextField(unique=True)),
                ('gallery', models.BooleanField(default=False)),
                ('users', models.ManyToManyField(related_name='projects', to=settings.AUTH_USER_MODEL)),
            ],
        ),
        migrations.CreateModel(
            name='StencilaProject',
            fields=[
                ('id', models.AutoField(auto_created=True, primary_key=True, serialize=False, verbose_name='ID')),
                ('name', models.SlugField(max_length=255)),
                ('uuid', models.UUIDField(default=uuid.uuid4, editable=False, unique=True)),
                ('owner', models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to=settings.AUTH_USER_MODEL)),
                ('project', models.OneToOneField(on_delete=django.db.models.deletion.CASCADE, to='director.Project')),
            ],
        ),
        migrations.AddField(
            model_name='checkout',
            name='project',
            field=models.ForeignKey(on_delete=django.db.models.deletion.CASCADE, to='director.Project'),
        ),
        migrations.AlterUniqueTogether(
            name='stencilaproject',
            unique_together={('name', 'owner')},
        ),
    ]