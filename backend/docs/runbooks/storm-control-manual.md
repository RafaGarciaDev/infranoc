# Runbook: Storm Control Manual (Tempestade de Broadcast)

## Sintoma
Pico anormal de trafego broadcast/multicast em switch de acesso.
Sintomas associados: lentidao generalizada na rede do setor, CPU
alta no switch, LEDs de portas piscando em ritmo continuo.

## Impacto
Uma tempestade de broadcast pode saturar a rede do site PSA em
minutos, derrubando comunicacao de sensores, cameras e telefonia IP
do segmento afetado. Loops de camada 2 sao a causa mais comum.

## Diagnostico
1. Identificar o switch afetado nos alertas do InfraNOC.
2. Verificar contadores de broadcast por porta no switch para
   localizar a porta de origem do trafego anomalo.
3. Checar se ha loop fisico: cabo conectando duas portas do mesmo
   switch ou de switches vizinhos (comum apos manutencao no setor).
4. Verificar estado do spanning-tree: porta que deveria estar em
   blocking operando em forwarding.
5. Descartar equipamento defeituoso (placa de rede em broadcast).

## Acao
1. Se porta de origem identificada: desabilitar a porta (shutdown)
   imediatamente para conter a tempestade.
2. Se loop fisico confirmado: remover o cabo em loop e reabilitar
   a porta apos 5 min de observacao.
3. Aplicar storm control na porta afetada conforme padrao P-NET-021
   (limite de broadcast em 1% da banda) antes de reativar.
4. Se spanning-tree inconsistente: revisar prioridades e portas edge
   com o analista de redes antes de qualquer mudanca.
5. Registrar incidente no InfraNOC vinculado ao switch afetado.

## Escalonamento
- 0-15 min: operador NOC (contencao da porta)
- 15-40 min: analista de redes (causa raiz e storm control)
- +40 min ou multiplos switches afetados: coordenador de TI
