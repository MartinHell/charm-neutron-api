from test_utils import CharmTestCase
from test_utils import patch_open
from mock import patch, MagicMock
import neutron_api_context as context
import charmhelpers
TO_PATCH = [
    'relation_get',
    'relation_ids',
    'related_units',
    'config',
    'determine_api_port',
    'determine_apache_port'
]


class IdentityServiceContext(CharmTestCase):
    def setUp(self):
        super(IdentityServiceContext, self).setUp(context, TO_PATCH)
        self.relation_get.side_effect = self.test_relation.get
        self.config.side_effect = self.test_config.get
        self.test_config.set('region', 'region457')

    @patch.object(charmhelpers.contrib.openstack.context, 'context_complete')
    @patch.object(charmhelpers.contrib.openstack.context, 'relation_get')
    @patch.object(charmhelpers.contrib.openstack.context, 'related_units')
    @patch.object(charmhelpers.contrib.openstack.context, 'relation_ids')
    @patch.object(charmhelpers.contrib.openstack.context, 'log')
    def test_ids_ctxt(self, _log, _rids, _runits, _rget, _ctxt_comp):
        _rids.return_value = 'rid1'
        _runits.return_value = 'runit'
        _ctxt_comp.return_value = True
        id_data = {
            'service_port': 9876,
            'service_host': '127.0.0.4',
            'auth_host': '127.0.0.5',
            'auth_port': 5432,
            'service_tenant': 'ten',
            'service_username': 'admin',
            'service_password': 'adminpass',
        }
        _rget.return_value = id_data
        ids_ctxt = context.IdentityServiceContext()
        self.assertEquals(ids_ctxt()['region'], 'region457')

    @patch.object(charmhelpers.contrib.openstack.context, 'relation_ids')
    @patch.object(charmhelpers.contrib.openstack.context, 'log')
    def test_ids_ctxt_no_rels(self, _log, _rids):
        _rids.return_value = []
        ids_ctxt = context.IdentityServiceContext()
        self.assertEquals(ids_ctxt(), None)


class HAProxyContextTest(CharmTestCase):

    def setUp(self):
        super(HAProxyContextTest, self).setUp(context, TO_PATCH)
        self.determine_api_port.return_value = 9686
        self.determine_apache_port.return_value = 9686

    def tearDown(self):
        super(HAProxyContextTest, self).tearDown()

    @patch.object(charmhelpers.contrib.openstack.context, 'relation_ids')
    @patch.object(charmhelpers.contrib.openstack.context, 'log')
    def test_context_No_peers(self, _log, _rids):
        _rids.return_value = []
        hap_ctxt = context.HAProxyContext()
        self.assertTrue('units' not in hap_ctxt())

    @patch.object(charmhelpers.contrib.openstack.context, 'config')
    @patch.object(charmhelpers.contrib.openstack.context, 'local_unit')
    @patch.object(charmhelpers.contrib.openstack.context, 'unit_get')
    @patch.object(charmhelpers.contrib.openstack.context, 'relation_get')
    @patch.object(charmhelpers.contrib.openstack.context, 'related_units')
    @patch.object(charmhelpers.contrib.openstack.context, 'relation_ids')
    @patch.object(charmhelpers.contrib.openstack.context, 'log')
    def test_context_peers(self, _log, _rids, _runits, _rget, _uget,
                           _lunit, _config):
        unit_addresses = {
            'neutron-api-0': '10.10.10.10',
            'neutron-api-1': '10.10.10.11',
        }
        _rids.return_value = ['rid1']
        _runits.return_value = ['neutron-api/0']
        _rget.return_value = unit_addresses['neutron-api-0']
        _lunit.return_value = "neutron-api/1"
        _uget.return_value = unit_addresses['neutron-api-1']
        _config.return_value = None
        service_ports = {'neutron-server': [9696, 9686]}

        ctxt_data = {
            'units': unit_addresses,
            'service_ports': service_ports,
            'neutron_bind_port': 9686,
        }
        with patch_open() as (_open, _file):
            _file.write = MagicMock()
            hap_ctxt = context.HAProxyContext()
            self.assertEquals(hap_ctxt(), ctxt_data)
            _file.write.assert_called_with('ENABLED=1\n')


class NeutronAPIContextsTest(CharmTestCase):

    def setUp(self):
        super(NeutronAPIContextsTest, self).setUp(context, TO_PATCH)
        self.relation_get.side_effect = self.test_relation.get
        self.config.side_effect = self.test_config.get
        self.api_port = 9696
        self.determine_api_port.return_value = self.api_port
        self.test_config.set('neutron-plugin', 'ovs')
        self.test_config.set('neutron-security-groups', True)
        self.test_config.set('debug', True)
        self.test_config.set('verbose', True)
        self.test_config.set('neutron-external-network', 'bob')

    def tearDown(self):
        super(NeutronAPIContextsTest, self).tearDown()

    @patch.object(context.NeutronCCContext, 'network_manager')
    @patch.object(context.NeutronCCContext, 'plugin')
    def test_neutroncc_context_no_setting(self, plugin, nm):
        plugin.return_value = None
        napi_ctxt = context.NeutronCCContext()
        ctxt_data = {
            'debug': True,
            'external_network': 'bob',
            'neutron_bind_port': self.api_port,
            'verbose': True,
        }
        with patch.object(napi_ctxt, '_ensure_packages'):
            self.assertEquals(ctxt_data, napi_ctxt())

    @patch.object(context.NeutronCCContext, 'network_manager')
    @patch.object(context.NeutronCCContext, 'plugin')
    def test_neutroncc_context_api_rel(self, plugin, nm):
        nova_url = 'http://127.0.0.10'
        plugin.return_value = None
        self.related_units.return_value = ['unit1']
        self.relation_ids.return_value = ['rid2']
        self.test_relation.set({'nova_url': nova_url})
        napi_ctxt = context.NeutronCCContext()
        self.assertEquals(nova_url, napi_ctxt()['nova_url'])
        self.assertEquals(self.api_port, napi_ctxt()['neutron_bind_port'])

    def test_neutroncc_context_manager(self):
        napi_ctxt = context.NeutronCCContext()
        self.assertEquals(napi_ctxt.network_manager, 'neutron')
        self.assertEquals(napi_ctxt.plugin, 'ovs')
        self.assertEquals(napi_ctxt.neutron_security_groups, True)

    def test_neutroncc_context_manager_pkgs(self):
        napi_ctxt = context.NeutronCCContext()
        with patch.object(napi_ctxt, '_ensure_packages') as ep:
            napi_ctxt._ensure_packages()
            ep.assert_has_calls([])
