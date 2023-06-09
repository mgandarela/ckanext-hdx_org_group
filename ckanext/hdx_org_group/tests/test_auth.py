'''
Created on Jul 24, 2014

@author: alexandru-m-g
'''
import datetime
import logging as logging

import ckan.lib.helpers as h
import ckan.model as model
import ckan.tests.factories as factories
import ckan.tests.helpers as helpers
import ckan.tests.legacy as tests
import ckanext.hdx_org_group.tests as org_group_base
import ckanext.hdx_theme.tests.hdx_test_base as hdx_test_base

from ckanext.hdx_org_group.tests.test_data_completeness import _generate_dataset_dict

log = logging.getLogger(__name__)


class TestOrgAuth(org_group_base.OrgGroupBaseTest):

    @classmethod
    def _load_plugins(cls):
        hdx_test_base.load_plugin('ytp_request hdx_org_group hdx_theme')

    @classmethod
    def _get_action(cls, action_name):
        return tests.get_action(action_name)

    def test_create_org(self):
        user = model.User.by_name('tester')
        tests.call_action_api(self.app, 'organization_create', name='test_org_a',
                              title='Test Org A',
                              apikey=user.apikey, status=403)
        testsysadmin = model.User.by_name('testsysadmin')
        tests.call_action_api(self.app, 'organization_create', name='test_org_a_admin',
                              title='Test Org A Admin',
                              apikey=testsysadmin.apikey, status=200)
        assert True

    def test_edit_org(self):
        testsysadmin = model.User.by_name('testsysadmin')
        user = model.User.by_name('tester')
        create_result = tests.call_action_api(self.app, 'organization_create',
                                              name='test_org_b', title='Test Org B',
                                              apikey=testsysadmin.apikey, status=200)
        tests.call_action_api(self.app, 'organization_update', id=create_result['id'],
                              title='Test Org B CHANGED',
                              apikey=user.apikey, status=403)
        assert True, 'user should not be allowed to modify the org'

    def test_delete_org(self):
        testsysadmin = model.User.by_name('testsysadmin')
        user = model.User.by_name('tester')
        create_result = tests.call_action_api(self.app, 'organization_create',
                                              name='test_org_c', title='Test Org C',
                                              apikey=testsysadmin.apikey, status=200)
        tests.call_action_api(self.app, 'organization_delete', id=create_result['id'],
                                       apikey=user.apikey, status=403)
        assert True, 'user should not be allowed to delete the org'

    def test_create_org_member(self):
        testsysadmin = model.User.by_name('testsysadmin')
        user = model.User.by_name('tester')
        create_result = tests.call_action_api(self.app, 'organization_create',
                                              name='test_org_d', title='Test Org D',
                                              apikey=testsysadmin.apikey, status=200)
        tests.call_action_api(self.app, 'organization_member_create',
                              id=create_result['id'], username='tester', role='editor',
                              apikey=user.apikey, status=403)
        assert True, 'user shoudn\'t be allowed to add himself as a member'

    def test_remove_self_org_member(self):
        testsysadmin = model.User.by_name('testsysadmin')
        user = model.User.by_name('tester')
        create_result = tests.call_action_api(self.app, 'organization_create',
                                              name='test_org_e', title='Test Org E',
                                              apikey=testsysadmin.apikey, status=200)

        tests.call_action_api(self.app, 'organization_member_create',
                              id=create_result['id'], username='annafan', role='member',
                              apikey=testsysadmin.apikey, status=200)

        for role in ('editor', 'member'):
            tests.call_action_api(self.app, 'organization_member_create',
                                  id=create_result['id'], username='tester', role=role,
                                  apikey=testsysadmin.apikey, status=200)

            tests.call_action_api(self.app, 'organization_member_delete',
                                  id=create_result['id'], username='annafan',
                                  apikey=user.apikey, status=403)

            assert True, 'a {} shouldn\'t be able to remove any other member from the org'.format(role)

            tests.call_action_api(self.app, 'organization_member_delete',
                              id=create_result['id'], username='tester',
                              apikey=user.apikey, status=200)

            assert True, 'any member should be able to remove himself from an org'

        tests.call_action_api(self.app, 'organization_member_create',
                              id=create_result['id'], username='tester', role='admin',
                              apikey=testsysadmin.apikey, status=200)

        tests.call_action_api(self.app, 'organization_member_delete',
                              id=create_result['id'], username='annafan',
                              apikey=user.apikey, status=200)
        assert True, 'an admin should be able to remove any other member from the org'

        tests.call_action_api(self.app, 'organization_member_delete',
                              id=create_result['id'], username='tester',
                              apikey=user.apikey, status=200)

        assert True, 'any member should be able to remove himself from an org'

    def test_maintainer_protection(self):
        testsysadmin = model.User.by_name('testsysadmin')
        user = model.User.by_name('tester')
        create_result = tests.call_action_api(self.app, 'organization_create',
                                              name='test_org_maintainer', title='Test Org Maintainer',
                                              apikey=testsysadmin.apikey, status=200)

        tests.call_action_api(self.app, 'organization_member_create',
                              id=create_result['id'], username='tester', role='editor',
                              apikey=testsysadmin.apikey, status=200)

        group = factories.Group(name='some_location')
        dataset = _generate_dataset_dict('dataset-maintainer1', 'test_org_maintainer', group.get('name'), datetime.datetime.utcnow(), user.id, True)

        tests.call_action_api(self.app, 'organization_member_delete',
                              id=create_result['id'], username=user.id,
                              apikey=testsysadmin.apikey, status=500)
        assert True, 'an admin should not be able to remove member if maintainer of a dataset belonging to current org'

        tests.call_action_api(self.app, 'organization_member_create',
                              id=create_result['id'], username=user.id, role='member',
                              apikey=testsysadmin.apikey, status=500)
        assert True, 'an admin should not be able to change role to member if user is maintainer of a dataset belonging to current org'

        #remove dataset
        helpers.call_action(
            "package_delete", context={"user": testsysadmin.name}, **dataset
        )

        tests.call_action_api(self.app, 'organization_member_delete',
                              id=create_result['id'], username=user.id,
                              apikey=testsysadmin.apikey, status=200)
        assert True, 'an admin should be able to remove member if not maintainer'

    def test_new_org_request_page(self):
        offset = h.url_for('hdx_org.request_new')
        result = self.app.get(offset)
        assert result.status_code == 403
        assert 'You don\'t have permission to access this page' in result.body

    def test_new_org_request(self):
        tests.call_action_api(self.app, 'hdx_send_new_org_request',
                           title='Org Title', description='Org Description',
                           org_url='http://test-org.com/',
                           your_name='Some Name', your_email='test@test.com',
                           status=403)

    def test_editor_request_for_org(self):
        tests.call_action_api(self.app, 'hdx_send_editor_request_for_org',
                           display_name='User Name', name='username',
                           email='test@test.com',
                           organization='Org Name', message='Some message',
                           admins=[],
                           status=403)

    # TODO need to align with the new membership request YTP extension
    # def test_request_membership(self):
    #     tests.call_action_api(self.app, 'hdx_send_request_membership',
    #                        display_name='User Name', name='username',
    #                        email='test@test.com',
    #                        organization='Org Name', message='Some message',
    #                        admins=[],
    #                        status=403)

