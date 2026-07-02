import hashlib
import unittest
from types import SimpleNamespace
from unittest.mock import patch, MagicMock

from apps.integrations.models import ApiClient
from apps.integrations.authentication import ApiKeyAuthentication
from apps.integrations.permissions import EsApiClientActivo
from apps.accounts.models import Institucion


class TestApiClientModel(unittest.TestCase):
	def test_verificar_key_uses_sha256_and_filters(self):
		raw = 'mi-secreta-key'
		expected_hash = hashlib.sha256(raw.encode()).hexdigest()

		# Patch the manager to provide a query-like chain
		with patch('apps.integrations.models.ApiClient.objects') as mock_manager:
			q = MagicMock()
			q.filter.return_value = q
			q.select_related.return_value = q
			q.first.return_value = 'SENTINEL_CLIENT'
			mock_manager.filter.return_value = q

			result = ApiClient.verificar_key(raw)

			# manager.filter should be called first with the hash and activo=True
			mock_manager.filter.assert_called_once()
			called_kwargs = mock_manager.filter.call_args.kwargs
			assert called_kwargs.get('api_key_hash') == expected_hash
			assert called_kwargs.get('activo') is True

			# the chained queryset.filter should have been used for the expiration check
			q.filter.assert_called()
			q.select_related.assert_called_once_with('institucion')
			assert result == 'SENTINEL_CLIENT'


class TestApiKeyAuthentication(unittest.TestCase):
	def test_authenticate_returns_none_when_header_missing(self):
		auth = ApiKeyAuthentication()
		req = SimpleNamespace(headers={})
		assert auth.authenticate(req) is None

	def test_authenticate_raises_when_key_invalid(self):
		auth = ApiKeyAuthentication()
		req = SimpleNamespace(headers={auth.keyword: 'bad-key'})

		with patch('apps.integrations.authentication.ApiClient') as mock_model:
			mock_model.verificar_key.return_value = None
			try:
				auth.authenticate(req)
			except Exception as e:
				from rest_framework.exceptions import AuthenticationFailed

				assert isinstance(e, AuthenticationFailed)
			else:
				raise AssertionError('AuthenticationFailed not raised')

	def test_authenticate_returns_client_and_raw_key_when_valid(self):
		auth = ApiKeyAuthentication()
		req = SimpleNamespace(headers={auth.keyword: 'raw-key-123'})

		fake_client = SimpleNamespace(id=1)
		with patch('apps.integrations.authentication.ApiClient') as mock_model:
			mock_model.verificar_key.return_value = fake_client
			user, raw = auth.authenticate(req)
			assert user is fake_client
			assert raw == 'raw-key-123'


class TestEsApiClientActivoPermission(unittest.TestCase):
	def test_has_permission_true_for_active_client_and_institucion(self):
		institucion = Institucion(activo=True)
		client = ApiClient(institucion=institucion, nombre_cliente_api='x', api_key_hash='h', activo=True)
		req = SimpleNamespace(user=client)
		perm = EsApiClientActivo()
		assert perm.has_permission(req, None) is True

	def test_has_permission_false_for_missing_user(self):
		perm = EsApiClientActivo()
		req = SimpleNamespace(user=None)
		assert perm.has_permission(req, None) is False

	def test_has_permission_false_for_inactive_client_or_institucion(self):
		institucion = Institucion(activo=False)
		client = ApiClient(institucion=institucion, nombre_cliente_api='x', api_key_hash='h', activo=True)
		req = SimpleNamespace(user=client)
		perm = EsApiClientActivo()
		assert perm.has_permission(req, None) is False


if __name__ == '__main__':
	unittest.main()
