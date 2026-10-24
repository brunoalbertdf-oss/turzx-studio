# Registro de mudanças

## 1.1.0 (24/10/2026)
- **Skins completas**: além das cores, cada skin traz fontes e fundo decorado e muda o visual de
  todas as telas sem mexer no layout. Os 8 visuais temáticos (Saiyajin, Super Saiyajin Blue,
  Esferas do Dragão, Ninja da Folha, Tático, Operações, Liberty, Festival) agora são skins.
- Galeria de skins com prévia da sua própria tela e botão "Usar esta skin".
- Telas prontas ("Painel completo" e "Relógio e tempo") na aba Telas.
- **MSI Afterburner como fonte de sensores**: temperatura, potência e clock da CPU e todos os
  dados da GPU (NVIDIA, AMD ou Intel).
- **FPS em todos os jogos, inclusive o CS2**, com o PresentMon (Intel, MIT) em modo administrador,
  ativado uma vez pelo Agendador de Tarefas, como no app original. O RivaTuner fica de reserva.
- Aviso no primeiro uso, faixa no editor e painel "Fontes de dados" quando o Afterburner ou o
  RivaTuner não são encontrados.
- **Correção do congelamento da tela**: a marca de fim das atualizações parciais passa a entrar na divisão
  em blocos de 249 bytes, como no app da TURZX. Antes, cerca de 1 em cada 249 atualizações chegava corrompida
  e a tela travava pedindo reenvio. Como rede de segurança, se a tela pedir reenvio, o app a reinicia e reconecta sozinho.
- Correção: respostas JSON declaram UTF-8 (acentos corretos em qualquer cliente).

## 1.0.0 (24/10/2026)
Primeira versão.
- Driver próprio da tela TURZX 5" (protocolo descoberto com o REA), com envio só das áreas alteradas.
- Editor visual no navegador: widgets, skins, desfazer/refazer, prévia ao vivo.
- Carrossel com transição suave (fade de brilho).
- CPU/GPU com nome e selo do fabricante; FPS (RivaTuner); HDs/SSDs; RAM; rede; tempo e previsão.
- GIFs e vídeos nos painéis; vídeo fluido em tela cheia tocado pela própria tela, com gerenciador
  da memória da tela.
- 8 temas: Saiyajin, Super Saiyajin Blue, Esferas do Dragão, Ninja da Folha, Tático, Operações,
  Liberty e Festival.
- Ícone na bandeja, iniciar com o Windows, executável e pacote zip.