class TestGroupAuth(org_group_base.OrgGroupBaseTest):

    @classmethod
    def _load_plugins(cls):
        hdx_test_base.load_plugin('ytp_request hdx_org_group hdx_theme')

    def test_create_country(self):
        user = model.User.by_name('tester')
        tests.call_action_api(self.app, 'group_create', name='test_group_a',
                              title='Test Group A',
                              apikey=user.apikey, status=403)
        assert True

    def test_edit_country(self):
        testsysadmin = model.User.by_name('testsysadmin')
        user = model.User.by_name('tester')
        create_result = tests.call_action_api(self.app, 'group_create',
                                              name='test_group_b', title='Test Group B',
                                              apikey=testsysadmin.apikey, status=200)
        tests.call_action_api(self.app, 'group_update', id=create_result['id'],
                                       title='Test Group B CHANGED',
                                       apikey=user.apikey, status=403)
        assert True, 'user should not be allowed to modify the group'

    def test_delete_country(self):
        testsysadmin = model.User.by_name('testsysadmin')
        user = model.User.by_name('tester')
        create_result = tests.call_action_api(self.app, 'group_create',
                                              name='test_group_c', title='Test Group C',
                                              apikey=testsysadmin.apikey, status=200)
        tests.call_action_api(self.app, 'group_delete', id=create_result['id'],
                                       apikey=user.apikey, status=403)
        assert True, 'user should not be allowed to delete the group'

    def test_create_country_member(self):
        testsysadmin = model.User.by_name('testsysadmin')
        tester = model.User.by_name('tester')
        create_result = tests.call_action_api(self.app, 'group_create',
                                              name='test_group_d', title='Test Group D',
                                              apikey=testsysadmin.apikey, status=200)
        tests.call_action_api(self.app, 'group_member_create',
                              id=create_result['id'], username='tester', role='editor',
                              apikey=tester.apikey, status=403)
        assert True, 'Country members shouldn\'t be allowed'
