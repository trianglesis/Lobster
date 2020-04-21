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


# # https://gist.github.com/bmihelac/3010093
# # changing verbose name of model does not change ContentType name
# # this script will loop through all ContentType objects and refresh names
#
# # optional activate translation
# from django.utils import translation
# translation.activate('en')
#
# from django.contrib.contenttypes.models import ContentType
# content_types = ContentType.objects.all()
#
# for ct in content_types:
#     model = ct.model_class()
#     if model:
#         ct.name = model._meta.verbose_name
#         ct.save()