"""Cliente dos serviços de Facturação Electrónica da AGT.

Documentação: https://quiosqueagt.minfin.gov.ao/doc-agt/faturacao-electronica/1/

Os nomes dos campos de listarFacturas (queryStartDate/queryEndDate) e a forma da
resposta ainda não foram confirmados contra a documentação oficial; estão
concentrados aqui para serem fáceis de ajustar.
"""

import time
import uuid
from datetime import datetime, timezone

import jwt
import requests


class ErroAGT(Exception):
    def __init__(self, status, corpo):
        self.status = status
        self.corpo = corpo
        super().__init__(f"AGT respondeu HTTP {status}: {corpo}")


class ClienteAGT:
    def __init__(self, config, sessao=None, tentativas=4, espera=2.0):
        self.config = config
        self.sessao = sessao or requests.Session()
        self.sessao.auth = (config.utilizador, config.senha)
        self.tentativas = tentativas
        self.espera = espera

    def _assinar(self, campos):
        """Assinatura JWS compacta RS256 dos campos indicados por cada serviço."""
        return jwt.encode(campos, self.config.chave_privada_pem, algorithm="RS256")

    def _base(self):
        return {
            "schemaVersion": "1.0",
            "submissionId": str(uuid.uuid4()),
            "taxRegistrationNumber": self.config.nif,
            "submissionTimeStamp": datetime.now(timezone.utc).strftime("%Y-%m-%dT%H:%M:%SZ"),
            "softwareInfo": {
                "softwareInfoDetail": {
                    "productId": self.config.product_id,
                    "productVersion": self.config.product_version,
                    "softwareValidationNumber": self.config.software_validation_number,
                },
                "jwsSoftwareSignature": self.config.jws_software_signature,
            },
        }

    def _post(self, servico, corpo):
        url = f"{self.config.base_url}/{servico}"
        for tentativa in range(self.tentativas):
            resposta = self.sessao.post(url, json=corpo, timeout=60)
            # 429 = E98 (demasiados pedidos repetidos): espera e tenta de novo
            if resposta.status_code == 429 and tentativa < self.tentativas - 1:
                time.sleep(self.espera * 2**tentativa)
                continue
            if resposta.status_code >= 400:
                try:
                    detalhe = resposta.json()
                except ValueError:
                    detalhe = resposta.text
                raise ErroAGT(resposta.status_code, detalhe)
            return resposta.json()

    def listar_facturas(self, data_inicio, data_fim):
        """Facturas comunicadas pelo NIF entre duas datas (YYYY-MM-DD)."""
        corpo = self._base()
        corpo["queryStartDate"] = data_inicio
        corpo["queryEndDate"] = data_fim
        corpo["jwsSignature"] = self._assinar(
            {
                "taxRegistrationNumber": self.config.nif,
                "queryStartDate": data_inicio,
                "queryEndDate": data_fim,
            }
        )
        return self._post("listarFacturas", corpo)

    def consultar_factura(self, numero_documento):
        """Detalhe de um documento comunicado (ex.: 'FT A/123')."""
        corpo = self._base()
        corpo["documentNo"] = numero_documento
        corpo["jwsSignature"] = self._assinar(
            {"taxRegistrationNumber": self.config.nif, "documentNo": numero_documento}
        )
        return self._post("consultarFactura", corpo)


def extrair_documentos(resposta):
    """Devolve a primeira lista de objectos encontrada na resposta de listarFacturas."""
    if isinstance(resposta, list):
        return [d for d in resposta if isinstance(d, dict)]
    if isinstance(resposta, dict):
        for valor in resposta.values():
            if isinstance(valor, list) and valor and all(isinstance(d, dict) for d in valor):
                return valor
        for valor in resposta.values():
            encontrados = extrair_documentos(valor)
            if encontrados:
                return encontrados
    return []


def numero_do_documento(documento):
    for chave in ("documentNo", "invoiceNo", "documentNumber"):
        if documento.get(chave):
            return documento[chave]
    return None
