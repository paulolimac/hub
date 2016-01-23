# -*- coding: utf-8 -*-
# Generated by Django 1.9.1 on 2016-01-23 03:59
from __future__ import unicode_literals

from django.db import migrations, models


class Migration(migrations.Migration):

    dependencies = [
        ('users', '0004_userevent'),
    ]

    operations = [
        migrations.AddField(
            model_name='userdetails',
            name='tester',
            field=models.BooleanField(default=False, help_text='Is this user a tester of new features?'),
        ),
    ]