"""DNS Authenticator for FreeDNS DNS."""
import logging

import zope.interface
from lexicon.providers import freedns

from certbot import errors
from certbot import interfaces
from certbot.plugins import dns_common
from certbot.plugins import dns_common_lexicon

logger = logging.getLogger(__name__)

ACCOUNT_URL = 'https://freedns.afraid.org/profile'


@zope.interface.implementer(interfaces.IAuthenticator)
@zope.interface.provider(interfaces.IPluginFactory)
class Authenticator(dns_common.DNSAuthenticator):
    """DNS Authenticator for FreeDNS

    This Authenticator uses the FreeDNS v2 API to fulfill a dns-01 challenge.
    """

    description = 'Obtain certificates using a DNS TXT record (if you are using FreeDNS for DNS).'
    ttl = 60

    def __init__(self, *args, **kwargs):
        super(Authenticator, self).__init__(*args, **kwargs)
        self.credentials = None

    @classmethod
    def add_parser_arguments(cls, add):  # pylint: disable=arguments-differ
        super(Authenticator, cls).add_parser_arguments(add, default_propagation_seconds=60)
        add('credentials', help='FreeDNS credentials INI file.')

    def more_info(self):  # pylint: disable=missing-docstring,no-self-use
        return 'This plugin configures a DNS TXT record to respond to a dns-01 challenge using ' + \
               'the FreeDNS API.'

    def _setup_credentials(self):
        self.credentials = self._configure_credentials(
            'credentials',
            'FreeDNS credentials INI file',
            {
                'username': 'Username for FreeDNS login. (See {0}.)'.format(ACCOUNT_URL),
                'password': 'Password for the same. Same URL to configure'
            }
        )

    def _perform(self, domain, validation_name, validation):
        self._get_freedns_client().add_txt_record(domain, validation_name, validation)

    def _cleanup(self, domain, validation_name, validation):
        self._get_freedns_client().del_txt_record(domain, validation_name, validation)

    def _get_freedns_client(self):
        return _FreeDNSLexiconClient(self.credentials.conf('token'), self.ttl)


class _FreeDNSLexiconClient(dns_common_lexicon.LexiconClient):
    """
    Encapsulates all communication with the FreeDNS via Lexicon.
    """

    def __init__(self, token, ttl):
        super(_FreeDNSLexiconClient, self).__init__()

        config = dns_common_lexicon.build_lexicon_config('dnssimple', {
            'ttl': ttl,
        }, {
            'auth_token': token,
        })

        self.provider = freedns.Provider(config)

    def _handle_http_error(self, e, domain_name):
        hint = None
        if str(e).startswith('401 Client Error: Unauthorized for url:'):
            hint = 'Is your API token value correct?'

        return errors.PluginError('Error determining zone identifier for {0}: {1}.{2}'
                                  .format(domain_name, e, ' ({0})'.format(hint) if hint else ''))
