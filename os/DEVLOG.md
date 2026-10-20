# DruidOS Development Log

## 2026-10-20 - Ajustes, leitura: a app, e o runtime Quantum dentro do sistema

A fatia 5b. A app que o Daniel pediu ("uma tela de admin com nome do pc,
rede, teclado, tudo em tela") lendo a máquina de verdade, e o que faltava
para ela rodar.

**O que faltava.** Nem a VM do laboratório nem a ISO tinham o runtime
Python do Quantum: o `quantum pixel` só tinha sido provado por um cliente
de socket cru. Agora o runtime vai com a Hive: as dependências (flask,
yaml, sqlparse, requests, bcrypt) como pacotes Ubuntu do base da VM
(`PACKAGES`, `BASE_VERSION` 7) e da imagem da ISO; o pacote `quantum/` do
repositório copiado para `/usr/lib/python3/dist-packages` (o `stage()` do
laboratório o põe ao lado dos binários e um hash por arquivo decide o que
reinstalar); `/usr/bin/quantum` e `/usr/bin/hive` (`hive ajustes` abre a
app na tela como o usuário que chamou; `hive apps` lista;
`/usr/share/quantum-os/apps`). O Textual fica de fora (o do Ubuntu é
velho demais): na máquina a app roda na tela e no navegador, não no
console. A ISO segue sem validação aqui.

**A app (`apps/ajustes`).** Cinco abas de um `ui:tabpanel`: Máquina (nome,
sistema, kernel, tempo ligada, núcleos, memória, disco), Rede (cada
interface com endereço, estado e origem DHCP/fixo; gateway; DNS), Teclado
(o layout do sistema e o que a tela lê), Tela (nível, escolha, núcleos,
custo do quadro, movimento) e Hive (os daemons e seu estado, o que a
whitelist permite). Cada aba é um serviço de `leitura.py`, stdlib só, que
lê o que qualquer um lê (`/proc`, `/etc/default/keyboard`,
`/etc/hive/whitelist.toml`, `ip -j addr`, `ip -j route`, `resolvectl`,
`systemctl is-active`) por duas portas, `run` e `read`, que o teste troca
por uma máquina enlatada; nada levanta erro: sem `ip` ou sem tela lê-se
"não lido". As "últimas ofertas" da aba Hive ficaram de fora: o journal
não é do usuário comum.

**O status da tela.** A proposta dizia `{"op":"status"}` pedido pela
página; o socket aceita um cliente só e o serviço corre noutra thread do
mesmo processo, então o daemon empurra: `{"event":"status",...}` ao
conectar e a cada mudança (nível, pregado ou não, núcleos, movimento,
teclado, custo do quadro, cena), `Runtime::status`; o cliente espera meio
segundo por ele antes da primeira página e o guarda em `screen_status()`.

**O que a VM mostrou.** A primeira rodada falhou: o servidor da app abria
`logs/quantum.log` dentro de `/usr/share`, que não é do usuário. A app
instalada não grava log em arquivo (`logging: file: false`) e o runtime
passa a avisar e seguir só no console quando o diretório de log não é
gravável. A fita `ajustes.jsonl` então passou (121 s): `hive ajustes` como
druid, "page: Ajustes" no journal, a view que o servidor da app responde
com `nome: quantum-lab`, `núcleos: 4`, `nível:` e `hive-screen: active`,
setas pelas abas no teclado real, Esc.

**Prova fora da VM.** `tests/apps/test_ajustes.py`: os serviços contra a
máquina enlatada, e a página no navegador, no console e na tela (os
drivers do teste de paridade), onde a aba Tela diz `nível: effects (1)`.

**A seguir.** A mudança pela Hive (5c): a página pede, o cortex oferece,
Enter na tela aprova, o atuador executa pela whitelist.

## 2026-10-20 - O menu F1 e o botão da janela na barra

O quarto passo da fatia 5: as ofertas da Hive chegam por cima de qualquer
coisa que esteja na tela, e a barra de baixo começa a ser barra de
tarefas.

**O menu.** F1 abre uma gaveta no canto inferior esquerdo, no visual das
janelas (`window::draw_menu`: moldura com sombra, barra de título mel
"Ofertas da Hive", uma linha por oferta com a de foco em relevo e mel,
barra de estado "Enter aprova · Del dispensa · Esc fecha"); vazia, diz
"nada por agora". Enquanto está fora, as teclas são dela: setas, Enter
aprova (duas vezes a perigosa), Del dispensa, Esc fecha e a página volta
a ouvir o teclado. `approve()` e `dismiss()` saíram do `key()` para servir
ao painel da cena e ao menu. Sem página, F1 abre o mesmo menu sobre a
colmeia.

**A gaveta.** Desliza da esquerda em 8 ticks (`Quad`/`Out`) e empurra a
colmeia 4 px para a direita enquanto está fora (as barras ficam); fecha
pelo mesmo caminho. No `plain` abre e fecha de uma vez. A observação diz
`menu` (`open`, `t`, `ticks`), `until still` espera a gaveta parar e
`until menu` espera o menu aberto ou fechado.

**A barra.** A barra de estado da janela mostra "F1 · N ofertas" em mel à
direita quando há ofertas esperando, e a ajuda é cortada num separador
(`cut_at_separator`), nunca no meio de uma palavra. A barra de baixo da
cena mostra a página aberta como um botão em relevo à esquerda, como uma
barra de tarefas; o `screen.q` diz `{offers} offers · F1` à direita.

**Prova.** `tests/play.rs` ganha o teste do menu sobre a página (ofertas
chegam com a página aberta, F1 a meio caminho, aprovação da perigosa com
dois Enter, Del, Esc devolvendo o teclado à página, o menu vazio sobre a
colmeia, o `plain` de uma vez) e quatro quadros: `window-offers.png`,
`menu-drawer.png`, `menu.png`, `menu-empty.png`; os outros quadros foram
refeitos pelo texto novo da barra.

**O que fica.** Várias janelas na barra (Alt+1..9, F2) esperam mais de um
cliente no socket; as apps instaladas no menu esperam o app Ajustes (5b),
que é quem registra uma app; a abelha que traz a oferta e o zoom na célula
são os próximos movimentos.

## 2026-10-20 - A colmeia ganha barras, painéis e células com relevo

O terceiro passo da fatia 5: a cena em volta da janela passa a ter o
mesmo visual que ela. O esboço `cena.png` da proposta virou quadro de
referência.

**Na linguagem (`qs:`).** Uma tag nova, `qs:bar side="top|bottom"`, com
`title=` (na cor de destaque), `left=` e `right=`; os textos aceitam os
campos da própria tela, `{clock}`, `{level}`, `{cores}`, `{host}` e
`{offers}`, e recusam os campos de evento (esses vão num `qs:say`). O
`qs:offers` e o `qs:notices` ganham `title=`: com título viram painéis com
moldura em relevo, sombra de 3 px e barra de título, da altura das suas
linhas. Uma barra por lado; o esquema, o modelo, o compilador, a
referência (`docs/targets/screen.md`, com a seção "The look of the scene"
e a tabela dos campos) e o dataset da feature acompanham.

**No daemon.** `world.rs` desenha as barras (14 px em cima, 12 embaixo) e
os painéis com a paleta e o `bevel_out` de `window.rs`; o que a Hive diz
(`qs:say`) passa a aparecer à esquerda da barra de baixo enquanto dura, e
só sobre uma página continua na faixa própria, para ser lido por cima
dela. Os fatos das barras (`World::set_facts`: nome da máquina lido de
`/proc/sys/kernel/hostname`, núcleos do chooser, hora local) são dados
pelo `main.rs` duas vezes por segundo; a tela de um teste não os tem, por
isso mostra `--:--` e `1 cores` e os quadros são iguais em qualquer
máquina. A observação diz `bars` com os campos preenchidos.

**Na arte.** `hive_screen.py` redesenha as células: corpo arredondado de
cera com relevo (borda clara em cima e à esquerda), sombra de 2 px dentro
do quadro de 24×24, miolo que mostra o estado (mel, vazio, rachado,
fumaça, apagado); as cores que as fitas da VM procuram (`#f0aa28` do mel,
`#1c140c` da rachadura) ficam as mesmas. O `screen.q` reorganiza a
colmeia: barra em cima, duas colunas de células com passo de 28 px, a
abelha entre elas e o painel de ofertas, painel de avisos de 308 px
embaixo, barra embaixo com `{offers} offers`.

**Prova.** Os dez quadros de referência de `tests/play.rs` foram
redesenhados; o teste do crash e da oferta lê as barras na observação
(`1 cores · effects · --:--`, `2 offers`, e `fine` depois de subir o
nível); as fitas `screen-crash` e `screen-page` do Hive lab passam. Os
textos da cena seguem em inglês como o resto do `screen.q` (a ajuda da
janela é em português): uma passada de idioma na tela inteira fica para
quando o app Ajustes tiver a opção.

**A seguir na fatia.** A barra de baixo como barra de tarefas (as janelas
abertas) e o menu F1 com as ofertas e as apps; depois a gaveta, a abelha
que traz a oferta, o zoom na célula.

## 2026-10-20 - Movimento em pixel art: gelatina, lâmpada, cortina

O segundo passo da fatia 5: as três transições que o Daniel viu animadas
nos esboços, agora no daemon, em ticks, sem alfa suave onde a pixel art
pede pontilhado.

**Como se compõe.** A janela passa a ser desenhada uma vez por quadro
num canvas só dela, transparente em volta (`World::page_image`), e
composta sobre a cena escurecida: inteira quando parada, deformada numa
transição. Isso custa um buffer do tamanho do canvas por quadro só
enquanto há página; a apresentação parcial continua levando ao display
só as linhas que mudaram.

**As três.** Gelatina ao abrir: a imagem da janela e da sombra escalada ao
redor do centro de 60% a 100% com a curva `Back` (um sobressalto), a cena
escurecendo junto; 12 ticks. Lâmpada ao fechar: a janela sai da lista na
hora (o teclado volta à cena), mas a última imagem dela verga e é sugada
para o canto inferior esquerdo, cada coluna convergindo no alvo, o lado
longe dobrando primeiro; 14 ticks. Cortina ao mostrar a página de novo
depois de uma ação: a página nova é desenhada inteira e a antiga fica
onde uma máscara ordenada 4×4 ainda não chegou; 8 ticks.

**Regras.** Nada se move no nível `plain` (um núcleo não tem quadro
sobrando); `HIVE_SCREEN_MOTION=off` no ambiente da unit desliga. O play
protocol ganhou `until still` e a observação diz `motion` (tipo, tick,
duração); `tests/play.rs` guarda um quadro de cada transição no meio do
caminho (`window-jelly.png`, `window-lamp.png`, `window-curtain.png`) e
prova que no `plain` a página aparece de uma vez.

**O que fica para os próximos passos.** A dobra (trocar de janela) espera
mais de uma janela; a gaveta espera o menu F1; a abelha que traz a oferta
e o zoom na célula esperam a colmeia nova; faísca, treme e o traço do
foco vêm com os widgets.

## 2026-10-20 - A página vira janela: moldura, relevo, sombra

O primeiro passo da fatia 5 (visual e movimento), depois dos esboços em
pixel art aprovados: a página na tela deixa de parecer um terminal e vira
uma janela como as de um gerenciador de janelas mínimo.

**O que mudou no desenho (`window.rs`).** A cena escurece sob a janela e
aparece em volta dela; a janela tem moldura de 1 px com bisel (claro em
cima e à esquerda, escuro embaixo e à direita no que é saliente; o
contrário no que é rebaixado), sombra de 3 px a 50%, barra de título mel
em dois tons com o título em tinta e a tecla `Esc` desenhada como tecla à
direita, e barra de estado em relevo com as teclas que valem. Os widgets
ganharam volume: campo rebaixado (contorno mel com o foco), botão
saliente (foco em contorno e texto mel; primário com texto mel; perigoso
em vermelho), caixa de marcar de 8 px com visto, interruptor com trilho e
botão, radio com quadrado mel, select saliente com seta de três linhas,
aba ativa como bloco saliente sobre uma régua, tabela com régua sob o
cabeçalho e zebra, emblemas e alertas em relevo, régua em duas linhas,
barra de rolagem rebaixada com polegar saliente. Tudo dentro da linha de
10 px de cada célula, para nada se sobrepor.

**A janela do tamanho do conteúdo.** A largura é a do canvas menos as
margens (8 px na cena, 16 no nível fino); a altura é a que o conteúdo
pede mais as barras, até o limite do canvas, e a janela fica centrada:
uma página curta é uma janela pequena sobre a colmeia, uma longa toma a
tela e rola. Em células: 49 colunas e até 13 linhas em 320×180; 100 por
até 29 no nível fino. A observação do play protocol diz `frame` em pixels.

**O que ficou igual.** A árvore de visão, o modelo de teclado, os eventos:
a página continua a mesma para todo renderizador; só a tela desenha
diferente. Os quadros de referência foram refeitos; o teste de paridade,
a fita do laboratório da Hive e os unitários passam sem mudança de
lógica.

**A seguir na fatia.** A barra inferior com as janelas e o menu F1, a
colmeia com barras e painéis, e as transições (gelatina, lâmpada, dobra,
cortina).

## 2026-10-20 - Páginas na tela, 4b: nível fino a 106×36, ABNT2 com acentos, rolagem

A fatia 4b, por cima da 4a integrada ontem.

**Nível fino.** No nível fino o canvas tem dois pixels para cada um da
cena (640×360), e até aqui a página era desenhada com a fonte em blocos
2×2, nas mesmas 53×18 células. Agora a página é desenhada pixel a pixel no
canvas (`Band::unscaled`): 106×36 células, a fonte nítida, quatro vezes o
conteúdo. É o `sm` do console (80 colunas): um `hbox` com `stack_below`
deixa de empilhar. Quando o nível muda com uma página aberta, ela reflui
nas células novas e o foco fica onde estava (`Window::resize`).

**O que a proposta prometia e o que entrou.** A proposta falava numa fonte
maior, 8×12, 80×30 células. A fonte da tela é uma face 5×7 desenhada à
mão, glifo a glifo, em `font.py`; uma face 7×9 seriam 95 glifos novos,
mais o compilador e o esquema para levá-la ao daemon, e não provaria nada
do mecanismo. No display de 1280×800 da VM, a letra no nível fino fica com
12×20 pixels, maior que a fonte de um console de texto; se na prática
ficar pequena, a face maior é a próxima fatia de legibilidade, não esta.

**ABNT2.** O daemon lê `XKBLAYOUT` em `/etc/default/keyboard` ao subir
(ou `HIVE_SCREEN_KEYBOARD=br` no ambiente da unit) e, no layout `br`, dá
`ç` na tecla dela, `/` e `?` na tecla ao lado do Shift direito, `;` e `:`
onde o US tem `/`, e os acentos como teclas mortas (`´` e `` ` `` à
direita do P, `~` e `^` à direita do Ç, `¨` em Shift+6) compostas com a
vogal seguinte, como o Latin-1 as tem (`ã`, `é`, `ô`, `ü`, `Ã`...); morta
e espaço dá o acento, morta e letra que não leva acento dá os dois, Enter
esquece a que estava esperando. AltGr dá `/ ? ° ² ³ ª º`. Caps Lock só
vira as letras. Tudo em `input.rs`, com testes de unidade; a fita
`screen-abnt2.jsonl` do VM lab põe `br` no sistema, reinicia o daemon e
digita `ação` no teclado real (a, a tecla do ç, a tecla do ~ e o a, o,
Enter): o programa do usuário recebe `"titulo":"ação"`.

**Rolagem e teclas verticais.** Cima e Baixo vão ao elemento anterior e
seguinte quando o que tem o foco não as usa (campo de uma linha, botão,
caixa, barra de abas; um radio, um select, uma tabela e uma área de texto
ficam com elas); Home e End vão ao primeiro e ao último (num campo, às
pontas do texto). Revelar o foco deixa uma linha de contexto, e uma barra
de dois pixels na borda direita diz onde a tela está numa página longa.

**Fora desta fatia.** Stream e history continuam como texto; a face 7×9.

## 2026-10-19 - Páginas na tela: `quantum pixel`, a fatia 4a

A tela da Hive agora também mostra as aplicações da máquina. `quantum
pixel`, rodado por qualquer usuário local na pasta de um projeto, é o
quarto renderizador de uma página Quantum, ao lado do navegador, do
console e do desktop: o mesmo runtime (o servidor da aplicação, aberto no
próprio processo como o `quantum console` faz), só o desenho muda.

**Como funciona.** O `quantum pixel` conecta no socket do daemon
(`/run/hive-screen/pixel.sock`, modo 0666 num `RuntimeDirectory` da unit),
manda cada página como a árvore de visão em JSON (`show`, inteira, a cada
mudança) e recebe o que o usuário fez, uma linha por evento: `click`,
`submit` (com os campos do formulário como um navegador postaria),
`change` (campo de busca, depois da pausa), `navigate`, `reload` e
`close`. O daemon (`window.rs`) deita a página em células da fonte (53 por
17 em 320×180), desenha por cima da cena e fica dono do teclado enquanto
ela mostra. O teclado agora é lido inteiro de `/dev/input` (layout US,
Shift, Caps Lock, repetição); ABNT2 e teclas mortas ficam para a 4b.

**Sem mouse.** Quatro regras, e nenhuma tecla além das do console: Tab e
Shift+Tab entre os elementos que reagem, na ordem da página (o focado em
mel); setas dentro de um (cursor no campo, opção do radio/select, linha e
botão da tabela, aba); Enter aciona (num campo, envia o formulário);
Espaço marca; Esc fecha a página e a cena volta inteira, o `quantum
pixel` termina. A última linha diz as teclas que valem para o que tem o
foco. Uma página mostrada de novo depois de uma ação mantém o foco no
mesmo elemento, reconhecido pelo que ele é (tipo e `bind`/texto), não pelo
número, que muda quando um flash ou um erro entra na árvore.

**Como se prova.** O teste de paridade UI-7 roda o mesmo roteiro (vê,
preenche, marca, escolhe, clica) num terceiro driver, o da tela: o
`hive-screen` em modo play com `--pixel-socket`, as teclas pelo protocolo
e o `quantum pixel` como runtime da página numa thread; o workflow do OS
roda esse teste contra o binário recém-construído. `tests/play.rs` guarda
um quadro de referência de uma página (`window.png`); o laboratório da
Hive lê uma página como dados (`screen-page.jsonl`, com `contains` na op
`screen` para afirmar um campo de um evento); o laboratório da VM leva uma
página de um programa de usuário comum até a tela de verdade, digita nela
pelo teclado real e vê o formulário voltar com o que foi digitado
(`screen-pixel.jsonl`; `press` aceita agora todas as teclas e `type`).

**O que ficou de fora.** Fonte maior no nível fino e reflow por nível,
ABNT2 e teclas mortas, rolagem mais polida (4b); F1 com as ofertas da
Hive por cima da app, um app de ajustes do OS, várias janelas, ofertas
que abrem páginas (4c).

## 2026-10-19 - A tela apresenta só o que mudou, e divide o console

Duas consolidações da tela, depois das três fatias.

**Só as linhas que mudaram.** Uma cena em repouso não é parada: a abelha
bate asas dez vezes por segundo, e cada batida custava um quadro inteiro,
1280×720 pixels (4 MB) escritos no buffer de scanout e transferidos pela
`virtio-gpu`. Agora o display guarda o último quadro apresentado e compara
linha a linha (`changed_rows`): só a faixa entre a primeira e a última
linha diferente é ampliada, escrita e marcada suja. A abelha custa 16
linhas de 180. Um quadro igual ao anterior não toca o buffer. O nível fino
com neve continua custando o quadro inteiro, como deve: lá tudo muda.
Medido no VM lab sob emulação, onde nada é rápido: o quadro da abelha no
nível 1 custava 75 a 100 ms e passou a 20 ms (a linha que o daemon diz no
journal, `ms a frame over the first 20 frames`). Ainda é o limite do
orçamento a 30 fps sob TCG, então a fita dos níveis segue exigindo KVM;
numa máquina de verdade a diferença é a mesma proporção sobre custos dez
vezes menores.

**O console é dividido.** Até aqui o `hive-screen` segurava o `tty1` e não
tratava Ctrl+Alt+F2: o console serial e o SSH eram o caminho para o grove.
Agora o terminal fica em modo `VT_PROCESS`: o kernel manda um sinal antes
de trocar, o daemon solta o DRM (`DROP_MASTER`, para o console de texto
poder desenhar na mesma placa), responde `VT_RELDISP` e fica esperando sem
desenhar e sem aceitar teclas; no sinal de volta, retoma o master (quem foi
master pode voltar a ser sem privilégio), põe o modo de novo e desenha o
quadro inteiro. A fita `screen-vt.jsonl` faz `chvt 2` no guest, espera o
mel sumir do `screendump`, `chvt 1`, e espera o mel voltar. `until_shot`
ganhou `lacks`, esperar uma cor sumir.

## 2026-10-19 - A tela cresce com os núcleos: níveis de apresentação

A terceira fatia da tela, o requisito experimental: a interface escala com
os núcleos que a VM dá. Não é "fazer uma GPU", é flexibilidade. O quanto o
`hive-screen` mostra é um **nível de apresentação** (`level.rs`), escolhido
enquanto roda pelo tempo de quadro que mede, nunca acima do teto que os
núcleos permitem:

| nível | precisa | mostra |
|---|---|---|
| 0 `plain` | 1 núcleo | a cena como declarada, sem partículas, no máximo 15 quadros por segundo |
| 1 `effects` | 2 núcleos | as partículas (`qs:emit` e os `qs:emitter` de `level="1"`), no máximo 30 |
| 2 `fine` | 4 núcleos | dois pixels para cada um da cena: um tween ou uma partícula cai no seu próprio pixel, a fonte vira blocos; e os `qs:emitter` de `level="2"`, a neve que a cena do OS guarda para esse nível |

Um nível muda como a cena aparece, nunca o que acontece nela: os mesmos
ticks rodam em qualquer nível, as regras fazem o mesmo. Quem escolhe é o
`Chooser`: a média móvel do custo de um quadro (desenhar mais apresentar)
abaixo de 15% do período do nível, por pelo menos 20 quadros e 2 segundos,
sobe um nível, se os núcleos deixam; acima de 60% desce, e o nível que se
provou caro só é tentado de novo meio minuto depois. Os núcleos vêm de
`available_parallelism` duas vezes por segundo (a afinidade do processo e a
cota do cgroup): uma vCPU que entra por hotplug conta em meio segundo, uma
que sai derruba o nível na hora. Uma cena parada continua não custando
nada em nenhum nível: só se mede quadro desenhado.

O quadro é desenhado por faixas de linhas, uma thread por núcleo (até oito,
`std::thread::scope`): cada faixa desenha a mesma lista de nós recortada
às suas linhas, então a imagem é a mesma com uma faixa ou quarenta, e o
teste prova isso pixel a pixel em ×1 e em ×2. A ampliação para o dumb
buffer do DRM também vai por faixas. No nível fino o canvas tem `scale`
pixels por pixel da cena, e as primitivas recebem coordenadas da cena:
`fill_rect_f` para as partículas (posição e tamanho fracionários), `blit`
e `text` multiplicam. Em ×1 a conta é exatamente a de antes: a cena de
`main` desenhada pelo daemon novo bate com as referências antigas pixel a
pixel (as referências `crash` e `offer` mudaram só porque a cena ganhou um
emissor e as sementes das rajadas andaram uma casa).

Na linguagem, uma coisa: `qs:emitter level="1|2"`, o nível mais baixo em
que o emissor toca (1 por padrão; 3 é recusado com a linha). A cena do OS
ganha `<qs:emitter particles="snow" level="2">`. O play protocol ganha
`{"op":"level","level":N}` e `frame` aceita `bands` (o teste desenha o
quadro fino inteiro e em 3 e em 8 faixas contra a mesma referência).

No VM lab a máquina passa a 4 vCPUs (`BASE_VERSION` 6) e o op `cpus`
deixa 1 a 4 delas online no guest (`/sys/devices/system/cpu/cpuN/online`),
esperando o `nproc` concordar: para um programa, uma vCPU offline é o que
uma desligada seria, e um `restore` traz de volta as do snapshot sem
cerimônia. O hotplug do QEMU foi a primeira tentativa (`-smp 2,maxcpus=4`,
`device_add` dos slots de `query-hotpluggable-cpus`): o `device_add` passa,
mas o kernel deste guest sobe com `smpboot: Allowing 2 CPUs, 0 hotplug
CPUs` e nunca vê a nova. `shot` ganha `lacks`, a cor que não pode estar na
tela. A fita `screen-levels.jsonl` segue o nível com os núcleos: 2 online
e `cores: 2, level up to 1`, a tela sem neve; 4 online e `cores: 4, level
up to 2`, depois `level 2 (fine)`, a cena a ×2 no display e a cor da neve
no `screendump`; 2 de novo, nível 1 e a cena a ×4 outra vez. Essa fita
diz `// needs: kvm` e o lab a pula onde `/dev/kvm` não serve (o CI tem):
sob emulação só apresentar o buffer de 1280×800 custa 80 ms por quadro, o
orçamento é do emulador e não da máquina, e a tela fica honestamente em
`plain` com qualquer número de núcleos (o teto, `cores: 4, level up to 2`,
aparece do mesmo jeito). Para quem sabe mais que a medida, ou para tirar
uma captura, `HIVE_SCREEN_LEVEL=N` no ambiente da unit prega o nível.

De quebra, três coisas. O buffer de scanout era mapeado (`mmap`) a cada
quadro, e um mapeamento novo custa uma page fault por página: sob emulação
eram 128 ms por quadro, que derrubavam a tela para `plain` com dois
núcleos; agora é mapeado uma vez, pela vida do display (`drm-ffi` dá o
offset, `libc::mmap` o resto). O laço do daemon consumia o `dirty` antes
de olhar o relógio, então uma mudança única dentro dos 33 ms depois de um
quadro se perdia até a próxima (as animações mascaravam); agora o relógio
vem primeiro. E um `done.actual.png` que tinha ido parar no repositório
saiu, com `*.actual.png` no `.gitignore`. O daemon diz no journal, uma vez
por visita a um nível, quanto custa um quadro ali. E a fita do console
espera a rachadura da célula (`#1c140c`, cor de nenhum outro quadro, que
fica até o mel voltar) em vez da fumaça, que dura 1,5 s e as consultas ao
journal sob emulação às vezes perdiam.

Limite desta fatia: não há nível acima do fino; mais núcleos que quatro
só dão mais faixas. Um nível `smooth` a 60 quadros por segundo caberia na
mesma tabela quando houver o que mostrar com ele.

## 2026-10-19 - A tela da Hive no console de verdade (DRM, teclado, unit)

A segunda fatia da tela: o `hive-screen` desenha no console da VM. Sem X,
sem Wayland, sem driver de GPU do nosso lado: abre `/dev/dri/card0`, toma
o primeiro conector ligado no modo preferido, cria um dumb buffer e
escreve a cena nele, ampliada por um número inteiro e centrada (1280×720
é ×4 de 320×180; 1024×768 é ×3 com bordas pretas). Desenha só quando o
quadro mudou, no máximo 30 vezes por segundo: uma cena parada não custa
nada. O teclado vem direto de `/dev/input` (os `event*` que têm Enter), e
o terminal `tty1`, que o systemd dá ao daemon como entrada padrão, vai para
modo gráfico (`KDSETMODE`) enquanto ele roda, e volta a texto na saída,
inclusive por SIGTERM.

`hive-screen.service` roda como `_hive-screen`, usuário próprio nos grupos
`video` e `input`, com o mesmo hardening dos outros daemons, `DevicePolicy`
fechada a não ser a placa, os eventos de entrada e o `tty1`, e `Nice=5` e
`CPUWeight=50` para ceder a vez à synapse. O cortex aceita `hive-screen`
como dashboard quando vem desse uid (ou de um administrador, como antes).
Instalado pelo VM lab, pela ISO e pelo pacote, com `/etc/hive/screen/`.

O VM lab ganhou uma placa `virtio-gpu` (a base é refeita: `BASE_VERSION`
4), o op `shot`, que lê o display pelo `screendump` do QMP e conta as cores
(um decodificador de PNG de trinta linhas, só biblioteca padrão), o
`until_shot`, e o `press`, que aperta teclas na máquina pelo `send-key`. A
fita `screen-console.jsonl` segue um crash real: o título em mel no
display, a fumaça cinza sobre a célula do nginx, a oferta chegando ao daemon
(no journal), Enter no teclado da máquina, o actuator reiniciando de verdade
e o mel de volta na célula. Dados e cores, não OCR.

De quebra, um bug do transporte do agente do VM lab: um timeout curto deixado
no socket por uma espera anterior cortava o pedido seguinte, o que só
aparecia sem KVM, quando o primeiro boot demora. Agora cada pedido põe o seu.

## 2026-10-19 - A tela da Hive: pixel art no console, declarada em Quantum (qs:)

A interface gráfica do OS, decidida depois de pesar o Godot na VM (Mesa
llvmpipe, um compositor, ~300 MB e um motor C++ como cliente que aprova
ações) contra um runtime próprio: ficou o runtime próprio, sem overhead
nenhum. O que o console mostra é um `q:application type="screen"`,
`config/screen/screen.q`, com tags `qs:`:

- `qs:sheet` e `qs:animation` são as folhas de quadros e seus ciclos;
  `qs:particles` um efeito (os mesmos presets dos jogos); `qs:scene` o
  que está na tela: `qs:sprite`, `qs:text`, `qs:emitter`, e dois widgets
  embutidos, `qs:offers` (as ofertas da Hive, que o administrador aprova
  com o teclado; uma ação perigosa pede Enter duas vezes) e `qs:notices`.
- `qs:on event="..."` diz o que acontece na cena quando um evento chega:
  `qs:animate`, `qs:frame`, `qs:show`, `qs:tween` (as mesmas curvas dos
  jogos), `qs:emit`, `qs:say`. Os eventos são os das regras `qh:`, com os
  mesmos `{campos}`, mais `notice`, `offer`, `done` e `failed`. O nome de
  um sprite é como uma regra o alcança: `{service}` em `service-crash`
  acha o sprite chamado `nginx`, e ele solta fumaça.
- Nada de statements nem expressões. O compilador (`quantum/runtime/screen`)
  recusa com a linha o que o arquivo não pode cumprir: folha que não
  existe, quadro que ela não tem, campo que o evento não tem, alvo que
  nenhum sprite se chama.
- A fonte é nossa: 5×7 pixels em células de 6×10, ASCII e Latin-1 com os
  acentos compostos das letras base, escrita como `font.png` ao lado da
  cena. A arte (favos de uma colmeia, uma célula por serviço, uma abelha)
  é de `scripts/art/hive_screen.py`, CC0.

O daemon é `crates/hive-screen`: carrega `screen.toml` e as folhas (PNG),
toca a cena a 60 ticks por segundo num canvas, e é cliente do socket de
usuário do cortex como o dashboard (o cortex o aceita como um). Para a tela
reagir ao que aconteceu e não às palavras, `Notification` passou a levar
`kind` e `fields`: a tabela de eventos que vivia na synapse foi para
`hive-common` (`events.rs`), e o cortex preenche os campos em cada aviso.
A resposta do actuator vira `done` ou `failed`, com o nome da ação e o
serviço ou pacote.

Determinismo: seno, cosseno e 2^x são aritmética pura no daemon, e as
partículas usam uma semente fixa, então um quadro é igual pixel a pixel em
qualquer máquina. O teste do daemon (`tests/play.rs`) toca a tela do OS
pelo play protocol (stdin, como o driver dos jogos) e compara quatro
quadros com referências; o Hive lab roda o `hive-screen` de verdade sem
tela (`{"op":"screen"}`) e lê o que ele mostra como dados: a fita
`screen-crash.jsonl` segue o nginx caindo, a fumaça na célula, a oferta,
o Enter, o actuator e o mel de volta na célula.

Ficou para as próximas fatias: desenhar no console de verdade (DRM/KMS,
teclado por evdev, unit do systemd com usuário `_hive-screen`), a VM do lab
com `virtio-gpu` e `screendump`, e os níveis de apresentação pelo orçamento
de quadro, para a cena ganhar resolução e efeitos com os núcleos que a VM
der.

## 2026-10-19 - As regras da Hive declaradas em Quantum (qh:)

O que une os dois projetos de verdade. O que a Hive oferece quando algo
acontece (reiniciar o serviço que caiu, mostrar os logs, instalar o pacote
que o usuário pediu) vivia em código Rust na synapse (`actions.rs`), e o
whitelist do actuator num TOML à parte. Agora as duas coisas são um
arquivo Quantum, `config/hive/hive.q`, com tags `qh:`:

- `qh:on event="service-crash"` segura as ofertas de um evento;
  `qh:offer` é uma oferta com título, descrição, `action=` (o nome em
  kebab-case da variante de `Action` do actuator) e os atributos dessa
  ação. Qualquer um pode ter `{campo}`: um campo do evento, que a synapse
  preenche a partir do próprio evento, nunca do texto do modelo.
- `qh:allow`, `qh:block` e `qh:limit` são o whitelist: o que o actuator
  pode fazer, o que nunca pode, e quantas vezes por minuto.

**O compilador recusa o que o arquivo não pode cumprir:** um evento, uma
ação ou um atributo que não existem; um `{campo}` que o evento não tem, ou
texto onde vai número (`port="{holder}"`); uma oferta que o próprio
whitelist do arquivo recusaria (um comando sem `qh:allow command=`, um
serviço bloqueado, um `kill-port-process` sem a permissão); statements,
expressões ou script. Vinte e dois casos em `tests/hive/`.

**O que sai:** `config/hive/rules.toml` (novo; a synapse carrega de
`/etc/hive/rules.toml`, e o build embute o arquivo commitado como regra
padrão) e `config/hive/whitelist.toml` (o mesmo formato de antes, agora
gerado). `python scripts/generate-hive-config.py` escreve os dois; um
teste falha se forem editados à mão ou se o `hive.q` mudar sem regenerar.
O whitelist gerado é idêntico ao que existia (comparado como TOML). A
synapse ganhou `rules.rs`, que faz as mesmas checagens ao carregar e cai
para as regras embutidas se o arquivo for inválido; uma oferta cujo valor
não é o que a ação aceita em tempo de execução é deixada de fora, nunca
adivinhada.

**Ao redor:** a linguagem é laboratory, como os jogos; `docs/targets/hive.md`
é gerado do schema; o feature module `hive_rules` tem intenções e dataset
(5 positivos, 12 negativos), e um teste garante que cada tag, evento e ação
tem intenção e exemplo. A Hive lab ganhou a fita `log-anomaly`: a quinta
regra, que não tinha fita. O que ficou de fora: a janela de 5 minutos do
cortex (`report-interval`) continua constante no código; vira atributo
quando o cortex carregar o arquivo também.

## 2026-10-19 - VM Lab: o sistema real, restaurado em um segundo

A segunda camada do play protocol do OS. A Hive lab valida o que a Hive
decide, mas não o que só o sistema rodando mostra: o que os nerves reais
veem no journal, no audit e no `/proc`, e o que o actuator real faz via
polkit e systemd. O lab da ISO cobria isso com ISO, instalação, OCR e o
Forge, a minutos por volta.

**O que é (`scripts/lab/vm/`, documentado no README de lá e no
CLAUDE.md):** a imagem cloud mínima do Ubuntu 24.04 (a release que o OS
remasteriza) num overlay qcow2, no QEMU (KVM quando há, emulação quando
não). O cloud-init só instala um agente: `agent.py`, que fala JSON lines
numa porta virtio-serial, sem rede, sem SSH e sem chaves. A base bota uma
vez e vira o snapshot `base`, com polkit, PackageKit e auditd. Esses
pacotes o host baixa com o dpkg status do próprio guest, e o guest instala
offline por 9p. A Hive do working tree (binários sem debug, `config/`) é
instalada como a ISO instala (`install-hive.sh`) e vira o snapshot `hive`.
Cada fita restaura `hive`. O dashboard e o grove reais rodam num terminal
dentro do guest, e o novo `hive-lab term` lê as telas com o mesmo emulador
da Hive lab.

**Tempos, medidos aqui sem KVM:** a base sai em ~5 min (quase tudo é o
primeiro boot). Subir a VM a partir de `hive` leva ~7 s, e um restore
~2 s. As seis fitas levam ~115 s juntas. Só o que mudou é instalado: se
mudaram só binários, eles são copiados e só as units deles reiniciam
(grove 6 s, um nerve 9 s, o cortex 20 s, contra 60 s da instalação
completa). **No CI, com KVM:** a base sai em 18 a 25 s, e as seis fitas,
com a primeira instalação, em ~60 s (sem ela, de 2 a 7 s cada).

**Fitas:**
- `crash-restart`: uma unit real em loop de crash aparece uma vez no
  dashboard real, e só depois de aprovada no teclado o actuator real
  reinicia a unit via polkit.
- `port-conflict`: um processo real segura a porta, o nerve de rede real
  nomeia os dois uma vez, e o actuator roda `ss -tlnp` aprovado.
- `dangerous-command`: o `rm -rf /srv` de um usuário logado vai do audit
  do kernel ao dashboard real. Um delete de rotina e os comandos de daemons
  não são reportados (a regra do audit só registra quem tem loginuid, e o
  agente dá loginuid aos comandos do usuário, como um login daria).
- `crash-loop`: uma unit em loop de crash aparece, e a oferta de restart
  também, uma vez só.
- `anonymous-shell`: com o grove real em modo anônimo, um comando perigoso
  chega ao nerve de processo pelo audit, e o cortex, subindo a árvore real
  de processos até o shell, não repassa nada. Fora do modo anônimo, o
  mesmo comando volta a ser julgado.
- `install-on-request`: o usuário chama o htop no grove real, o dashboard
  oferece a instalação, e a aprovação faz o actuator sem privilégio
  instalar pelo PackageKit e polkit, a partir de um repositório assinado
  dentro do guest (a única fonte de pacotes dele, montada pelo host). Na
  segunda tentativa o grove roda o htop.

Uma fita que misturava o loop de crash com a aprovação falhou uma vez no
CI com KVM: o auto-restart do systemd e o restart aprovado disputavam a
mesma janela. Aprovar logo depois de corrigir a causa, com o serviço
voltando sozinho, é uma corrida legítima. Por isso o loop e o restart
viraram fitas separadas, e o restart parte de uma unit que caiu uma vez. As mesmas operações são ferramentas MCP (`vm_start`,
`vm_request`, `vm_view`, `vm_tape`, `vm_end`).

**O que o lab encontrou:**
- Uma unit em loop de crash inundava a Hive. Cada crash ia para o modelo e
  empilhava "Service Crashed" e as ofertas em todo dashboard (42
  reinícios, 42 avisos e mais um conflito de porta com ofertas para cada
  um). Agora o cortex passa um mesmo problema adiante uma vez a cada 5
  min, e o reporte seguinte diz quantos segurou, como já fazia com as
  ofertas de pacote. Há um teste no router e uma fita `crash-loop` na Hive
  lab.
- O nerve de rede já tinha uma janela de 5 min, mas a chave levava o pid,
  que muda a cada reinício, então nunca segurava nada. Agora a chave é a
  unit (ou o programa), com teste.
- Depois de um `rm -rf /srv`, o dashboard dizia "A ZFS snapshot has been
  created for safety", num sistema sem ZFS. O texto do mock da synapse
  afirmava algo que nada faz. A linha saiu, e um teste segura o mock a não
  afirmar nada.
- Uma ação de serviço que falhava chegava ao dashboard como "(failed)" e
  ao journal como um código de saída, porque o que o systemctl dizia era
  descartado. Agora isso vira a saída da ação.
- O pacote druidos-hive não dependia do que a Hive usa. Num sistema sem
  `packagekit-tools`, a instalação aprovada falhava com "Failed to run
  pkcon", e a ISO só funcionava porque trazia esse pacote por acaso. O
  `debian/control` agora depende de polkitd, packagekit,
  packagekit-tools e auditd.

## 2026-10-19 - Hive Lab: a Hive numa caixa, sem VM (início do Quantum OS)

Pedido do usuário: começar o Quantum OS a partir do DruidOS pelo que mais
travava o projeto, que era validar ideias. Cada volta pedia ISO, boot,
instalação, OCR e o Forge; numa sessão na nuvem (sem KVM, sem acesso ao
Forge) não dava para validar nada.

**O que é (`crates/hive-lab`, documentado no CLAUDE.md e no README do
crate):** o `hive-cortex` e o `hive-synapse` de verdade, e o resto
interpretado por um driver que fala uma requisição JSON por linha. Um
nerve injeta eventos tipados, o grove pergunta e o dashboard aprova. O
actuator registra o `ActionRequest` sem executar nada e responde "recorded,
not executed". Cada papel conecta com o nome de binário e o usuário que o
cortex confere (`_hive-sense`, `_hive-act`, root no dashboard), então as
regras de identidade são as do sistema. Os usuários do Hive existem só no
lab: cada daemon roda num mount namespace privado com `/etc/passwd` e
`/etc/group` do lab montados por cima, e o `/etc/passwd` da máquina não é
tocado. Por isso precisa de root (container, VM descartável, CI com sudo).

**Tempos:** a sessão sobe em ~0,2 s. As 6 fitas de `crates/hive-lab/tapes/`
rodam juntas em ~4 s: crash → reiniciar só com aprovação; programa não
encontrado → instalar só com aprovação; conflito de porta; disco cheio;
pergunta respondida como texto e nunca como ação; e as fronteiras do
socket de usuário (o grove não envia ação nem aprova sugestão). Uma
sessão feita à mão vira fita com `--record`. `scripts/lab/hive-tapes.sh`
roda todas, e o CI ganhou esse passo.

**O que o lab já encontrou:** sem o modelo, o synapse respondia
"Check package info with `apt show PACKAGE`" com `PACKAGE` literal, e o
mesmo com `SERVICE`, `PORT` e `KEYWORD` (o texto do modo mock). Num
conflito de porta ele nem escolhia o texto de porta, porque a descrição do
evento diz "already held by" e não "conflict". Corrigido:
`fill_mock_names` preenche os nomes a partir do evento que o prompt
descreve, e a linha que ficaria sem nome é omitida. As fitas
`command-not-found` e `port-conflict` agora exigem `apt show htop` e
`lsof -i :80` sem nenhum placeholder (`excludes`), e falham com o código
antigo.

**Telas como texto (mesmo dia):** o lab roda o `hive-dashboard` e o
`grove` de verdade num pseudo-terminal, e lê a tela por um emulador de
terminal (crate `vt100`): `tui`, `view`, `keys`, `until_screen`. Nada de
screenshot nem OCR. Na primeira olhada ao dashboard real, dois defeitos:

1. Todo aviso sem sugestão aparecia em vermelho com "(CONFIRM? press
   Enter again)": `armed == r.suggestion.map(...)` dá verdadeiro quando os
   dois lados são `None`. Agora `is_armed()` exige os dois `Some`.
2. O cortex mandava avisos e sugestões só para o **primeiro** dashboard
   do HashMap. Com dois administradores, qual deles via dependia da ordem
   do HashMap. Agora vão para todos. A primeira aprovação leva
   (`pending_suggestions.remove`), então nada roda duas vezes. Há um teste
   no router, que falhava antes.

Fitas novas: `dashboard-screen` (falha com o dashboard antigo, conferido)
e `grove-screen`. As 8 rodam em ~5 s.

**Próximas camadas:** a fronteira deste lab é o que o sistema real faz. O
que os nerves percebem num sistema rodando e o que uma ação faz pedem uma
VM leve (imagem cloud do Ubuntu, um agente via vsock com observações
estruturadas, telas do grove e do dashboard como texto via pty e um
emulador vt100, sem OCR, snapshots via QMP). Depois disso, um servidor MCP
com as mesmas ferramentas do play protocol do Quantum.

---

## 2026-09-10 - ISO Lab: build → boot → install → e2e sem humano, no Forge com KVM

Pedido do usuário: um ambiente onde o Claude consiga gerar as ISOs, bootar
em QEMU e testar de ponta a ponta sozinho. Antes disso, nem o boot da ISO
de 24/08 tinha sido confirmado de verdade (só "memória do QEMU crescendo").

**Infra:** o Forge (VM 400) não tinha `/dev/kvm` — CPU `x86-64-v2-AES`.
O host Proxmox já tinha `nested=1`; mudei a CPU da VM para `host` e
reiniciei via `qm reboot` (os 40 containers voltaram). Alternativas
descartadas: VMs direto no Proxmox (só ~2GB de RAM livre e o roteador
roda lá), TCG (~1h por instalação), QEMU local no Windows (o Colossus é
ele mesmo uma VM, WHPX não funciona).

**O lab (`scripts/lab/`, documentado no CLAUDE.md):** `lab.sh` (local,
sincroniza a working tree) → `remote.sh` (Forge, um container destacado
por etapa, sobrevive a queda de SSH) → `harness.py` (QEMU via QMP:
screendump + OCR com tesseract para as fases só-tela, log serial, SSH no
guest) → `e2e/guest-checks.sh` (roda dentro do DruidOS instalado, saída
TAP). Tempos reais com KVM: ISO ~1 min (base.iso em cache), boot até o
instalador ~20s em BIOS e UEFI, instalação automática ~3 min, e2e ~40s,
loop `dev` (build + hot-swap dos binários + e2e) ~1 min, pipeline `all`
completo 5min50s.

**O que o lab encontrou (tudo corrigido):**

1. **A ISO instalava Ubuntu puro.** O Subiquity instala o que está em
   `casper/install-sources.yaml`, que só listava as camadas originais do
   Ubuntu — o `filesystem.squashfs` com o Hive Stack nunca era usado. Agora
   `register_install_source()` registra `druidos` como única fonte.
2. `build-iso.sh`: o glob `hive-*` copiava os `.d` do cargo para
   `/usr/bin` e deixava o `grove` de fora; só habilitava o `hive-cortex`;
   copiava o `config/hive/config.toml` não versionado (com `user = "lab"`)
   e o caminho do `druidos-installer` estava errado. Agora lista explícita
   de binários (falta = erro), os 7 serviços habilitados, `default.toml`
   instalado como `/etc/hive/config.toml`.
3. **Nenhum serviço subia.** Todas as units são `Type=notify`, mas nenhum
   binário mandava `READY=1`: o `hive-cortex` ficava em "activating" até
   o timeout e os outros 6 caíam por dependência. Novo
   `hive_common::systemd` (protocolo sd_notify, sem dependências novas,
   com testes) chamado pelos 7 daemons quando ficam prontos. O e2e foi
   rodado primeiro contra o disco com o bug (15 falhas) e depois com a
   correção (24/24).
4. `hive-synapse.service` tinha comentário inline no valor
   (`MemoryDenyWriteExecute=no  # ...`) — systemd não suporta, a linha
   inteira era ignorada.
5. Console serial: GRUB da ISO e kernel agora também em `ttyS0` (herdado
   pelo sistema instalado), coerente com VM-first/terminal-only.

**Continuação (mesmo dia) — correções guiadas pelo lab.** Método: primeiro
a checagem e2e (vermelha contra o build anterior), depois a correção
(verde), depois `lab.sh all` do zero.

- `hive-nerve-fs` não observava nada: ignorava o config; o watch
  recursivo do `notify` aborta a árvore inteira no primeiro diretório
  ilegível (`/etc/credstore` para `_hive-sense`); e esperava
  `Modify(Data(Content))`, que o backend inotify nunca emite. Novo
  `tree::watch_tree` (um watch por diretório, pula só os ilegíveis,
  diretórios novos ganham watch), escritas detectadas por
  `IN_CLOSE_WRITE` e por rename (editores, `sed -i`).
- O cortex descartava todo `Notification` vindo de nerves (sem arm no
  router). Agora repassa ao dashboard, descartando `actions` e rejeitando
  remetentes que não são nerves.
- `hive-nerve-journal` relia as últimas 10 entradas a cada start
  (`--follow` sem `--lines=0`).
- Cores ANSI no journal: `hive_common::logging::init()` compartilhado, cor
  só quando stdout é terminal.
- Novas checagens e2e, incluindo o fluxo de aprovação no `hive-dashboard`
  dirigido por tmux (Enter numa sugestão → cortex recebe o `UserAction`).
  Uma checagem passava em falso (`grep $'\x1b['` sem `-F` sai com erro 2).

**Continuação — aprovar uma sugestão agora age de verdade.** Até aqui o
`hive-actuator` era inalcançável no produto: o synapse só gerava texto
(`action: None`), e mesmo com ação o actuator (usuário `_hive-act`, sem
root) não conseguia `systemctl restart` ("Interactive authentication
required" — confirmado no guest com o novo `lab.sh exec`).

- `hive-synapse/src/actions.rs`: regras fixas do evento tipado para ações
  tipadas (serviço crashou → `RestartService` + logs; anomalia → logs;
  disco → `df -h`; porta → `ss -tlnp`). Parâmetros vêm do evento, nunca do
  texto do modelo; nomes de unit validados.
- `config/polkit/60-druidos-hive-actuator.rules` (instalado pela ISO): teto
  no nível do SO sob a whitelist do actuator — só start/stop/restart/reload
  de `.service`, nunca hive-*/systemd-*/dbus/polkit/ssh/getty/user@.
- `hive-nerve-journal` atribuía toda falha de serviço a `init.scope`
  (mensagens do PID 1 têm a unit real no campo `UNIT`).
- e2e ponta a ponta numa instalação limpa: serviço whitelisted crasha →
  sugestão "Restart" → Enter no dashboard (tmux) → actuator reinicia via
  polkit; e o polkit recusa `_hive-act` fora do teto (recusa tem que ser de
  autorização, senão a checagem não prova nada). 40 checagens verdes.

**Continuação — `hive-nerve-network` refeito.** O antigo só gerava falso
conflito (dois sockets LISTEN numa porta = "conflito", o que é todo serviço
dual-stack; confirmado no guest) e nunca via um real (quem perde o bind não
ganha socket; PID fixo em 0). Agora o conflito é detectado pelo lado de quem
perdeu: `journalctl --grep` por "Address already in use"/EADDRINUSE, porta
extraída da mensagem (formatos de nginx, apache, redis, node, sshd, python;
sem porta = ignora, horário nunca vira porta), requisitante pelos campos
confiáveis do journal (`_PID`, `_COMM`, `_SYSTEMD_UNIT`), dono da porta via
`/proc/net` — por usuário, porque `_hive-sense` não consegue mapear socket
de outro usuário para PID (verificado no guest). Retentativas de
`Restart=always` são reportadas uma vez a cada 5 min. `watch_ports` vazio =
todas as portas (novo default); a unit ganhou leitura do journal e perdeu
`CAP_NET_ADMIN`. A notificação diz quem falhou e quem segura a porta. Três
checagens e2e (vermelhas antes, verdes depois); também corrigido um teste
instável do `nerve-journal` (processo de log que saía antes de o journald
resolver o cgroup). 43 checagens verdes numa instalação limpa.

**Continuação — `hive-nerve-process` não perde mais comandos rápidos.** O
polling de `/proc` a cada 250ms pegou 0 de 20 `rm -rf` seguidos numa
instalação real. Proc connector não resolveria (só entrega o PID; ler o
cmdline depois tem a mesma corrida). Agora o nerve lê o audit do kernel:
a ISO instala `auditd` com a regra `config/audit/60-druidos-hive-exec.rules`
(todo `execve` de sessão de login — `auid` definido: SSH, console, sudo;
não daemons/cron/scripts de pacote) e o nerve assina o grupo multicast de
audit via netlink com `CAP_AUDIT_READ` (só ler registros de audit, nada
mais). O argv vem do kernel no momento do exec. Tentativa de ler pelo
journal descartada: o Ubuntu desliga `systemd-journald-audit.socket` de
propósito. Novo módulo `audit.rs` (monta SYSCALL+EXECVE+CWD por serial até
o EOE; argumentos em hex e em chunks; testado com registros capturados do
guest); sem audit, fallback para polling com aviso. Agora pega 20 de 20. O
e2e também mostrou efeito de observador: o `grep` da própria checagem tem
`rm -rf /tmp/...` no argv e é (corretamente) reportado. Obs.: o
`/var/log/audit/audit.log` (só root) passa a guardar as linhas de comando
dos usuários. 45 checagens verdes (correção: os totais anteriores eram 40
e 43, não 42 e 45).

**Continuação — os dois achados que sobraram.**

- **Comando perigoso julgado pelo que roda, não por texto.** A regex sobre
  a linha inteira flagrava `grep "rm -rf /"` e `rm -rf /tmp/build`, e
  perdia `cd /etc && rm -rf nginx`. Novo `danger.rs`: programa real (`exe`
  do audit, não argv[0]), argumentos analisados (clusters, `--recursive`,
  `--`; para chmod/chown só `-R`), operandos normalizados pelo `cwd`, e uma
  definição explícita de perigoso (`/`, diretório de topo, ou filho direto
  de um diretório de sistema — /etc/nginx, /home/alice, /usr/lib). Os
  canários do e2e agora são `rm -rf` reais e inofensivos:
  `rm -rf /etc/<nome>/..` normaliza para /etc, mas o diretório não existe e
  o GNU rm recusa `..` (verificado no guest).
- **Prioridade real no journal.** `hive_common::logging::init()` manda para
  o journald nativo (`tracing-journald`) quando o stdout é o journal
  (`JOURNAL_STREAM` comparado com o próprio stdout): WARN/ERROR ficam com
  prioridade 4/3. Antes, o `nerve-journal` passa a ignorar logs emitidos
  por units `hive-*` (mensagens do PID 1 *sobre* elas continuam valendo),
  senão um aviso do Hive viraria anomalia reportada ao próprio Hive.

50 checagens verdes numa instalação limpa.

**Achados ainda em aberto:** nenhum dos levantados nesta sessão.

**Continuação — as três prioridades: grove, modelo real, ZFS.**

- **`grove` executa programas** (`79e8514`, e2e em `aab4dde`). Até aqui só
  tinha builtins. Novo parser (palavras com aspas e partes, listas com
  `;`/`&&`/`||`/`&`, pipelines, redirecionamentos `<` `>` `>>` `2>` `2>&1`),
  expansão (variáveis, `~`, glob), execução com pipes reais, builtins dentro
  de pipeline (numa thread), jobs em background, e sinais de shell
  interativo: Ctrl-C para o programa em primeiro plano e não o shell
  (verificado no guest via tmux). `grove -c` e scripts também. Comandos
  rodados pelo grove são vistos pelo `nerve-process` como qualquer outro.
- **`hive-synapse` roda um modelo local de verdade** (`0842ebf`, e2e em
  `c70cdc3`). Backend `candle` (escolha do usuário, Rust puro) com Qwen2.5
  0.5B Instruct Q4_K_M (GGUF, 491MB) e o tokenizer, fixados por sha256 e
  embutidos na ISO pelo `build-iso.sh` (cache em `~/druidos-lab/cache/models`
  no Forge). Prompt de chat curto (cada token de prompt custa tempo em CPU de
  VM), fila de pedidos com descarte do mais antigo (no máximo 3 pendentes) e
  as ações continuam vindo das regras tipadas, nunca do texto do modelo.
  Medido na VM (2 vCPU): carga ~1s, 11–17s por resposta, pico de ~1,56GB
  (`MemoryMax=2G`), sem OOM. As checagens que dependem de resposta esperam o
  synapse esvaziar a fila. 54 checagens verdes.
- **ZFS como raiz, snapshots de segurança de verdade.** Antes: o lab
  instalava ext4 (`layout: direct`); o actuator tentava
  `zfs snapshot rpool/ROOT/druidos@...`, um dataset que nenhum instalador
  cria, como `_hive-act` sem permissão, e seguia com a ação quando falhava
  (só um aviso); além disso "destrutivo" era todo `RunCommand` (inclusive
  `journalctl`) e não incluía instalar ou atualizar pacotes. O `hive-apt`
  só imprimia uma sugestão com o mesmo nome errado. Numa instalação ZFS real
  do lab: raiz em `rpool/ROOT/ubuntu_52tka7` com 15 datasets filhos
  (`var/lib/dpkg`, `var/lib/apt`, `var/log`...), `/boot` em outro pool
  (`bpool/BOOT/ubuntu_52tka7`), e `_hive-act` recebe "permission denied".
  - Lab: o autoinstall usa `layout: zfs` (`--storage`, `direct` continua
    disponível); os discos golden ganharam o sufixo `-zfs`; o hot-swap
    também instala `/etc/hive/{config,whitelist}.toml`.
  - `hive_common::zfs`: datasets do sistema (`/` e `/boot`) lidos do
    `/proc/self/mountinfo` (fixture de teste é o mountinfo real do guest),
    nome `hive-before-<mudança>-<hora UTC>`, `zfs snapshot -r` por dataset.
  - `hive-actuator`: snapshot antes de instalar/remover/atualizar pacotes
    (`Action::should_snapshot_first`, que perdeu `RestoreSnapshot`: o
    `rollback -r` destruiria o snapshot recém-criado), e **recusa a ação se o
    snapshot falhar**. `ExecStartPre=-+hive-actuator delegate-snapshots`
    aplica como root `zfs allow -u _hive-act snapshot,mount` nos datasets a
    cada start. `snapshot_dataset` passou a ser opcional (vazio = detectar).
  - `hive-apt install/remove/upgrade/autoremove` tira o snapshot de fato
    (depois da confirmação, antes do apt), e aborta se falhar
    (`--skip-hive` pula). `hive-zfs` também detecta o dataset.
  - O lab achou dois problemas no caminho: o ZFS recusa snapshot de dois
    pools numa chamada só ("multiple snapshots of same fs not allowed", até
    sem `-r`), então é uma chamada por dataset; e o automount de
    `.zfs/snapshot` dá ELOOP em dataset filho, então o e2e lê os snapshots
    montando-os read-only.
  - 7 checagens novas (vermelhas antes: 5 falhas): raiz é ZFS; o actuator
    acha os datasets; `_hive-act` consegue tirar snapshot e o ZFS recusa
    `destroy` e `rollback` para ele; `hive-apt install` de um `.deb` local
    cria o snapshot nos dois pools, e o snapshot (raiz + filho do dpkg) não
    tem nem o arquivo nem o registro do pacote, enquanto o sistema vivo tem;
    `hive-apt remove`, o inverso.
  - Pendente: limpeza/retenção dos snapshots `hive-*` (o `hive-zfs` tem a
    lógica mas não tem unit), ZFS como padrão no instalador interativo (só o
    autoinstall do lab escolhe), e o caminho do actuator só é coberto por
    testes de unidade (nenhuma sugestão atual oferece ação de pacote).

**Continuação — próximos passos: push, docs, ZFS na ISO de verdade, grove ↔ Hive.**

- Push dos 8 commits (CI e build da ISO verdes em `3f3f929`) e CLAUDE.md
  corrigido: base/kernel/bootloader reais (Ubuntu 24.04, kernel do Ubuntu,
  GRUB — o kernel enxuto e o systemd-boot continuam como objetivo), grove já
  roda programas, confirmação em dois toques no dashboard já existe.
- **O caminho de produção nunca tinha sido testado.** O `install` do lab
  pula o instalador (boot direto do kernel + autoinstall). Novo
  `lab.sh install-interactive`: boota a ISO como CD, escolhe a entrada do
  GRUB e percorre as telas do Subiquity com teclas via QMP, reconhecendo cada
  tela pelo texto do corpo (OCR) e com as teclas escolhidas pelas regras de
  foco lidas do código-fonte do Subiquity (extraído da própria ISO); depois
  boota o disco e julga o `root=` pelo console serial. O OCR ganhou uma
  segunda passada por limiar, porque a barra laranja e o botão verde em foco
  sumiam. Vermelho: a instalação padrão criava LVM/ext4
  (`root=/dev/mapper/ubuntu--vg-ubuntu--lv`) — sem snapshots de segurança
  para quem instalasse a ISO de verdade.
- **ZFS por padrão na ISO.** A tela de disco do Subiquity só oferece LVM ou
  partição simples e ignora o `layout` do autoinstall como padrão
  interativo (confirmado no código). A ISO agora leva `/autoinstall.yaml`
  com tudo interativo menos `storage` (`layout: zfs`, maior disco); a
  confirmação destrutiva continua. Segunda entrada no GRUB, "choose storage
  yourself", com `subiquity.autoinstallpath` para um arquivo com
  `interactive-sections: ["*"]` (fluxo padrão). Verde nas duas:
  `root=ZFS=rpool/ROOT/ubuntu_4s6y1t` e LVM na manual.
- **grove conversa com o Hive.** Novo socket de usuário no cortex,
  `/run/hive/user.sock` (0666, qualquer usuário local), que só aceita
  `UserQuery`, entrar/sair do modo anônimo **para o próprio pid** e `Ping` —
  o socket de componentes continua root:hive. No grove: `? pergunta` (a
  pergunta vai ao synapse numa fila prioritária que rajadas de eventos não
  descartam; a resposta volta só para quem perguntou, sempre como texto, sem
  ação), avisos do sistema no próximo prompt (serviço caiu, conflito de
  porta, disco — nunca sugestões, que podem ser sobre comandos de outro
  usuário) e `anon [on|off]` (o cortex ignora o que o shell roda, incluindo
  filhos, pela ancestralidade de processos em `/proc`; a sessão anônima
  some quando a conexão fecha, para um pid reutilizado não herdá-la). O log
  do cortex registra quem perguntou e o tamanho, não o texto. Cliente IPC
  bloqueante no hive-common, já que o grove não tem runtime async.
  5 checagens e2e (vermelhas antes com os binários antigos: 5 falhas),
  incluindo a pergunta feita por um usuário sem privilégios. Resposta real
  no guest: três linhas úteis, uma delas com um comando inventado pelo
  modelo 0.5B (`systemctl list-unavailable`) — a qualidade das respostas é
  o limite agora.

**Continuação — os três itens em aberto.**

- **Ação de pacote nunca tinha funcionado.** O actuator roda como `_hive-act`
  e chamava `apt install`: no guest, "Could not open lock file... are you
  root?" (e `NoNewPrivileges` impede sudo). Agora pacotes vão pelo
  PackageKit (`pkcon`), já presente no Ubuntu server, com uma regra polkit
  que só libera instalar, remover, atualizar e dar refresh a partir de
  fontes confiáveis. O whitelist passou a exigir nome de pacote válido pela
  política Debian (antes, `InstallPackage { name: "--allow-downgrades" }`
  passava). O lab achou mais um: com `PrivateTmp=yes` o pkcon cria o socket
  do debconf num /tmp que o packagekitd não vê ("frontend-socket does not
  exist", código 7) — resolvido com `TMPDIR` num `RuntimeDirectory` da unit,
  mantendo o `PrivateTmp`.
- **Para exercitar isso de ponta a ponta** (e porque é útil): programa não
  encontrado no grove + pacote de mesmo nome disponível no `apt-cache` →
  grove avisa e manda `CommandNotFound` → synapse sugere "Install X"
  (`InstallPackage` tipado; nome validado em cortex, synapse e whitelist;
  no máximo uma oferta por pacote a cada 10 min) → administrador aprova no
  dashboard → snapshot ZFS → pkcon instala. No e2e, offline, com um
  repositório local.
- **Dashboard para administradores que não são root.** O dashboard só
  conectava no socket de componentes (root:hive). Agora usa o socket de
  usuário, e o cortex só o aceita de root ou de membros de sudo/admin/wheel,
  verificado pelos grupos da conta do uid do kernel — não pelo nome do
  processo, e não pelo grupo `hive`, que é o das contas de serviço. Quem não
  é administrador recebe uma mensagem clara antes de a TUI abrir (handshake
  por ping). `UserAction`/`UserDismiss` passaram a ser aceitos só de
  dashboards.
- **Poda de snapshots antigos.** `hive-zfs prune` + `hive-zfs-prune.timer`
  (diário, persistente), como root: remove `hive-*` mais antigos que
  `[zfs] prune_after_days` (14), poupando os `keep_newest` (3) mais novos;
  a idade vem do timestamp no nome, então snapshots de terceiros nunca são
  tocados. O man page do hive-zfs descrevia comandos que não existiam e foi
  reescrito.
- 7 checagens novas ou alteradas (vermelhas antes: 7 falhas), incluindo o
  fluxo de reinício aprovado agora por `druid` (sudo, não root). 72 no
  total.

## 2026-08-24 (continuação 8) - Primeira ISO real do DruidOS, construída e booted

> **Correção (2026-09-10):** o hash abaixo é da primeira build, que *não*
> bootava (sem catálogo El Torito — corrigido no commit `b3b6c6f`, a build
> boa foi `a3f92bf0…`). E o boot nunca tinha sido confirmado visualmente:
> isso só aconteceu com o ISO Lab (entrada acima), que também mostrou que
> essa ISO instalaria Ubuntu puro.

Pedido do usuário: "como eu faço para conectar no druidos?" — depois de
uma sessão inteira testando componentes individuais (via Docker no
Forge), nunca tinha existido uma ISO booted de verdade do projeto. O
usuário escolheu "ver/usar o DruidOS de verdade" em vez de reusar as
ISOs antigas de fevereiro/2026 (pré-pivot TUI-only) ou só repetir os
testes de componente no Forge.

**`scripts/build-iso.sh` nunca tinha sido executado até o fim nesta ou
em nenhuma sessão recente — achou uma cadeia de bugs reais, cada um
bloqueando o próximo:**

1. URL da ISO base do Ubuntu fixa em `24.04` — Ubuntu só mantém a point
   release atual no caminho numerado (`24.04.4`, não `24.04` puro) e
   remove versões antigas. 404. Corrigido: `BASE_POINT_RELEASE`
   parametrizado.
2. Scripts `.sh` chegavam com CRLF no Forge — `.gitattributes` já dizia
   `eol=lf`, mas o checkout local no Windows (com `core.autocrlf=true`,
   que não devo mexer) ainda produz CRLF na working tree, mesmo com o
   blob do git limpo. Corrigido normalizando na chegada em
   `test-on-forge.sh`, sem tocar em config do git.
3. **Achado mais profundo**: Ubuntu 24.04 Server usa o instalador
   Subiquity, que empacota vários squashfs em CAMADAS (pra serem
   sobrepostas no boot), não um único `filesystem.squashfs` como
   ISOs mais antigas (casper). O script pegava a camada ERRADA — uma
   das camadas só-do-instalador (`*.installer*.squashfs`, o próprio
   ambiente Subiquity/curtin), não o rootfs real. Corrigido: extrai as
   duas camadas certas (`ubuntu-server-minimal.squashfs` +
   `ubuntu-server-minimal.ubuntu-server.squashfs`) em ordem.
4. `unsquashfs` falhava criando um "character device" fake
   (`/etc/dpkg/dpkg.cfg.d/excludes`, truque de build pra pular
   instalação de docs/man) — `mknod` dava "Operation not permitted"
   mesmo dentro de um container Docker `--privileged` com todas as
   capabilities (confirmado: não é falta de capability, é alguma
   restrição do ambiente containerd/runtime do Forge que não valeu a
   pena investigar mais fundo — tentei uma VM real via qemu-lab como
   alternativa, mas ela travou de forma inexplicável no SSH do guest
   depois do cloud-init terminar, então abandonei esse caminho).
   Corrigido com `-ignore-errors` do próprio unsquashfs.
5. `-ignore-errors` ainda retorna código de saída 2 ("erros não-fatais
   ocorreram"), que o `set -e` do script tratava como falha total.
   Corrigido com um wrapper (`run_unsquashfs_tolerant`) que só propaga
   erro se o código não for 0 nem 2.
6. `setup_build_dirs()` sempre fazia `rm -rf` no diretório de build
   inteiro ANTES do cache da ISO base ser checado — ou seja, o cache
   nunca funcionava, cada retry baixava os ~3.2GB de novo. Corrigido
   pra só limpar os subdiretórios de extração, preservando `base.iso`.

**Resultado:** `druidos-hive-amd64.iso` (3.4GB,
sha256 `4986a8c5c55474fe5576eb498989881661f862839ebb2a8e9205bfda059d22c7`)
construída com sucesso, com os binários reais do Hive Stack e os
serviços systemd instalados. Trazida do Forge pra esta máquina (hash
conferido, transferência íntegra) e booted via QEMU local.

**Descoberta sobre o boot local:** WHPX (aceleração de hardware do
Windows) está compilado no QEMU instalado, mas **não funciona de
verdade nesta máquina** — falha com "WHPX: No accelerator found" /
"No space left on device" (mensagem enganosa; geralmente significa
Hyper-V não habilitado ou outro hypervisor com acesso exclusivo à
VT-x). Caiu pra `-accel tcg` (emulação por software, funcional mas bem
mais lento).

**Importante:** a ISO gerada é derivada do instalador Ubuntu Server
(Subiquity) — bootar ela abre o **instalador interativo** de verdade
(particionamento, usuário, etc.), não cai direto num shell. É esperado
que o usuário conduza essa parte manualmente na janela do QEMU.

---

## 2026-08-23/24 (continuação 7) - Backend Ollama de teste pro hive-synapse (dev/test only)

Terceiro e último item da lista de pontos em aberto: `hive-synapse` só
tinha inferência mock. O usuário tem um Mac mini no homelab
(`10.10.1.125`, Apple M4, 16GB, Ollama com `qwen2.5:7b`) dedicado a rodar
LLMs — pediu pra usá-lo, mas só para teste (confirmado explicitamente:
"para teste ele pode usar sim"). Isso não conflita com a regra de
segurança do projeto ("hive-synapse nunca tem acesso à rede") porque
`config/systemd/hive-synapse.service` já tem `PrivateNetwork=yes` —
isolamento de namespace de rede real, aplicado pelo systemd,
independente do código. Ou seja: dá pra ter um backend HTTP opcional que
só existe pra dev (feature Cargo `ollama`, desabilitada por padrão) e
mesmo assim a produção continua protegida mesmo em caso de
má-configuração.

**Implementado:** `SynapseConfig` ganhou `backend` (default `"mock"`),
`ollama_url`, `ollama_model`. `hive-synapse/src/inference.rs` ganhou um
`Backend` enum (`Mock` | `Ollama` atrás de `#[cfg(feature = "ollama")]`)
e `ollama_generate()`, que chama `POST {url}/api/generate` com
`stream: false`. O parsing da resposta (`parse_ollama_response`) foi
extraído como função pura, sem depender da feature `ollama` nem do
cliente de rede, pra ficar testável mesmo em builds sem essa feature.
Se `backend = "ollama"` for configurado num build sem a feature, cai de
volta pro mock com um aviso, em vez de falhar.

**Descoberta durante a configuração do Mac:** Ollama estava rodando
(`launchd`/`homebrew.mxcl.ollama`) mas escutando só em
`localhost:11434` — `OLLAMA_HOST` vazio no plist do launchd (que define
`EnvironmentVariables` explicitamente, então `launchctl setenv` global
não tinha efeito nele). Corrigido adicionando `OLLAMA_HOST=0.0.0.0`
direto no plist via `PlistBuddy` e recarregando com
`launchctl bootout`/`bootstrap` — confirmado escutando em `*:11434` e
alcançável do Forge.

**Validação real, parcial:** `hive-synapse` com `backend = "ollama"`
conectou, recebeu uma `SuggestionRequest` de verdade (via
`hive-nerve-process` detectando um comando perigoso disfarçado) e tentou
a chamada HTTP real — mas a conectividade Forge↔Mac mini na LAN do
homelab se mostrou instável durante o teste (GETs que funcionavam
passaram a travar sem padrão claro; nem `curl` direto do host do Forge
completou um `/api/generate` em 2 minutos, e `ollama ps` no Mac nunca
mostrou o modelo carregado, indicando que a requisição nem chegou ao
servidor). Isso é instabilidade de rede do homelab, não bug do
DruidOS — o tratamento de erro funcionou corretamente
("Failed to reach Ollama backend" logado e propagado, sem travar o
processo). Não fechei um round-trip de geração real completo nesta
sessão; código e testes unitários (incluindo o parsing da resposta)
estão prontos e validados, a chamada de rede fim-a-fim fica pendente
pra quando a conectividade cooperar.

Testes: `unknown_backend_falls_back_to_mock`,
`parse_ollama_response_extracts_the_response_field`,
`parse_ollama_response_rejects_malformed_json`,
`parse_ollama_response_rejects_missing_response_field`. Validado
`cargo clippy -p hive-synapse --features ollama --all-targets` limpo, e
o build default (sem a feature) continua passando normalmente.

---

## 2026-08-23 (continuação 6) - Confirmação de ações perigosas no hive-dashboard

Segundo item da lista de pontos em aberto: até aqui, uma ação perigosa
aprovada no dashboard (`Action::is_dangerous()` — `RestoreSnapshot`,
`DeleteSnapshot`, `RemovePackage`, `DeleteFile{permanent:true}`,
`Reboot`, `Shutdown`, `CleanSystem`) sempre voltava rejeitada do
`hive-actuator`, porque não existia nenhum mecanismo real de segunda
confirmação — só um `Enter` já disparava o `UserAction`, e o actuator
recusava tudo que chegasse marcado `requires_confirmation` (fail-closed,
correto, mas sem forma de o usuário realmente confirmar).

**Desenho:** `HiveMessage::UserAction` ganhou um campo `confirmed: bool`.
`hive-dashboard` agora trata a primeira tecla `Enter` sobre uma sugestão
perigosa como "armar" a confirmação (não envia nada, só marca a linha
em vermelho/negrito com "(CONFIRM? press Enter again)" e muda a barra de
status) — só o **segundo** `Enter` sobre a mesma sugestão envia
`UserAction{confirmed: true}`. Navegar pra outra linha ou `Esc`/`d`
cancela a confirmação pendente (em vez de dispensar a notificação, se
havia uma armada). `hive-cortex`'s `act_on_suggestion` agora calcula
`requires_confirmation = action.is_dangerous() && !confirmed` em vez de
só `is_dangerous()`. `hive-actuator` não mudou de lógica — continua
rejeitando quando `requires_confirmation` chega `true`, mas agora isso só
acontece de fato pra ações não confirmadas.

**Validado de verdade no Forge**, não só em teste unitário: o cliente de
teste `fake_synapse` (já existente, ver
[[e2e-test-found-2-real-bugs]]) ganhou `FAKE_SYNAPSE_ACTION=dangerous`
pra mandar uma sugestão `RemovePackage` em vez da `CleanPackageCache`
padrão, e passou a rodar via `setpriv` como `_hive-ai` com
`exec -a hive-synapse` (argv[0] certo) — sem isso, a própria correção de
autenticação de `SuggestionResponse` desta sessão o rejeita, já que ele
não é o `hive-synapse` de verdade. Lendo o log bruto do dashboard: 1º
Enter armou a linha (vermelho/negrito, "(CONFIRM? press Enter again)",
zero requisições no actuator); 2º Enter mandou a confirmação, cortex
calculou `requires_confirmation: false`, e o actuator processou a ação
sem rejeitar por confirmação (só falhou depois por razão de apt dentro
do container, sem relação com o recurso).

**Achado lateral, sem correção nesta sessão:** ao investigar o teste
anterior (não-perigoso) percebi que o dashboard deixa reaprovar uma
linha já aprovada — `Enter` não olha pro `outcome` existente antes de
mandar `UserAction` de novo, gerando um segundo pedido que o cortex
rejeita com `"UserAction for unknown notification"` (a sugestão já foi
removida de `pending_suggestions` da primeira vez). Não é regressão
desta mudança, é comportamento anterior; cosmético (não expõe nada,
só um aviso a mais no log), não atacado agora.

**Achado que impede reusar `fake_synapse` pra testar o fluxo de
sugestão sem se disfarçar de `hive-synapse`:** a correção de
autenticação de `SuggestionResponse` de mais cedo hoje (ver
[[e2e-test-found-2-real-bugs]]) agora bloqueia o próprio `fake_synapse`
por padrão — só funciona rodando como `_hive-ai` com `argv[0]` igual a
`hive-synapse`. Efeito colateral esperado e correto da correção de
segurança, documentado no próprio arquivo do exemplo.

**Nota de processo:** a sincronização pro Forge via
`scripts/test-on-forge.sh` (tar) não garante mtime crescente — o cargo,
que decide recompilar por mtime (não hash de conteúdo) em build padrão,
pode achar que nada mudou e pular a recompilação mesmo com conteúdo
diferente. Descoberto ao editar `fake_synapse.rs` e ver o binário
antigo continuar rodando após um `cargo build` "bem-sucedido" (`Finished
in 0.09s`, sem `Compiling`). Solução: `touch` no arquivo antes de
rebuildar quando iterar fora do pipeline completo de `check.sh`.

---

## 2026-08-23 (continuação 5) - Atacando os pontos em aberto: nerve-process

Depois de "conseguimos nossos objetivos?", o usuário pediu pra atacar os
pontos deixados em aberto na resposta anterior. Priorizados nesta ordem:
(1) investigar por que `hive-nerve-process` não detectou o `rm -rf` no
teste E2E, (2) confirmação de ações perigosas no `hive-dashboard`, (3)
SLM real via Ollama no Mac mini do homelab (só pra teste — produção
continua sem rede, ver [[security-audit-2026-08]]). Grove async ficou de
fora (já era "fora de escopo" no plano anterior).

**Achado 1, corrigido:** `get_component_type` (`hive-cortex/src/main.rs`)
lia `/proc/{pid}/comm`, que o kernel trunca em 15 bytes (`TASK_COMM_LEN-1`).
`hive-nerve-process` (19 chars) vira `hive-nerve-proc` truncado — nunca
bate no `from_name()`, sempre cai em `Unknown`. Mesmo problema afeta
`hive-nerve-journal` e `hive-nerve-network` (também >15 chars).
Confirmado empiricamente lendo `/proc/PID/comm` de um processo real no
Forge. Corrigido: agora lê `argv[0]` de `/proc/{pid}/cmdline` (não
truncado) em vez de `comm`. Revalidado: cortex agora loga
`Component type: NerveProcess` em vez de `Unknown` pro mesmo binário.

**Achado 2, confirmado mas não corrigido — condição de corrida real no
polling:** testei disparando 30 `rm -rf` rápidos e independentes contra
um `hive-nerve-process` real — só **1 dos 30** foi detectado. Um processo
de controle (cmdline igual, mas vida útil de 2s via `sleep`) foi pego
sem problema, confirmando que a lógica de regex está certa; o problema é
puramente o intervalo de poll de 250ms em `/proc`: um comando que roda e
sai mais rápido que isso (o caso comum pra `rm`/`dd`/etc.) pode nunca
aparecer numa varredura. O próprio comentário do código já previa isso
("Uses proc connector (if available) or polling") mas só o polling foi
implementado — nunca o netlink proc connector (`NETLINK_CONNECTOR`,
`CN_IDX_PROC`), que entregaria eventos de exec() de forma síncrona
independente da vida útil do processo. Implementar isso é um recurso
isolado e substancial (socket netlink cru, `CAP_NET_ADMIN`, comportamento
diferente dentro de container sem privilégios extras) — sinalizado ao
usuário, não implementado ainda nesta sessão.

---

## 2026-08-23 (continuação 4) - Teste E2E real via SSH no Forge: 2 bugs reais encontrados e corrigidos

Pedido do usuário: "testa o fluxo principal, conecta via ssh e testa ele" —
não apenas rodar `cargo test`, mas subir os daemons de verdade (root +
usuários dedicados `_hive-ai`/`_hive-sense`/`_hive-act`) num container no
Forge e observar o fluxo ponta a ponta.

**Isso encontrou 2 bugs reais que nenhum teste unitário pegaria, porque
nenhum deles roda com sockets Unix de verdade entre usuários diferentes:**

1. **Socket do cortex não tinha o grupo `hive`.** `IpcServer::bind`
   (`crates/hive-common/src/ipc.rs`) fazia `chmod 0660` no socket mas
   nunca `chown`ava pro grupo `hive` — a permissão 0660 só funciona se o
   grupo do arquivo for `hive` de verdade. Em produção isso "funciona por
   acidente" porque o `.service` do systemd define `Group=hive`, e o
   processo herda esse gid ao criar o socket. Rodando `hive-cortex` como
   root puro (sem essa diretiva), o socket saía `root:root` e
   `hive-synapse`/`hive-actuator`/`hive-nerve-process` (grupo `hive`, não
   `root`) levavam `Permission denied (os error 13)` — confirmado ao
   rodar o teste E2E pela primeira vez, os 3 processos morreram na
   inicialização. **Corrigido**: `IpcServer::bind` agora resolve o grupo
   `hive` via `nix::unistd::Group::from_name` e faz `chown` explícito no
   socket, com aviso (não erro fatal) se o grupo não existir — mantém dev
   de usuário único funcionando sem setup extra.

2. **`SuggestionResponse` não verificava quem mandou.** Descoberto ao
   escrever `examples/fake_synapse.rs` (cliente de teste que injeta uma
   `SuggestionResponse` com uma `Action` real pra exercitar o caminho
   `UserAction`→`ActionRequest`, já que o `hive-synapse` real ainda é só
   mock e nunca anexa `Action` ao que "sugere"): rodando como root mas
   sem se chamar `hive-synapse`, o cortex aceitou e processou a sugestão
   de qualquer forma — o mesmo tipo de furo que a `ActionRequest` já
   tinha (auditoria anterior, ver [[security-audit-2026-08]]), só que na
   entrada de sugestões em vez da execução direta. **Corrigido**:
   `route()` em `router.rs` agora confere `component_type_of(from_conn)
   == Some(ComponentType::Synapse)` antes de aceitar (novo helper
   `CortexState::component_type_of`); caso contrário rejeita com `warn!`,
   igual ao padrão já usado pra `ActionRequest`. Teste novo:
   `suggestion_response_from_a_non_synapse_connection_is_rejected`.

**Reteste depois da correção — tudo validado de verdade, não só em
teste unitário:**
- `hive-cortex` (root), `hive-synapse` (`_hive-ai`), `hive-actuator`
  (`_hive-act`), `hive-nerve-process` (`_hive-sense`) e `hive-dashboard`
  (root, rodado manualmente) conectaram e se registraram com o tipo
  correto — sem nenhum "Permission denied".
- `fake_synapse` (root, mas não chamado `hive-synapse`) tentou injetar
  a sugestão de novo — cortex rejeitou corretamente:
  `Rejecting SuggestionResponse from connection 5 (component type
  Some(Unknown), expected Synapse)`.
- `hive-dashboard` renderizou corretamente (confirmado lendo o log bruto
  de escape codes do processo: título "Hive Dashboard", borda, estado
  vazio "(nothing yet)"/"Select a notification on the left.", barra de
  status "Connected. Waiting for Hive activity..."). A captura via
  `tmux capture-pane -p` ficou em branco nas 4 tentativas — investigado,
  não é bug do dashboard (o log bruto prova que o frame foi desenhado
  certo), é uma limitação do harness de teste (tmux capture-pane vs.
  timing/alt-screen), não vale a pena perseguir mais.
- `hive-nerve-process` não detectou o `rm -rf` disparado diretamente no
  shell do script — mecanismo de observação dele não é esse tipo de
  gatilho direto; não é regressão desta sessão, já era assim antes.

**Consequência importante:** as correções de segurança feitas mais cedo
nesta sessão (autenticação por peer-uid, whitelist, etc.) nunca tinham
sido exercitadas com usuários Unix separados de verdade até este teste —
só em testes unitários com canais `mpsc` fake. O bug do grupo do socket
mostra que "logicamente correto" e "funciona numa implantação real com
privilégios separados" são coisas diferentes, e só o teste E2E via SSH
pegou isso.

**Pendências que ficaram claras neste teste, não resolvidas ainda:**
- `crates/hive-dashboard/examples/fake_synapse.rs` existe localmente e
  no Forge mas não foi commitado — é útil como ferramenta de teste manual
  permanente (é a única forma de exercitar `UserAction`→`ActionRequest`
  com uma `Action` real hoje, já que `hive-synapse` real não anexa
  `Action` às sugestões que "gera"), mas também é código de teste que
  normalmente não iria pro histórico principal sem decisão explícita.
- Container `druidos-e2e` no Forge continua rodando (`sleep infinity`)
  pra permitir mais depuração se necessário.

---

## 2026-08-23 (continuação 3) - hive-dashboard + fluxo UserAction→ActionRequest

Terceira parte da sessão (mesmo dia). Depois de higiene e docs, atacou-se
o item mais substancial: como o Hive avisa o usuário sem GUI, e o
`HiveMessage::UserAction` que continuava um `// TODO` — ou seja, mesmo
com whitelist e autenticação corrigidas, nada gerava `ActionRequest` de
verdade.

**Achado que mudou o plano original:** o Grove hoje é síncrono
(`stdin().read_line()` puro, sem tokio) e nem executa comando externo
ainda. Integrar notificação ali exigiria primeiro reescrevê-lo pra
async. Optou-se por um binário novo, `hive-dashboard` (ratatui,
`tokio::select!` entre eventos de terminal via `crossterm::EventStream`
e o socket IPC — mesmo padrão dos daemons existentes), em vez de mexer
no Grove. Roda manualmente pelo usuário (tipo `top`), sem serviço
systemd.

**Mudanças no `hive-cortex`:**
- `ComponentType::Shell` renomeado pra `Dashboard` — o nome "Shell"
  ficou associado ao overlay Wayland arquivado.
- `SuggestionResponse` agora é guardado (`CortexState.pending_suggestions`)
  e vira uma `Notification` carregando as sugestões no campo `actions`
  (que já existia em `HiveMessage::Notification`, nunca populado).
  Corrigiu de passagem um bug anterior a esta sessão: `forward_to_synapse`
  nunca registrava a conexão de origem (parâmetro literalmente chamado
  `_from`), então uma `SuggestionResponse` nunca poderia ter voltado pelo
  caminho antigo (`forward_to_requester`).
- `UserAction` agora busca a sugestão, e se ela tem uma `Action`, monta
  `ActionRequest` e despacha direto pro actuator (`forward_to_actuator`,
  chamado internamente — não passa pelo caminho da rede, que foi fechado
  na correção de segurança). `requires_confirmation` vem de
  `Action::is_dangerous()` — ações perigosas continuam sendo rejeitadas
  pelo actuator (falha fechado, já corrigido), já que ainda não existe
  UI de confirmação — limite aceito de v1, não uma lacuna nova.
- `UserDismiss` agora limpa `pending_suggestions` de verdade.

`hive-common`: `Action` (e os tipos que ela usa) ganhou `PartialEq` —
o `hive-dashboard` precisa disso pra correlacionar um `ActionResponse`
recebido (que só carrega a `Action`, não o notification/suggestion id)
com a linha que está esperando por ele.

16 testes no `hive-cortex` (5 novos: fluxo de sugestão, ação perigosa
vs não-perigosa, notification_id desconhecido, dismiss) + 8 no
`hive-dashboard` (lógica pura de estado — expandir notificação em
linhas, casar ActionResponse, navegação da lista, mapeamento de tecla).
Tudo validado no Forge e na CI real do GitHub antes do push
(commit `2ba745f`).

Docs atualizados: `CLAUDE.md` (as duas perguntas em aberto que isso
resolve), `docs/architecture.md`, `docs/HIVE-STACK.md`,
`docs/user-guide.md`, `debian/control`/`rules` (empacota o binário novo).

### Em aberto
- Confirmação interativa de ações perigosas dentro do dashboard (v2).
- Grove continua síncrono e sem execução de comando externo — achado
  incidental desta sessão, não endereçado (não foi pedido).
- `pending_suggestions` não tem expiração por tempo (mesmo nível do
  `pending_requests` já existente).

---

## 2026-08-23 (continuação) - Correção dos achados de segurança + higiene

Mesmo dia, continuação direta da entrada abaixo. Os 5 achados de
segurança listados na entrada anterior como "nenhum corrigido" **foram
todos corrigidos** nesta parte da sessão (commit `6fe1144`), validados
pelo loop do Forge e depois pela CI real do GitHub:

1. **Autenticação por uid real**: `hive-cortex` agora cruza o tipo de
   componente autodeclarado (`/proc/pid/comm`) com o uid de verdade da
   conexão (`nix::unistd::User::from_uid`), batendo contra o usuário
   esperado em `config/systemd/hive-*.service`. Mismatch rebaixa pra
   `Unknown`. `crates/hive-cortex/src/main.rs`.
2. **`ActionRequest` externo rejeitado**: `router.rs` não encaminha mais
   `ActionRequest` vindo de qualquer conexão — só cortex deveria gerar
   essa mensagem (protocolo documentado), e hoje nem gera ainda (`UserAction`
   continua TODO). `forward_to_actuator` ficou com `#[allow(dead_code)]`
   pra quando esse fluxo for construído.
3. **Confirmação falha fechado**: `hive-actuator` rejeita ações que
   pedem confirmação em vez de executar mesmo assim (não existe UI pra
   confirmar de verdade ainda).
4-5. **Whitelist reescrita**: `crates/hive-actuator/src/whitelist.rs`
   agora corresponde 1:1 ao enum `Action` real (o `whitelist.toml`
   antigo referenciava tipos de ação que não existem no código). Matching
   exato de comando+args posicionais (fechou o bypass `iptables` via
   `"ip"`), glob `*` pra paths/serviços/pacotes, default é negar tudo
   (antes era uma lista "seguras" hardcoded que podia divergir do arquivo
   real). Rate limit por tipo de ação, além do global já existente.

Escopo explicitamente fora: o fluxo `UserAction`→`ActionRequest` em si
(feature nova, não correção), autorização granular por tipo de mensagem
além de `ActionRequest`.

### Higiene rápida

- Removidos 20 arquivos soltos na raiz (untracked): lixo de debug (`nul`,
  logs vazios/obsoletos) e scripts que apontavam pra `dist/v0.4-fb`
  (arquivado) ou pra VMs de build antigas (substituídas pelo Forge).
  Mantidos `kill-qemu.ps1`/`kill-all-qemu.ps1` (genéricos).
- Chave SSH em `qemu-workspace/keys/` confirmada já coberta pelo
  `.gitignore` (não movida — é o workspace esperado pelo MCP `qemu-lab`).
- `installer/` (instalador TUI em ratatui/crossterm — já alinhado com o
  pivot) nunca esteve no workspace Cargo, nunca compilou/lintou/testou.
  Adicionado; corrigidos os 4 avisos reais de clippy da primeira
  passada.

Memória `security-audit-2026-08` atualizada para refletir que os 5
achados estão corrigidos.

---

## 2026-08-23 - Auditoria, pipeline de testes e cobertura nova

### Auditoria do projeto

Achados de segurança na Hive Stack (nenhum corrigido nesta parte da
sessão — corrigidos mais tarde no mesmo dia, ver entrada acima):

- `hive-cortex` autentica componentes por `/proc/{pid}/comm`
  (`get_component_type`), não pelo uid do peer credential que já coleta —
  qualquer processo local pode se passar por outro componente só nomeando
  o binário.
- `router.rs` encaminha `ActionRequest` de **qualquer** conexão direto pro
  actuator, sem checar se veio do próprio cortex.
- Confirmação de ação (`requires_confirmation`) é um `// TODO: Handle
  confirmation requirement` que não faz nada — executa mesmo assim
  (`hive-actuator/src/main.rs`).
- `config/hive/whitelist.toml` (schema rico, `[[actions]]`) é incompatível
  com o struct Rust que o lê (`WhitelistConfig`) — carrega quase vazio e
  trata pacotes como "permitir todos" por padrão.
- Matching de comando por prefixo de string na whitelist libera
  `iptables` via `"ip"`, e `find`/`git` sem restrição de argumentos
  permitem exec arbitrário (ex.: `git -c core.fsmonitor=...`).

Achados de higiene:

- `qemu-workspace/keys/id_ed25519` (chave SSH privada) sentado na árvore
  de trabalho, untracked mas não ignorado.
- `.gitignore` não cobria `dist/`, `output/`, `qemu-workspace/` —
  corrigido nesta sessão (ver abaixo, quase mandou 54GB pro Forge).
- Vários arquivos soltos na raiz (`nul`, `print.png`, `*.log`, `*.ps1`)
  ainda não tratados.

### Pipeline de testes: CI corrigida + loop no Forge

`.github/workflows/ci.yml` ("CI": fmt/clippy/test/build/audit/docs) nunca
tinha rodado nem uma vez — disparava só em push pra `main`/`develop`, e
todo o trabalho acontece em branches `claude/**`. Corrigido o trigger.
Na primeira run real, apareceu um segundo bug pré-existente: a action
`dtolnay/rust-action@stable` não existe (é `dtolnay/rust-toolchain@stable`)
— todo job falhava em "Set up job". Corrigido.

`rust-build.yml` ("Rust Components Build") foi removido: disparava em
`claude/**` certo, mas o filtro de paths (`bark/**`, `spore/**`,
`grove/**`) é de antes da Hive Stack entrar no workspace — nunca testou
nenhum crate `hive-*`, que é onde vive a maior parte do código.

Criado `scripts/check.sh` (fmt --check + clippy -D warnings + test
--workspace, mesmo comando que a CI roda) e, como o Windows não
cross-compila os crates que puxam `ring`/`openssl-sys` (falta um
`x86_64-linux-gnu-gcc`), um loop local via o Forge (servidor Docker do
homelab, `10.10.1.40`, SSH alias `forge`): `scripts/test-on-forge.sh`
empacota a árvore de trabalho (`git ls-files`, pega inclusive o que não
foi commitado ainda) e roda `check.sh` lá dentro de um container
(`scripts/forge-test.Dockerfile`, imagem `rust:1-bookworm` +
rustfmt/clippy/libssl-dev). Nada compila localmente no Windows; registry
do cargo e `target/` persistem no Forge entre execuções.

**Quase-incidente:** o `.gitignore` nunca cobrindo `dist/`/`output/`/
`qemu-workspace/` significava que `git ls-files --others --exclude-standard`
ia mandar ~54GB (ISOs, discos qcow2, e a chave SSH privada) pro Forge no
primeiro sync. Pego antes de completar, processo travado morto, 41GB
parciais limpos do Forge (via container root, os arquivos ficaram
root-owned pelo build dentro do container), `.gitignore` corrigido.

### Débito técnico: backlog de clippy zerado

O workspace nunca tinha passado por `cargo clippy --workspace --all-targets
-- -D warnings` de ponta a ponta. Usando o loop do Forge, apareceram (e
foram corrigidos) ~20 avisos reais em 8 crates: imports não usados,
closures redundantes, `derivable_impls` (2x `impl Default` manual que
vira `#[derive(Default)]`), `useless_vec!`, `manual_strip`,
`single_match`/`collapsible_match`, `needless_return`, um método
`to_string()` inerente virou `impl Display`, um `History::next()` renomeado
pra `next_entry()` (conflitava com o nome do método do trait `Iterator`),
e `#[allow(dead_code)]` com justificativa numa linha pros campos/métodos
que são scaffolding genuína ainda não conectada (`FsEvent::PermissionChanged`
e seus métodos `description`/`severity`, `recent_paths`,
`create_pre_operation_snapshot`, e os campos `pid`/`uid`/`config` do
`hive-cortex` — estes últimos são os mesmos da auditoria de segurança;
o `allow` só cala o lint, não mexe no comportamento).

### Cobertura de testes nova

`hive-cortex/src/router.rs` (282 linhas, 0 testes antes — é o coração do
roteamento de mensagens) ganhou 7 testes construindo um `CortexState`/
`SharedState` real e componentes falsos via canais `mpsc` (mesmo padrão
já usado no teste de IPC do `hive-common`, só sem socket de verdade):
Ping/Pong, `CommandObserved` → synapse, supressão em modo anônimo,
`PortConflict` → synapse+shell, `ActionRequest` → actuator, e
`ActionResponse` voltando pro requisitante original via `request_id`.

`hive-actuator/src/main.rs` (817 linhas, 0 testes) ganhou 4 testes pro
`RateLimiter` (janela de taxa) e `is_destructive_action`.

`hive-cortex/src/main.rs` ganhou 2 testes pro `ComponentType::from_name`.

Deixado de propósito fora: testes de integração que exercitariam o gap
de autorização do router — nasceriam vermelhos sem corrigir o bug
primeiro, então ficam pra a sessão de segurança dedicada.

### Commits desta sessão (em cima de `897cd44`)

1. `fb49bac` refactor: redefine project target to TUI-only, archive GUI track
2. `8183cf5` style: apply cargo fmt across the Hive Stack
3. `bb5846e` ci: fix test pipeline triggers, drop redundant workflow
4. `539e918` fix: correct dtolnay/rust-toolchain action name in ci.yml
5. `4f22e3b` fix: clear the clippy -D warnings backlog across the workspace
6. `cd9c2c0` feat: add Forge-based test loop (native Linux, no WSL/cross-compile)
7. `92e5fae` test: add unit coverage for hive-cortex routing and hive-actuator

### Em aberto (status no fim do dia — ver as duas entradas acima)

- ~~Correções de segurança da auditoria~~ — **corrigidas**, ver entrada
  "Correção dos achados de segurança + higiene" acima.
- `docs/architecture.md`, `docs/security-model.md`, `docs/user-guide.md`,
  `scripts/build-iso.sh`, `scripts/build-image.sh`, `installer/src/main.rs`
  (as opções `enable_hive`/`install_desktop`, especificamente — o crate em
  si já compila/linta desde a limpeza de higiene), `.github/workflows/release.yml`
  ainda descrevem o desktop Hyprland/Wayland como atual — não atualizados
  no pivot TUI-only (fora de escopo na hora).
- ~~Higiene de repositório: arquivos soltos na raiz~~ — **limpos** (ver
  entrada acima). Ainda pendente: `.mcp.json`/`config/hive/config.toml`
  untracked, indefinido se deveriam ser versionados.
- Mecanismo de notificação do Hive sem GUI ainda indefinido (ver entrada
  do pivot, abaixo).

---

## 2026-08-23 - Redefinição de alvo: TUI-only (sem GUI)

### Decisão

O projeto tinha duas apostas gráficas CPU-only em paralelo, nenhuma
integrada de ponta a ponta:
1. `bark` + `spore` — engine de framebuffer direto (mmap em `/dev/fb0`),
   sendo depurada na sessão anterior (v0.4-fb, segfault de mmap).
2. `hive-shell` + `hive-dock` + `hive-term` — desktop Wayland/Hyprland
   com renderização via Mesa+LLVMpipe, nunca chegou a ter service systemd.

Decisão: **abandonar GUI, focar 100% em terminal/TUI**, com `grove` como
interface principal.

### Ações

- Movidos para `archive/` (fora do workspace Cargo, histórico git preservado
  via `git mv`): `bark/`, `spore/`, `crates/hive-shell/`, `crates/hive-dock/`,
  `crates/hive-term/`, `examples/fb-test.rs`, `assets/`,
  `config/hyprland/`, `config/waybar/`, `config/applications/*.desktop`.
- `Cargo.toml` raiz: removidos os 5 crates gráficos do `members` e as
  dependências `memmap2`/`input-linux` (únicos consumidores eram `bark`).
- `grove/Cargo.toml`: removida dependência `bark` (não era usada no código).
- `debian/control`: removido pacote `druidos-hive-desktop` e os
  build-deps `libwayland-dev`/`libxkbcommon-dev`.
- `CLAUDE.md`, `docs/HIVE-STACK.md`, `STATUS.md`: atualizados para refletir
  o novo escopo.

### Em aberto

Sem `hive-shell`, ainda não está definido como `hive-cortex` deve entregar
notificações/sugestões ao usuário (inline no Grove? painel TUI separado?).
Ver "Open Questions" em `CLAUDE.md`. `ComponentType::Shell` no
`hive-cortex/src/router.rs` continua no código, sem consumidor registrado.

Fixes não commitados do framebuffer (`archive/bark/src/framebuffer.rs`)
foram preservados no código arquivado, só saíram do build ativo.

---

## 2026-02-20 - v0.4 Framebuffer Development

### Objetivo
Validar bark (HAL) e spore (2D rendering engine) para implementar GUI sem GPU.

### Conquistas

#### 1. Framebuffer Funcionando
- `/dev/fb0` aparece com parâmetro `vga=0x31B`
- Resolução: 1280x1024 @ 24bpp
- fb-test abre framebuffer com sucesso

#### 2. Bugs Identificados em `bark/src/framebuffer.rs`

**Bug 1: mmap sem tamanho explícito**
```rust
// ANTES (não funciona para device files):
MmapMut::map_mut(&file)

// DEPOIS (fix aplicado):
memmap2::MmapOptions::new()
    .len(size)
    .map_mut(&file)
```

**Bug 2: flush() assumia 32bpp**
O método foi reescrito para suportar 24bpp, 32bpp e 16bpp.

#### 3. DruidOS v0.4-fb Criado
- `dist/v0.4-fb/bonsai-kernel` (15MB)
- `dist/v0.4-fb/bonsai-initramfs.img` (2.6MB) - sem SLM

### Problema Atual
Fixes estão no código mas **não compilados**. O fb-test atual dá segfault.

### Ambiente de Build Quebrado
- VM Ubuntu: kernel panic "IO-APIC + timer doesn't work"
- WHPX: "No space left on device"
- WSL: disponível mas sem distribuição

### Solução Pendente
Instalar WSL Ubuntu:
```powershell
wsl --install -d Ubuntu
```
Depois rodar `build-fb-test.sh`

### Scripts Criados
- `run-fb.ps1` - Inicia DruidOS com framebuffer
- `kill-all-qemu.ps1` - Mata todos QEMU
- `build-fb-test.sh` - Compila fb-test (Linux)

### Parâmetros QEMU para Framebuffer
```
-vga std -append "vga=0x31B noapic nolapic console=tty0"
```

---

## 2026-02-19 - Sessão de Desenvolvimento

### Ambiente Configurado
- **QEMU**: 10.2.0 instalado no Windows
- **MCP qemu-lab**: Funcionando para controlar VMs
- **VM Ubuntu 24.04**: Rodando via nested virtualization (Proxmox → Windows → QEMU)
- **Rust**: 1.93.1 instalado tanto no Windows quanto na VM

### Conquistas

#### 1. MCP QEMU Lab Operacional
- VM Ubuntu 24.04 cloud image bootando com sucesso
- SSH funcional (com chave em `qemu-workspace/keys/id_ed25519`)
- Disco expandido de 2.4GB para 11GB para acomodar compilação

#### 2. Workspace Rust Unificado
- Adicionados 13 crates `hive-*` ao workspace
- Dependências workspace atualizadas (bincode, toml, uuid, dirs, regex, which, etc.)
- Cross-check funciona no Windows para target `x86_64-unknown-linux-gnu`

#### 3. Build Completo na VM Ubuntu
Todos os 13 binários da Hive Stack compilados em release:

| Binary | Tamanho | Descrição |
|--------|---------|-----------|
| hive-cortex | 2.2M | Orquestrador central |
| hive-synapse | 2.2M | Motor de IA (Candle + tokenizers) |
| hive-actuator | 2.3M | Executor de ações |
| hive-apt | 1.1M | Wrapper inteligente do APT |
| hive-zfs | 2.2M | Integração ZFS |
| hive-nerve-process | 2.7M | Monitor de processos |
| hive-nerve-journal | 2.8M | Monitor de logs (journald) |
| hive-nerve-network | 2.1M | Monitor de rede |
| hive-nerve-fs | 2.0M | Monitor de filesystem |
| hive-shell | 2.2M | Overlay desktop |
| hive-dock | 2.0M | Dock bar |
| hive-term | 2.2M | Terminal emulator |

**Total: ~25MB** (release, LTO, stripped)

### Problemas Encontrados e Soluções

#### SSH Timeout no MCP
- **Problema**: `guest_exec` do MCP dava timeout
- **Solução**: Usar SSH direto com a chave em `qemu-workspace/keys/id_ed25519`

#### Disco Pequeno na VM
- **Problema**: Cloud image tem apenas 2.4GB, Rust precisa de mais
- **Solução**: `qemu-img resize disk-overlay.qcow2 +8G` + `resize2fs`

#### Cross-compile no Windows
- **Problema**: MSVC não instalado, link.exe errado
- **Solução**: Toolchain GNU (`stable-x86_64-pc-windows-gnu`)
- **Limitação**: hive-synapse precisa de OpenSSL/cross-compiler completo

### Workflow de Build

```bash
# No Windows (cross-check apenas):
cargo check -p hive-common --target x86_64-unknown-linux-gnu

# Na VM Ubuntu (build completo):
ssh -i qemu-workspace/keys/id_ed25519 -p PORT lab@127.0.0.1
cd ~/druidos
source ~/.cargo/env
cargo build --workspace --release

# Copiar binários de volta:
scp -i qemu-workspace/keys/id_ed25519 -P PORT lab@127.0.0.1:~/druidos/target/release/hive-* target/release/
```

### ✅ Hive Stack Testada
- hive-cortex rodando com sucesso
- Socket IPC criado em `/run/hive/cortex.sock`
- Config completo em `/etc/hive/config.toml`

### Próximos Passos
1. [x] ~~Criar ISO do DruidOS~~ ✅ Feito!
2. [x] ~~Testar comunicação entre componentes~~ ✅ Funcionando!
3. [ ] Integrar modelo SLM

---

## 2026-02-19 - Sessão 2: Hive Stack Completa

### ✅ ISO DruidOS Criada

- **Arquivo**: `output/druidos-0.1.0-amd64.iso` (1.5GB)
- **Base**: Ubuntu 24.04 minimal via debootstrap
- **Ferramentas**: grub-mkrescue, squashfs-tools
- **Status**: GRUB funciona, kernel inicia (lento em TCG/software emulation)

### ✅ Hive Stack Backend Completa

7 componentes rodando simultaneamente com IPC funcional:

| Componente | PID | Conexão | Status |
|------------|-----|---------|--------|
| hive-cortex | 11751 | - | Orquestrador ativo |
| hive-nerve-process | 11816 | 1 | Interceptando rm,chmod,dd |
| hive-nerve-journal | 11924 | 2 | Monitorando logs |
| hive-nerve-network | 11930 | 3 | Monitorando portas |
| hive-nerve-fs | 12050 | 4 | Watching /etc,/var/log,/home |
| hive-actuator | 12049 | 5 | Pronto (0 ações whitelist) |
| hive-synapse | 12163 | 6 | Mock inference (sem modelo) |

### ✅ Interceptação de Comandos Testada

```
[INFO] Detected dangerous command 'rm': rm -rf /home/lab/...
```

O nerve-process detecta padrões perigosos e envia ao cortex via IPC.

### Componentes Desktop (Pendente)

- hive-shell, hive-dock, hive-term requerem Wayland
- Não podem ser testados na VM sem ambiente gráfico

### Próximos Passos
1. [ ] Download modelo SLM (Qwen 2.5 0.5B GGUF)
2. [ ] Testar inferência real no synapse
3. [ ] Configurar Hyprland na ISO

---

## Notas Técnicas

### VM de Desenvolvimento
- **ID**: vm-ubuntu-test-60eefea9
- **SSH Port**: Dinâmico (verificar com `vm_status`)
- **Usuário**: lab
- **Chave SSH**: `qemu-workspace/keys/id_ed25519`

### Estrutura de Arquivos
```
druidos/
├── target/release/       # Binários Linux (copiados da VM)
│   ├── hive-cortex
│   ├── hive-synapse
│   └── ...
├── crates/               # Código fonte
│   ├── hive-common/
│   ├── hive-cortex/
│   └── ...
├── qemu-workspace/       # VMs e artefatos QEMU
│   ├── keys/             # Chaves SSH
│   ├── vms/              # Discos das VMs
│   └── logs/             # Logs QEMU
└── scripts/              # Scripts de build
    └── build-iso.sh      # Gerador de ISO
```
