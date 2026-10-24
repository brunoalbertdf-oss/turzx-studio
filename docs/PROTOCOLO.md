# Protocolo da tela TURZX 5" (Rev C): o que o REA revelou

Fonte: `UsbMonitorL.exe` (TURZX, SHA-256 `d396126b…0608f`), analisado com
`rea inspect-managed-members` (REA 6.7.0), mais um desmontador de CIL e um decifrador
das strings do Dotfuscator, escritos para esta análise. Os tokens `0x06xxxxxx` identificam
os métodos nesse executável (os nomes estão ofuscados).

## Enquadramento (confirmado)

O método `0x0600005f` monta todo comando num buffer de **250 bytes**:

| Byte | Conteúdo |
|---|---|
| 0 | código do comando |
| 1–2 | `EF 69` |
| 3–6 | "tamanho" (32 bits, big-endian; o significado depende do comando) |
| 7 | flag |
| 10… | dados |

Dados longos (`0x06000060`) vão em blocos de **249 bytes + 1 byte `00`** (250 por escrita).
As respostas são texto ASCII lido da serial (`0x06000057`).

## Comandos encontrados

| Cód. | Método | Uso (pelas strings decifradas e pelo código) |
|---|---|---|
| `0x01` | — | HELLO / identificação (`chs_5inch.dev1_rom1.87`) |
| `0x64` | `⼏.⯃` | **espaço** ✅ resposta `flashTotal-flashUsado-flashLivre-sdTotal-sdUsado-sdLivre` em KB (esta tela: `10880-…`, ~10,6 MB, sem SD) |
| `0x65` | `0x060000f9` | **lista pasta** ✅ dados = caminho; resposta `result:dir:<subpastas>/file:<a.mp4>/<b.mp4>/` ou `result:nodir-createfailed` |
| `0x66` | `0x060000dc` | **apaga arquivo** ✅ dados = caminho completo (botão da página de arquivos do TURZX); sem resposta |
| `0x6E` | `0x060000ff` | **tamanho do arquivo** ✅ dados = caminho; resposta = bytes, `"0"` se não existir |
| `0x6F` | `0x06000111` | **abre arquivo para gravação** (ver abaixo) |
| `0x78` | `0x0600011a` | **toca vídeo** ✅ dados = caminho; resposta `play_video_success` |
| `0x79` | `0x060000d9` | parar vídeo |
| `0x7A` | `㐁.⯃` | (assíncrono, sem dados) |
| `0x7B` | `0x060000d8` | brilho (1 byte); log `brightness:` |
| `0x7D` | `0x060000da` | opções (5 bytes do AppConfig: modo de início, flip, sleep…) |
| `0x7F` | `㪙.⯃` | (assíncrono, sem dados) |
| `0x82`–`0x87` | `⿢.*` | controle (`0x83` desligar, `0x84` reiniciar, `0x86` pré-imagem); `0x82` é chamado antes de tocar vídeo |
| `0x8C` | `0x0600011d` | **mostra imagem do armazenamento**: dados = caminho; resposta `play_img_ok` |
| `0x96` | `0x06000117` | para mídia ✅ resposta `media_stop` |
| `0xC8`/`0xC9`/`0xCA`/`0xCC` | `⿢.*` | imagem inteira / parcial (já usados pelo TURZX Studio) |
| `0xCE` | `㌮.⯃` | armazenamento: `SdTotal` / `SdUsed` / `SdValid` |
| `0xCF` | `㉛.⯃` | status; `QuerryResend:` / `needReSend:1` |
| `0xD0` | `0x060000d1` | (dados binários) |

## Vídeo tocado pela própria tela (como o TURZX faz)

1. **Conversão** (strings em `0x06000093`):
   `ffmpeg … setsar=1:1 -c:v libx264 -b:v 2400k -bufsize 2400k -r 24 -an -pix_fmt yuv420p -f mp4`.
   Para telas giradas são gerados `_90.mp4`, `_180.mp4` e `_270.mp4`.
2. **Pastas na tela** (`RootPath..ctor`): `/root/video/` (interna), `/mnt/UDISK/video/`,
   `/mnt/SDCARD/video/` e `/mnt/SDCARD/img/`.
3. **Upload** (`0x06000111`):
   - para a mídia (`0x96`) e verifica o espaço;
   - lista a pasta (`0x65`);
   - envia `0x6F` com tamanho = comprimento do caminho e dados = `caminho ASCII + tamanho do arquivo (4 bytes little-endian)`;
   - envia o arquivo em leituras de **254 976 bytes** (`249×1024`; 1 019 904 em outro modo de firmware), cada uma escrita em blocos de 249+1;
   - termina quando a tela responde `file_rev_done`;
   - limite de 4 GB (`Max4gb`); sem espaço: `Noroom`.
4. **Tocar** (`0x0600011a`): confere o arquivo (`0x6E`), chama `0x82`, espera 2 s e envia `0x78` com o caminho. Sucesso = `play_video_success`.

## Confirmado na tela (24/10/2026)
- Upload: `0x96` → `0x65` (pasta) → `0x6F` (caminho + tamanho LE) → `create_success` → dados **contínuos**
  em blocos de 249+1 → `file_rev_done`. Tamanho conferido com `0x6E` (idêntico ao arquivo).
- **Não pausar** durante a transferência: com pausas de alguns segundos entre blocos, a tela abandona a gravação.
- A tela **não sobrescreve**: arquivo existente → `create_failed`. Apague antes com `0x66`.
- Memória cheia: `create_failed`, ou o arquivo fica truncado mesmo com `file_rev_done`. Consulte `0x64` antes.
- Nunca envie dados depois de um `create_failed`: a tela para de ler e a porta trava até reconectar o USB.
- Vídeo 800×480 H.264 24 fps tocou corretamente; para tela montada invertida, gire 180° na conversão.
- Cuidado no Git Bash: argumentos começando com `/` viram caminhos do Windows (`MSYS_NO_PATHCONV=1`).

- Para interromper um vídeo tocado pela tela é preciso `0x79` (parar vídeo); o `0x96` sozinho não basta.

## Ainda não confirmado
- os argumentos exatos de `0x82` e a flag do `0x78`;
- o que `Version.mode == 3` muda (outro modelo/firmware).

**Não usar:** `/update.app` é o caminho de atualização de firmware (`0x060000ee`).
