# Runbook: Failover de Link de Rede

## Sintoma
Alerta de perda do link principal (WAN-01, operadora A) no site PSA.
Latencia alta ou perda de pacotes acima de 10% tambem se aplicam.

## Impacto
Sem failover, o site PSA perde acesso a sistemas corporativos,
VoIP e monitoramento remoto. O link secundario (WAN-02, operadora B)
tem banda reduzida (50% da principal).

## Diagnostico
1. Confirmar estado das interfaces no roteador de borda RTR-PSA-01.
2. Verificar se o failover automatico (SLA tracking) ja atuou:
   rota padrao deve apontar para WAN-02.
3. Testar conectividade externa a partir do roteador (ping 8.8.8.8).
4. Checar ONU/modem da operadora A: LEDs de sinal e alarme.
5. Consultar painel da operadora A por incidentes na regiao.

## Acao
1. Se failover automatico atuou: validar navegacao e VoIP no site.
   Priorizar
@'
# Runbook: Failover de Link de Rede

## Sintoma
Alerta de perda do link principal (WAN-01, operadora A) no site PSA.
Latencia alta ou perda de pacotes acima de 10% tambem se aplicam.

## Impacto
Sem failover, o site PSA perde acesso a sistemas corporativos,
VoIP e monitoramento remoto. O link secundario (WAN-02, operadora B)
tem banda reduzida (50% da principal).

## Diagnostico
1. Confirmar estado das interfaces no roteador de borda RTR-PSA-01.
2. Verificar se o failover automatico (SLA tracking) ja atuou:
   rota padrao deve apontar para WAN-02.
3. Testar conectividade externa a partir do roteador (ping 8.8.8.8).
4. Checar ONU/modem da operadora A: LEDs de sinal e alarme.
5. Consultar painel da operadora A por incidentes na regiao.

## Acao
1. Se failover automatico atuou: validar navegacao e VoIP no site.
   Priorizar trafego critico (QoS ja aplica automaticamente).
2. Se failover NAO atuou: executar failover manual no RTR-PSA-01
   conforme procedimento P-NET-012 (alterar metrica da rota padrao).
3. Abrir chamado com a operadora A informando numero do circuito.
4. Registrar incidente no InfraNOC vinculado ao ativo RTR-PSA-01.
5. Apos retorno do link principal: aguardar 15 min de estabilidade
   antes de retornar o trafego (evitar flapping).

## Escalonamento
- 0-15 min: operador NOC
- 15-45 min: analista de redes
- +45 min ou falha dupla (WAN-01 e WAN-02): coordenador de TI + operadoras
