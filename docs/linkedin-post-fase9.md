# Rascunho — post LinkedIn (Fase 9: gestão real de rede e servidores + modernização visual)

---

🖥️ Mais uma rodada de evolução no **InfraNOC**, meu projeto pessoal de NOC/SOC/IAM com IA local.

Até agora o InfraNOC simulava boa parte da infraestrutura de uma fábrica fictícia (CMDB, alertas, backup, SIEM...). Nessa fase eu quis ir além da simulação e fazer o sistema conversar de verdade com equipamentos e servidores:

🔌 **Console de Dispositivos com SNMP real** — GET e SET de verdade em equipamentos de rede, com trava dupla de segurança pra comandos de escrita (permissão + confirmação explícita).

🪟 **Windows Server Ops** — operações reais via WinRM num Windows Server de laboratório: serviços, processos, disco, sessões RDP. Sem simulação, comando de verdade chegando na máquina.

🌐 **Hub de Redes** — consolidei três telas separadas (mapa de rede, dispositivos, hub de acessos) numa visão única, evitando duplicar o mesmo dado em lugares diferentes.

🎨 E fechei com uma rodada de modernização visual: tokens de design (espaçamento/raio/sombra), cabeçalho de página consistente em todas as telas, e ajustes de legibilidade em tabelas e badges de severidade.

Nessa fase também bati de frente com problemas bem "do mundo real" que não aparecem em tutorial: permissão WMI negada por conta de serviço sem privilégio de Administrador no domínio, VM presa numa rede virtual que nem aparecia no editor de redes do VMware, e volume de container corrompido por um crash do Docker Desktop. Depurar essas coisas (e não só "fazer o feature funcionar") é a parte que mais ensina.

O projeto continua 100% open source.

🔗 Repositório: github.com/RafaGarciaDev/infranoc

#DevOps #NOC #InfraNOC #SNMP #WinRM #FastAPI #NextJS #PortfolioDeProjetos

---

## Imagens recomendadas pra esse post (nessa ordem)

1. **Dashboard** (`/dashboard`) — mostra o cabeçalho de página novo e o rodapé de usuário na sidebar. Boa "capa" do post.
2. **Dispositivos** (`/dispositivos`) — abrir o console de um dispositivo e mostrar um comando SNMP marcado como "Real" (não "Simulado"), se possível junto com a confirmação de SET.
3. **Windows Server Ops** (`/windows-ops`) — a aba de Serviços ou Processos com dados reais da VM (nomes de serviço, status "Running"/"Stopped" legível, não número cru).
4. **Hub de Redes** (`/mapa-rede`) — visão geral consolidada (mapa + lista de dispositivos).
5. (opcional) **Segurança/SIEM** (`/security`) — pra mostrar os badges de severidade corrigidos (crítico/alto/atenção/info bem diferenciados por cor).

Print em tema escuro fica mais "NOC" e combina com o resto do README — mas se quiser mostrar os dois temas (claro/escuro) num carrossel, também funciona bem pro LinkedIn.
