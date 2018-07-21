# Generated by Django 2.0.7 on 2018-07-21 05:13

from django.db import migrations, models
import django.db.models.deletion


class Migration(migrations.Migration):

    initial = True

    dependencies = [
        ('projects', '0001_initial'),
        ('checkouts', '0003_checkout_host'),
    ]

    operations = [
        migrations.AddField(
            model_name='checkout',
            name='project',
            field=models.ForeignKey(blank=True, null=True, on_delete=django.db.models.deletion.SET_NULL, related_name='checkouts', to='projects.Project'),
        ),
    ]