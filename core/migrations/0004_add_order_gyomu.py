from django.db import migrations, models


def set_initial_order_gyomu(apps, schema_editor):
    Employee = apps.get_model('core', 'Employee')
    # assign sequential order_gyomu values based on id ordering
    for i, emp in enumerate(Employee.objects.all().order_by('id')):
        emp.order_gyomu = i + 1
        emp.save()


class Migration(migrations.Migration):

    dependencies = [
        ('core', '0003_populate_data'),
    ]

    operations = [
        migrations.AddField(
            model_name='employee',
            name='order_gyomu',
            field=models.IntegerField(default=0),
        ),
        migrations.RunPython(set_initial_order_gyomu),
    ]
