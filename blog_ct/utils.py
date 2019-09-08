import datetime
import json
from blog_ct.models import PinnedApplication
from collections import OrderedDict
from blog_ct import settings
from django.template import Context
from django.utils import translation
from django.apps.registry import apps
from django.core.serializers.json import DjangoJSONEncoder
from django.http import HttpResponse
from django.urls import reverse, resolve, NoReverseMatch
from django.contrib.admin import AdminSite
from django.utils.encoding import smart_text, force_text
from django.utils.text import capfirst
from django.contrib import messages
from django.utils.functional import Promise
from django.contrib.admin.options import IncorrectLookupParameters
from django.contrib import admin
from django.utils.translation import ugettext_lazy as _
from django.utils.text import slugify

def get_menu_items(context):
    pinned_apps = PinnedApplication.objects.filter(user=context['user'].pk).values_list('app_label', flat=True)
    original_app_list = OrderedDict(map(lambda app: (app['app_label'], app), get_original_menu_items(context)))
    custom_app_list = settings.CT_SIDE_MENU_ITEMS
    custom_app_list_deprecated = settings.CT_SIDE_MENU_CUSTOM_APPS

    if custom_app_list not in (None, False):
        if isinstance(custom_app_list, dict):
            admin_site = get_admin_site(context)
            custom_app_list = custom_app_list.get(admin_site.name, [])

        app_list = []

        def get_menu_item_app_model(app_label, data):
            item = {'has_perms': True}

            if 'name' in data:
                parts = data['name'].split('.', 2)

                if len(parts) > 1:
                    app_label, name = parts
                else:
                    name = data['name']

                if app_label in original_app_list:
                    models = dict(map(
                        lambda x: (x['name'], x),
                        original_app_list[app_label]['models']
                    ))

                    if name in models:
                        item = models[name].copy()

            if 'label' in data:
                item['label'] = data['label']

            if 'url' in data:
                item['url'] = get_menu_item_url(data['url'], original_app_list)

            if 'url_blank' in data:
                item['url_blank'] = data['url_blank']

            if 'permissions' in data:
                item['has_perms'] = item.get('has_perms', True) and context['user'].has_perms(data['permissions'])

            return item

        def get_menu_item_app(data):
            app_label = data.get('app_label')

            if not app_label:
                if 'label' not in data:
                    raise Exception('Custom menu items should at least have \'label\' or \'app_label\' key')
                app_label = 'custom_%s' % slugify(data['label'], allow_unicode=True)

            if app_label in original_app_list:
                item = original_app_list[app_label].copy()
            else:
                item = {'app_label': app_label, 'has_perms': True}

            if 'label' in data:
                item['label'] = data['label']

            if 'items' in data:
                item['items'] = list(map(lambda x: get_menu_item_app_model(app_label, x), data['items']))

            if 'url' in data:
                item['url'] = get_menu_item_url(data['url'], original_app_list)

            if 'url_blank' in data:
                item['url_blank'] = data['url_blank']

            if 'permissions' in data:
                item['has_perms'] = item.get('has_perms', True) and context['user'].has_perms(data['permissions'])

            item['pinned'] = item['app_label'] in pinned_apps

            return item

        for data in custom_app_list:
            item = get_menu_item_app(data)
            app_list.append(item)
    elif custom_app_list_deprecated not in (None, False):
        app_dict = {}
        models_dict = {}

        for app in original_app_list.values():
            app_label = app['app_label']
            app_dict[app_label] = app

            for model in app['models']:
                if app_label not in models_dict:
                    models_dict[app_label] = {}

                models_dict[app_label][model['object_name']] = model

            app['items'] = []

        app_list = []

        if isinstance(custom_app_list_deprecated, dict):
            admin_site = get_admin_site(context)
            custom_app_list_deprecated = custom_app_list_deprecated.get(admin_site.name, [])

        for item in custom_app_list_deprecated:
            app_label, models = item

            if app_label in app_dict:
                app = app_dict[app_label]

                for model_label in models:
                    if model_label == '__all__':
                        app['items'] = models_dict[app_label].values()
                        break
                    elif model_label in models_dict[app_label]:
                        model = models_dict[app_label][model_label]
                        app['items'].append(model)

                app_list.append(app)
    else:
        def map_item(item):
            item['items'] = item['models']
            return item
        app_list = list(map(map_item, original_app_list.values()))

    current_found = False

    for app in app_list:
        if not current_found:
            for model in app['items']:
                if not current_found and model.get('url') and context['request'].path.startswith(model['url']):
                    model['current'] = True
                    current_found = True
                else:
                    model['current'] = False

            if not current_found and app.get('url') and context['request'].path.startswith(app['url']):
                app['current'] = True
                current_found = True
            else:
                app['current'] = False

    return app_list

def get_admin_site(context):
    try:
        current_resolver = resolve(context.get('request').path)
        index_resolver = resolve(reverse('%s:index' % current_resolver.namespaces[0]))

        if hasattr(index_resolver.func, 'admin_site'):
            return index_resolver.func.admin_site

        for func_closure in index_resolver.func.__closure__:
            if isinstance(func_closure.cell_contents, AdminSite):
                return func_closure.cell_contents
    except:
        pass

    return admin.site

def get_menu_item_url(url, original_app_list):
    if isinstance(url, dict):
        url_type = url.get('type')

        if url_type == 'app':
            return original_app_list[url['app_label']]['url']
        elif url_type == 'model':
            models = dict(map(
                lambda x: (x['name'], x['url']),
                original_app_list[url['app_label']]['models']
            ))
            return models[url['model']]
        elif url_type == 'reverse':
            return reverse(url['name'], args=url.get('args'), kwargs=url.get('kwargs'))
    elif isinstance(url, str):
        return url