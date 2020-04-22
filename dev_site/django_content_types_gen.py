import django
django.setup()
# https://medium.com/@gauravtoshniwal/how-to-create-content-types-and-permissions-for-already-created-tables-89a3647ff720
from django.apps.registry import apps

apps_all = apps.get_app_configs()
print(apps_all)
for app in apps_all:
    print(f'Generating for: {app.name}: {app.label}')

    app_config = apps.get_app_config(app.label)

    # To create Content Types
    from django.contrib.contenttypes.management import create_contenttypes
    create_contenttypes(app_config)

    # To create Permissions
    from django.contrib.auth.management import create_permissions
    create_permissions(app_config)


# # Add users to new groups:
# from django.contrib.auth.models import Group, User
#
# g = Group.objects.get(name='Read and execute')
# users = User.objects.all()
# for u in users:
#     g.user_set.add(u)