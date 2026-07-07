# Imagem enxuta do Python 3.12 para os simuladores InfraNOC
FROM python:3.12-slim

WORKDIR /app

# Copia os simuladores para o container
COPY *.py /app/

# Sem dependencias externas - stdlib pura
# Porta padrao vem por CMD (asset=9200, oee=9201) - sobrescrever no compose

# Executa como usuario nao-root (boa pratica)
RUN useradd -r -u 1000 simulator && chown -R simulator /app
USER simulator

# CMD default (sobrescrito no compose por servico)
CMD ["python", "asset_simulator.py"]