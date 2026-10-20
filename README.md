# AGT - Validador Documentos Comunicados vs Emitidos em ERP Primavera

Primeira peça: `agt_consulta`, uma ferramenta de linha de comandos que consulta,
através da API oficial de Facturação Electrónica da AGT, os documentos que foram
comunicados e o detalhe de cada um. Mais tarde estes dados serão comparados com
os documentos emitidos no Primavera.

Documentação da AGT: <https://quiosqueagt.minfin.gov.ao/doc-agt/faturacao-electronica/1/>

## Instalação

```bash
python -m venv .venv
source .venv/bin/activate      # Windows: .venv\Scripts\activate
pip install -r requirements.txt
```

## Credenciais

Copie `.env.example` para `.env` e preencha. São necessários:

- o NIF do emissor;
- o utilizador e a senha de acesso aos serviços emitidos pela AGT;
- o caminho para a chave RSA privada do emissor (cada pedido é assinado em RS256);
- os dados do software certificado (`softwareInfo`), os mesmos que o Primavera usa.

O `.env` e os ficheiros `.pem`/`.key` estão no `.gitignore` e nunca devem ir para o Git.

## Utilização

```bash
# documentos comunicados num período + detalhe de cada um
python -m agt_consulta listar --de 2026-09-01 --ate 2026-09-30

# só a lista, sem consultar o detalhe
python -m agt_consulta listar --de 2026-09-01 --ate 2026-09-30 --sem-detalhe

# detalhe de um documento
python -m agt_consulta detalhe "FT A/123"
```

Os resultados ficam em `saida/`: um JSON com as respostas completas e dois CSV
(`_lista.csv` e `_detalhe.csv`, separados por `;`) que abrem directamente no Excel.
Para testar contra o ambiente de homologação use `AGT_AMBIENTE=homologacao`.

## Por confirmar

- Os nomes dos campos de `listarFacturas` (`queryStartDate`/`queryEndDate`) e a
  estrutura das respostas ainda não foram validados contra a AGT. Estão
  concentrados em `agt_consulta/cliente.py` para serem fáceis de ajustar.
- Os servidores da AGT podem só aceitar ligações a partir de Angola.

## Testes

```bash
pip install pytest
python -m pytest tests
```
