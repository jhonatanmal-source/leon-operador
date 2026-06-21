CENTRAL DE ATALHOS LEON
=======================

USO_DIARIO
- Abrir painel web.
- Iniciar operador com autonomia de 24 ou 8 horas.
- Conceder autonomia adicional de 2 horas.

ACESSO_REMOTO
- Ativar No-IP (recomendado).
- Ativar DuckDNS (alternativa preservada).
- Iniciar painel web e Cloudflare Quick Tunnel.
- Iniciar somente web ou somente tunnel.

MANUTENCAO
- Operador sem concessao automatica de autonomia.
- Painel local legado.
- Ferramentas antigas preservadas apenas para diagnostico.

IMPORTANTE SOBRE DDNS
- No-IP e DuckDNS apontam um nome para o IP publico do roteador.
- Eles nao mascaram um Quick Tunnel trycloudflare.com.
- Para URL publica fixa com HTTPS sem abrir portas, use um Cloudflare Named
  Tunnel associado a um dominio proprio.
- No plano gratuito, o No-IP exige confirmacao periodica do hostname.
- Se a operadora liberar somente portas altas, o HTTPS publico direto nao
  consegue renovar certificado pelas validacoes padrao 80/443.
- Nesse caso, use Cloudflare Tunnel ou Tailscale Funnel e nao exponha portas.

Entrada recomendada:
C:\XAU_ELITE_AI\LEON.bat
