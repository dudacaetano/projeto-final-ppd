# Chat Distribuído com Middleware Orientado a Mensagens
<h1 align="center">
   <br>Chat Distribuído com Middleware Orientado a Mensagens (MOM) e RPC
</h1>


## 📚 Resumo
> Este projeto implementa um sistema distribuído para troca de mensagens baseado em Middleware Orientado a Mensagens (MOM) e RPC (Remote Procedure Call). O sistema permite que usuários enviem mensagens uns aos outros com base na proximidade, utilizando um broker MQTT para facilitar a comunicação assíncrona entre os clientes .

## Clone Repositório:
```bash
git clone https://github.com/dudacaetano/projeto-final-ppd.git
cd projeto-final-ppd
```

## Config ambiente virtual
```bash
python -m venv .venv
source .venv/bin/activate
```

## Instalando Dependencias

```bash
pip install -r requirements.txt
```

## Executando servidor

```bash
python servidor.py
```

##  Clientes

Para ter um chat é necessário inicializar dois clientes.


## Executando cliente:

```bash
python cliente.py
```
