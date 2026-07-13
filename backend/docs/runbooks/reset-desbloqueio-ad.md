# Runbook: Reset de Senha e Desbloqueio de Conta AD

## Sintoma
Usuario relata senha expirada, esquecida ou conta bloqueada apos
tentativas invalidas. Alertas de lockout repetido tambem se aplicam.

## Impacto
Usuario sem acesso a estacao, e-mail e sistemas integrados ao AD.
Lockouts repetidos da mesma conta podem indicar credencial vazada
ou servico com senha antiga configurada.

## Diagnostico
1. Validar identidade do solicitante (matricula + gestor ou
   videochamada). NUNCA resetar senha por solicitacao anonima.
2. Verificar estado da conta no AD: bloqueada, expirada ou desativada.
3. Se lockout repetido: identificar origem das tentativas invalidas
   nos eventos 4740/4625 do controlador de dominio DC-01.
4. Conferir se a origem e um servico/tarefa agendada com senha antiga.

## Acao
1. Reset simples: gerar senha temporaria forte, marcar troca no
   proximo logon e informar ao usuario por canal seguro.
2. Desbloqueio: desbloquear a conta somente apos validar identidade.
3. Lockout por servico: corrigir a credencial no servico de origem
   e desbloquear em seguida.
4. Suspeita de comprometimento: NAO desbloquear; isolar a estacao de
   origem, resetar a senha e acionar o time de seguranca.
5. Registrar atendimento no InfraNOC com o ativo DC-01 vinculado.

## Escalonamento
- Rotina: service desk
- Lockout repetido sem origem identificada: analista de infraestrutura
- Suspeita de comprometimento: time de seguranca (imediato)
