# Runbook: Camara Fria Acima do Limite de Temperatura

## Sintoma
Alerta de sensor de temperatura da camara fria acima do limite
configurado (padrao: -18C, alerta a partir de -15C, critico a -10C).

## Impacto
Risco de perda de produtos refrigerados. Prazo critico: 4 horas
acima de -10C compromete a carga.

## Diagnostico
1. Confirmar leitura no painel do sensor local (descartar falso positivo).
2. Verificar se ha mais de um sensor da mesma camara em alerta.
3. Checar alimentacao eletrica do compressor (disjuntor QDF-07).
4. Verificar UPS da sala de maquinas no InfraNOC (tipo UPS, site PSA).
5. Inspecionar porta da camara: sensor de porta aberta ativo?

## Acao
1. Se porta aberta: fechar e monitorar por 30 min ate normalizar.
2. Se compressor desligado: rearmar disjuntor QDF-07 uma unica vez.
   Se desarmar novamente, NAO rearmar e acionar manutencao eletrica.
3. Se falha do compressor: acionar refrigeracao (plantao 24h) e
   iniciar transferencia de carga para camara reserva CF-02.
4. Registrar incidente
@'
# Runbook: Camara Fria Acima do Limite de Temperatura

## Sintoma
Alerta de sensor de temperatura da camara fria acima do limite
configurado (padrao: -18C, alerta a partir de -15C, critico a -10C).

## Impacto
Risco de perda de produtos refrigerados. Prazo critico: 4 horas
acima de -10C compromete a carga.

## Diagnostico
1. Confirmar leitura no painel do sensor local (descartar falso positivo).
2. Verificar se ha mais de um sensor da mesma camara em alerta.
3. Checar alimentacao eletrica do compressor (disjuntor QDF-07).
4. Verificar UPS da sala de maquinas no InfraNOC (tipo UPS, site PSA).
5. Inspecionar porta da camara: sensor de porta aberta ativo?

## Acao
1. Se porta aberta: fechar e monitorar por 30 min ate normalizar.
2. Se compressor desligado: rearmar disjuntor QDF-07 uma unica vez.
   Se desarmar novamente, NAO rearmar e acionar manutencao eletrica.
3. Se falha do compressor: acionar refrigeracao (plantao 24h) e
   iniciar transferencia de carga para camara reserva CF-02.
4. Registrar incidente no InfraNOC com criticidade High.

## Escalonamento
- 0-30 min: operador NOC
- 30-60 min: supervisor de facilities
- +60 min ou temperatura acima de -10C: gerente de operacoes
