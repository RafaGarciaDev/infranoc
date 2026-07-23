# ADR-005: Painel de VPN com dados simulados (sem WireGuard real no lab)

## Status
Aceito

## Contexto
A Fase 9i pede um painel de VPN mostrando usuarios remotos, sessoes ativas,
ultimo handshake e volume de trafego (rx/tx). A ferramenta de referencia
para VPN moderna e leve e o WireGuard.

## Decisao
Nao rodamos uma instancia real de WireGuard no laboratorio. Os motivos:
1. **Exigiria exposicao de rede real**: WireGuard real depende de um
   endpoint publico acessivel e de pares (peers) conectando de fora do
   laboratorio - algo fora do escopo de um ambiente de lab fechado, sem
   trafego real de usuarios remotos.
2. **O objetivo da sub-fase e o painel e a logica de negocio**: gerenciar
   usuarios (criar, editar, revogar, expirar), acompanhar sessoes e
   detectar handshakes antigos ("stale") - nao operar o tunel de fato.
3. **Mesma filosofia dos ADR-003 (Backup) e ADR-004 (SIEM)**: simular a
   fonte de dados, manter real a modelagem e a logica de consulta.

Optamos por:
- Modelar `VpnUser` como entidade de primeira classe no banco, com campos
  que espelham a configuracao real de um peer WireGuard (`public_key`,
  `internal_ip`, `active`, `expires_at`), mais vinculo opcional a uma
  conta do Active Directory (`ad_sam`).
- Modelar `VpnSession` separadamente, com campos que espelham a saida
  real do comando `wg show` (`endpoint_publico`, `connected_at`,
  `last_handshake`, `bytes_rx`, `bytes_tx`).
- Popular via seed (`app/seed_vpn.py`) com usuarios e sessoes ficticios.
- Calcular o status "stale" (handshake antigo) a partir da diferenca real
  entre `last_handshake` e o instante da consulta - a logica de deteccao
  e genuina, so a origem dos dados e fabricada. WireGuard real considera
  um peer provavelmente desconectado quando o handshake ultrapassa ~3
  minutos sem renovacao; a mesma janela foi usada aqui.
- Endpoint `POST /vpn/users/{id}/simulate-handshake` permite "reativar" a
  aparencia de uma sessao sem handshake recente, criando ou atualizando
  uma `VpnSession` com timestamp atual - substitui, no lab, o que seria a
  renovacao natural do handshake por um peer real conectado.

## Consequencias
- O painel reflete uma arquitetura de dados e uma logica de deteccao
  (stale/ativo) prontas para uso real, mas as sessoes e o trafego
  individuais sao fabricados, nao coletados de um tunel WireGuard real.
- Isso deve ficar claro em qualquer demonstracao do projeto, para nao
  passar a impressao de que ha usuarios remotos de fato conectados.
- Ao migrar para o servidor dedicado (Fase 9a), avaliar a instalacao de
  um WireGuard real (com `wg-easy` ou configuracao manual) para
  substituir o seed por dados coletados via `wg show` (parseando a saida
  ou usando um exporter como `prometheus-wireguard-exporter`), mantendo
  os mesmos endpoints e o mesmo formato de dados (`VpnUser`/`VpnSession`)
  para minimizar mudancas no frontend.
- O endpoint de simulacao de handshake (`simulate-handshake`) e exclusivo
  do modo simulado e deve ser removido (ou protegido atras de uma flag de
  ambiente) quando o WireGuard real for integrado, para nao permitir
  "falsificar" a presenca de um peer em producao.
