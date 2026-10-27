# Registro de mudanças

## 1.1.2 (27/10/2026)
- **A tela apaga ao desligar, reiniciar, fazer logoff ou suspender o PC**, e também ao sair do app.
  Muitas placas-mãe mantêm a USB alimentada com o PC desligado, e a tela ficava acesa com o último quadro.
  Ao voltar da suspensão, ela reacende e redesenha sozinha.
- **Inicialização bem mais rápida**: a tela acende uns 5 s depois da área de trabalho (antes, ~20 s).
  Sem o atraso de 10 s no login (a tarefa existente é atualizada sozinha), conexão com a tela antes do resto
  da abertura, consulta de hardware em segundo plano e busca da pasta do TURZX guardada.
- A tela só acende depois do primeiro desenho, sem mostrar a imagem antiga ou preta.
- Vídeos já convertidos continuam funcionando sem o ffmpeg (ele só é exigido para vídeos novos).

## 1.1.1 (24/10/2026)
- Acorda telas que aparecem "dormindo" no Windows (identificação `USB7INCH` / `1A86:CA21`), como o app original faz.
- Diagnóstico de conexão: quando a tela não é encontrada, o editor mostra as portas vistas com a identificação
  USB; quando a porta está ocupada, avisa que o app TURZX original ainda está rodando.
- README: seção "Problemas comuns".

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
- **Correção do travamento após redesenhar a tela inteira** (salvar no editor, trocar skin, enviar logo):
  a tela reinicia a numeração das atualizações parciais após cada imagem inteira; o app agora acompanha.
- **Logos oficiais pelo editor** (Ajustes → Logos dos fabricantes): versões para fundo escuro e claro,
  escolhidas pela skin; sem a versão clara, o texto preto é clareado automaticamente. O nome do modelo
  ao lado acompanha a altura do logo.
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
