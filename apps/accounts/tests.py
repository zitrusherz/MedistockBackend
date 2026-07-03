from django.test import SimpleTestCase
from django.core.exceptions import ValidationError

from .models import (
	Usuario,
	Institucion,
	PerfilTrabajador,
	PerfilCliente,
)
from .validators import validar_rut


class ValidatorsTests(SimpleTestCase):
	def test_validar_rut_short_raises(self):
		with self.assertRaises(ValidationError):
			validar_rut("1")

	def test_validar_rut_invalid_chars_raises(self):
		with self.assertRaises(ValidationError):
			validar_rut("ABC.DEF-G")


class ModelStrAndCleanTests(SimpleTestCase):
	def test_usuario_str_returns_username(self):
		u = Usuario(username="john")
		self.assertEqual(str(u), "john")

	def test_institucion_str_returns_razon_social(self):
		i = Institucion(razon_social="ACME Ltda")
		self.assertEqual(str(i), "ACME Ltda")

	def test_perfil_trabajador_str_returns_rut(self):
		p = PerfilTrabajador(rut="11111111-1")
		self.assertEqual(str(p), "11111111-1")

	def test_perfil_cliente_str_prefers_rut(self):
		c = PerfilCliente(rut="22222222-2", pasaporte=None)
		self.assertEqual(str(c), "22222222-2")

	def test_perfil_cliente_str_uses_pasaporte_when_no_rut(self):
		c = PerfilCliente(rut=None, pasaporte="P-12345")
		self.assertEqual(str(c), "Pasaporte: P-12345")

	def test_perfil_cliente_clean_requires_document(self):
		c = PerfilCliente(tipo_cliente="PARTICULAR", rut=None, pasaporte=None)
		with self.assertRaises(ValidationError) as cm:
			c.clean()
		self.assertIn("Debe proporcionar al menos un documento", str(cm.exception))

	def test_perfil_cliente_clean_cannot_have_both_documents(self):
		c = PerfilCliente(tipo_cliente="PARTICULAR", rut="11111111-1", pasaporte="P-1")
		with self.assertRaises(ValidationError) as cm:
			c.clean()
		self.assertIn("No se pueden registrar ambos documentos", str(cm.exception))

	def test_perfil_cliente_institucional_requires_rut(self):
		c = PerfilCliente(tipo_cliente="INSTITUCIONAL", rut=None, pasaporte=None)

		with self.assertRaises(ValidationError) as cm:
			c.clean()

		self.assertIn("rut", cm.exception.message_dict)
		self.assertIn(
			"Los clientes de tipo Institucional requieren obligatoriamente un RUT.",
			cm.exception.message_dict["rut"],
		)
