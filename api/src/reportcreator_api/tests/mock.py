import random
from datetime import datetime, timedelta
from unittest import mock
from django.utils import timezone
from reportcreator_api.pentests.customfields.utils import HandleUndefinedFieldsOptions, ensure_defined_structure

from reportcreator_api.pentests.models import FindingTemplate, PentestFinding, PentestProject, ProjectType, UploadedAsset, UploadedImage
from reportcreator_api.pentests.customfields.predefined_fields import finding_field_order_default, finding_fields_default, report_fields_default, report_sections_default
from reportcreator_api.users.models import PentestUser
from reportcreator_api.utils.models import Language
from django.core.files.uploadedfile import SimpleUploadedFile


def create_user(**kwargs) -> PentestUser:
    username = f'user{random.randint(0, 100000)}'
    return PentestUser.objects.create(**{
        'username': username,
        'email': username + '@example.com',
        'first_name': 'Herbert',
        'last_name': 'Testinger',
    } | kwargs)


def create_template(**kwargs) -> FindingTemplate:
    data = {
        'title': f'Finding Template #{random.randint(1, 100000)}',
        'description': 'Template Description',
        'recommendation': 'Template Recommendation',
        'undefined_field': 'test',
    } | kwargs.pop('data', {})
    template =  FindingTemplate.objects.create(**{
        'language': Language.ENGLISH,
        'tags': ['web', 'dev'],
    } | kwargs)
    template.update_data(data)
    template.save()
    return template


def create_project_type(**kwargs) -> ProjectType:
    additional_fields = {
        'field_string': {'type': 'string', 'label': 'String Field', 'default': 'test'},
        'field_markdown': {'type': 'markdown', 'label': 'Markdown Field', 'default': '# test\nmarkdown'},
        'field_cvss': {'type': 'cvss', 'label': 'CVSS Field', 'default': 'n/a'},
        'field_date': {'type': 'date', 'label': 'Date Field', 'default': '2022-01-01'},
        'field_int': {'type': 'number', 'label': 'Number Field', 'default': 10},
        'field_bool': {'type': 'boolean', 'label': 'Boolean Field', 'default': False},
        'field_enum': {'type': 'enum', 'label': 'Enum Field', 'choices': [{'value': 'enum1', 'label': 'Enum Value 1'}, {'value': 'enum2', 'label': 'Enum Value 2'}], 'default': 'enum2'},
        'field_combobox': {'type': 'combobox', 'label': 'Combobox Field', 'suggestions': ['value 1', 'value 2'], 'default': 'value1'},
        'field_user': {'type': 'user', 'label': 'User Field'},
        'field_object': {'type': 'object', 'label': 'Nested Object', 'properties': {'nested1':  {'type': 'string', 'label': 'Nested Field'}}},
        'field_list': {'type': 'list', 'label': 'List Field', 'items': {'type': 'string'}},
        'field_list_objects': {'type': 'list', 'label': 'List of nested objects', 'items': {'type': 'object', 'properties': {'nested1': {'type': 'string', 'label': 'Nested object field', 'default': None}}}},
    }
    project_type = ProjectType.objects.create(**{
        'name': f'Project Type #{random.randint(1, 100000)}',
        'language': Language.ENGLISH,
        'report_fields': report_fields_default() | additional_fields,
        'report_sections': report_sections_default(),
        'finding_fields': finding_fields_default() | additional_fields,
        'finding_field_order': finding_field_order_default(),
        'report_template': '''<section><h1>{{ report.title }}</h1></section><section v-for="finding in findings"><h2>{{ finding.title }}</h2></section>''',
        'report_styles': '''@page { size: A4 portrait; } h1 { font-size: 3em; font-weight: bold; }''',
        'report_preview_data': {
            'report': {'title': 'Demo Report', 'field_string': 'test', 'field_int': 5, 'undefined_field': 'test'}, 
            'findings': [{'title': 'Demo finding', 'undefined_field': 'test'}]
        }
    } | kwargs)
    UploadedAsset.objects.create(linked_object=project_type, name='file1.png', file=SimpleUploadedFile(name='file1.png', content=b'file1'))
    UploadedAsset.objects.create(linked_object=project_type, name='file2.png', file=SimpleUploadedFile(name='file2.png', content=b'file2'))
    return project_type

def create_finding(project, template=None, **kwargs) -> PentestFinding:
    data = ensure_defined_structure(
        value={
            'title': f'Finding #{random.randint(0, 100000)}',
            'cvss': 'CVSS:3.1/AV:N/AC:L/PR:N/UI:N/S:U/C:H/I:H/A:H',
            'description': 'Finding Description',
            'recommendation': 'Finding Recommendation',
            'undefined_field': 'test',
        } | (template.data if template else {}),
        definition=project.project_type.finding_fields_obj,
        handle_undefined=HandleUndefinedFieldsOptions.FILL_DEFAULT,
        include_undefined=True,
    ) | kwargs.pop('data', {})
    finding = PentestFinding.objects.create(**{
        'project': project,
        'assignee': None,
        'template': template,
    } | kwargs)
    finding.update_data(data)
    finding.save()
    return finding

def create_project(project_type=None, pentesters=[], report_data={}, findings_kwargs=None, **kwargs) -> PentestProject:
    project_type = project_type or create_project_type()
    project = PentestProject.objects.create(**{
        'project_type': project_type,
        'name': f'Pentest Project #{random.randint(1, 100000)}',
        'language': Language.ENGLISH,
    } | kwargs)
    project.update_data({
        'title': 'Report title',
        'undefined_field': 'test',
    } | report_data)
    project.save()
    project.pentesters.add(*pentesters)

    for finding_kwargs in findings_kwargs if findings_kwargs is not None else [{}] * 3:
        create_finding(project=project, **finding_kwargs)

    UploadedImage.objects.create(linked_object=project, name='file1.png', file=SimpleUploadedFile(name='file1.png', content=b'\x89PNG\x0d\x0a\x1a\x0afile1'))
    UploadedImage.objects.create(linked_object=project, name='file2.png', file=SimpleUploadedFile(name='file2.png', content=b'\x89PNG\x0d\x0a\x1a\x0afile2'))

    return project


def mock_time(before=None, after=None):
    return mock.patch('django.utils.timezone.now',
                      lambda: datetime.now(tz=timezone.get_current_timezone()) - (before or timedelta()) + (after or timedelta()))