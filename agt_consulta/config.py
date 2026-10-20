"""Configuração lida de variáveis de ambiente (ou de um ficheiro .env local)."""

import os
from dataclasses import dataclass
from pathlib import Path

URLS = {
    "producao": "https://sifp.minfin.gov.ao/sigt/fe/v1",
    "homologacao": "https://sifphml.minfin.gov.ao/sigt/fe/v1",
}


def carregar_env(caminho=".env"):
    """Carrega um .env simples (CHAVE=valor) sem sobrepor variáveis já definidas."""
    ficheiro = Path(caminho)
    if not ficheiro.is_file():
        return
    for linha in ficheiro.read_text(encoding="utf-8").splitlines():
        linha = linha.strip()
        if not linha or linha.startswith("#") or "=" not in linha:
            continue
        chave, valor = linha.split("=", 1)
        os.environ.setdefault(chave.strip(), valor.strip().strip('"').strip("'"))


@dataclass
class Config:
    nif: str
    utilizador: str
    senha: str
    chave_privada_pem: str
    product_id: str
    product_version: str
    software_validation_number: str
    jws_software_signature: str
    base_url: str

    @classmethod
    def do_ambiente(cls):
        em_falta = [
            nome
            for nome in (
                "AGT_NIF",
                "AGT_UTILIZADOR",
                "AGT_SENHA",
                "AGT_CHAVE_PRIVADA",
                "AGT_PRODUCT_ID",
                "AGT_PRODUCT_VERSION",
                "AGT_SOFTWARE_VALIDATION_NUMBER",
            )
            if not os.environ.get(nome)
        ]
        if em_falta:
            raise SystemExit("Variáveis em falta no .env: " + ", ".join(em_falta))

        ambiente = os.environ.get("AGT_AMBIENTE", "producao").lower()
        if ambiente not in URLS:
            raise SystemExit("AGT_AMBIENTE deve ser 'producao' ou 'homologacao'")

        caminho_chave = Path(os.environ["AGT_CHAVE_PRIVADA"])
        if not caminho_chave.is_file():
            raise SystemExit(f"Chave privada não encontrada: {caminho_chave}")

        return cls(
            nif=os.environ["AGT_NIF"],
            utilizador=os.environ["AGT_UTILIZADOR"],
            senha=os.environ["AGT_SENHA"],
            chave_privada_pem=caminho_chave.read_text(encoding="utf-8"),
            product_id=os.environ["AGT_PRODUCT_ID"],
            product_version=os.environ["AGT_PRODUCT_VERSION"],
            software_validation_number=os.environ["AGT_SOFTWARE_VALIDATION_NUMBER"],
            jws_software_signature=os.environ.get("AGT_JWS_SOFTWARE_SIGNATURE", ""),
            base_url=os.environ.get("AGT_BASE_URL", URLS[ambiente]).rstrip("/"),
        )
