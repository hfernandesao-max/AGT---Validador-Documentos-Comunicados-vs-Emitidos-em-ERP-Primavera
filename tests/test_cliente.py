import jwt
from cryptography.hazmat.primitives import serialization
from cryptography.hazmat.primitives.asymmetric import rsa

from agt_consulta.__main__ import achatar
from agt_consulta.cliente import ClienteAGT, ErroAGT, extrair_documentos
from agt_consulta.config import Config

CHAVE = rsa.generate_private_key(public_exponent=65537, key_size=2048)
PEM = CHAVE.private_bytes(
    serialization.Encoding.PEM,
    serialization.PrivateFormat.PKCS8,
    serialization.NoEncryption(),
).decode()


class Resposta:
    def __init__(self, status, corpo):
        self.status_code = status
        self._corpo = corpo
        self.text = str(corpo)

    def json(self):
        return self._corpo


class SessaoFalsa:
    def __init__(self, respostas):
        self.respostas = list(respostas)
        self.pedidos = []
        self.auth = None

    def post(self, url, json, timeout):
        self.pedidos.append((url, json))
        return self.respostas.pop(0)


def config():
    return Config("5000000000", "u", "s", PEM, "P", "1.0", "123", "sig", "https://x/sigt/fe/v1")


def test_consultar_factura_assina_campos():
    sessao = SessaoFalsa([Resposta(200, {"documentNo": "FT A/1"})])
    cliente = ClienteAGT(config(), sessao=sessao)
    assert cliente.consultar_factura("FT A/1") == {"documentNo": "FT A/1"}

    url, corpo = sessao.pedidos[0]
    assert url == "https://x/sigt/fe/v1/consultarFactura"
    assert sessao.auth == ("u", "s")
    assinado = jwt.decode(corpo["jwsSignature"], CHAVE.public_key(), algorithms=["RS256"])
    assert assinado == {"taxRegistrationNumber": "5000000000", "documentNo": "FT A/1"}


def test_repete_quando_429():
    sessao = SessaoFalsa([Resposta(429, {"code": "E98"}), Resposta(200, {"ok": True})])
    cliente = ClienteAGT(config(), sessao=sessao, espera=0)
    assert cliente.listar_facturas("2026-09-01", "2026-09-30") == {"ok": True}
    assert len(sessao.pedidos) == 2


def test_erro_http():
    sessao = SessaoFalsa([Resposta(400, {"code": "E93"})])
    cliente = ClienteAGT(config(), sessao=sessao)
    try:
        cliente.consultar_factura("X")
    except ErroAGT as e:
        assert e.status == 400
    else:
        raise AssertionError("devia falhar")


def test_extrair_documentos_e_achatar():
    resposta = {"resultado": {"documentList": [{"documentNo": "FT A/1", "totais": {"bruto": 10}}]}}
    docs = extrair_documentos(resposta)
    assert docs[0]["documentNo"] == "FT A/1"
    assert achatar(docs[0]) == {"documentNo": "FT A/1", "totais.bruto": 10}
