# DruidOS - Status do Desenvolvimento

**Data:** 2026-02-20
**Versão:** 0.3.0-slm

---

## Resumo Executivo

DruidOS alcançou o **primeiro SLM (Small Language Model) funcionando**: o usuário pode fazer perguntas em linguagem natural via comando `ask` e receber respostas em português. O modelo Qwen 2.5 0.5B carrega no boot e responde via HTTP API.

```
/ # ask ola tudo bem
Olá! Estou bem, obrigado. Como posso ajudar?
```

Também temos o `hive-cortex` (orquestrador central) rodando com socket IPC em `/run/hive/cortex.sock`.

---

## O Que É o DruidOS

DruidOS é uma distribuição Linux VM-first que integra uma IA local chamada "The Hive" (A Colmeia). O sistema observa o que o usuário faz e oferece sugestões inteligentes.

- **Kernel**: Linux 6.8+ (atualmente usando Ubuntu 6.8.0-100)
- **Stack**: 100% Rust (Hive Stack compilada, não integrada ainda)
- **IA**: SLM local (Qwen 0.5B) - modelo baixado, inferência pendente
- **Desktop**: Wayland/Hyprland - não integrado ainda

---

## Arquivos de Distribuição

### v0.3-slm (Atual)
Localização: `dist/v0.3-slm/`

| Arquivo | Tamanho | Descrição |
|---------|---------|-----------|
| `bonsai-kernel` | 15 MB | Kernel Linux 6.8.0-100-generic |
| `bonsai-initramfs.img` | ~470 MB | Initramfs com BusyBox + Hive + SLM |

**Nota:** O initramfs é grande devido ao modelo Qwen 2.5 0.5B (469 MB).

### v0.2-cortex (Preservado)
Localização: `dist/v0.2-cortex/`

| Arquivo | Tamanho | Descrição |
|---------|---------|-----------|
| `bonsai-kernel` | 15 MB | Kernel Linux 6.8.0-100-generic |
| `bonsai-initramfs.img` | 3.1 MB | Initramfs com BusyBox + hive-cortex |

### v0.1-minimal (Preservado)
Localização: `dist/v0.1-minimal/`

| Arquivo | Tamanho | Descrição |
|---------|---------|-----------|
| `druidos-bonsai.iso` | 27 MB | ISO bootável com GRUB |
| `bonsai-kernel` | 15 MB | Kernel Linux 6.8.0-100-generic |
| `bonsai-initramfs.img` | 700 KB | Initramfs mínimo com BusyBox |

### Checksums (SHA256)
```
bonsai-kernel:        528d909745819a1464848a2c4d91c609db4f54b33ccae7069aad4178fb34606f
bonsai-initramfs.img: ef1abd44dfbdc9a8a37cece427491e5c0017a934b19297142ae685a30e4ed6b1
druidos-bonsai.iso:   8491747ba7a7d541ffbb57aa592a16fc3dccc853cae4b45e361756fb7500ddbe
```

---

## Como Bootar

### v0.3-slm (Com SLM - Requer mais recursos)
```bash
qemu-system-x86_64 \
    -m 4096 \
    -smp 4 \
    -machine pc \
    -cpu qemu64 \
    -kernel dist/v0.3-slm/bonsai-kernel \
    -initrd dist/v0.3-slm/bonsai-initramfs.img \
    -append "console=tty0 noapic nolapic" \
    -vnc :0
```
Conecte via VNC em `localhost:5900`.

### Boot Direto Mínimo (v0.1/v0.2)
```bash
qemu-system-x86_64 -m 512 \
    -kernel dist/v0.1-minimal/bonsai-kernel \
    -initrd dist/v0.1-minimal/bonsai-initramfs.img \
    -append "console=ttyS0 console=tty0 quiet" \
    -nographic
```

---

## Progresso Completo

### ✅ Fase 1: Ambiente de Build
- [x] QEMU 10.2.0 no Windows
- [x] MCP qemu-lab funcionando
- [x] VM Ubuntu 24.04 para compilação
- [x] Rust 1.93.1 na VM

### ✅ Fase 2: Hive Stack (Compilação)
- [x] 12 binários hive-* compilados
- [x] ~25MB total (release, LTO, stripped)
- [x] Testados na VM Ubuntu

### ✅ Fase 3: Boot Mínimo
- [x] Kernel Ubuntu 6.8.0 extraído
- [x] Initramfs com BusyBox criado
- [x] Boot funcional em ~1.5s
- [x] ISO bootável com GRUB

### ⏳ Fase 4: Sistema Base (Próximo)
- [ ] Filesystem root persistente
- [ ] Login de usuário (`druid`)
- [ ] Rede automática (DHCP)
- [ ] Systemd como init

### ✅ Fase 5: Integração Hive (Parcial)
- [x] Binários hive-* no sistema (hive-cortex)
- [x] hive-cortex iniciando no boot
- [x] Socket IPC funcional (/run/hive/cortex.sock)
- [ ] Nerves conectando ao cortex

### ✅ Fase 6: IA (Parcial)
- [x] Modelo Qwen 0.5B no sistema
- [x] llama-server com inferência real (HTTP API)
- [x] Comando `ask` para interação em linguagem natural
- [ ] hive-synapse integrando com llama-server
- [ ] Sugestões end-to-end

### ⏳ Fase 7: Desktop
- [ ] Wayland/Hyprland
- [ ] hive-shell overlay
- [ ] hive-term terminal
- [ ] hive-dock

---

## Binários Hive Compilados

Todos em `target/release/` (Linux ELF 64-bit):

| Binary | Tamanho | Função | Status |
|--------|---------|--------|--------|
| hive-cortex | 2.2M | Orquestrador central | Compilado |
| hive-synapse | 2.2M | Motor IA | Compilado |
| hive-actuator | 2.3M | Executor de ações | Compilado |
| hive-apt | 1.1M | APT inteligente | Compilado |
| hive-zfs | 2.2M | Snapshots ZFS | Compilado |
| hive-nerve-process | 2.7M | Monitor processos | Compilado |
| hive-nerve-journal | 2.8M | Monitor logs | Compilado |
| hive-nerve-network | 2.1M | Monitor rede | Compilado |
| hive-nerve-fs | 2.0M | Monitor filesystem | Compilado |
| hive-shell | 2.2M | Overlay desktop | Compilado |
| hive-dock | 2.0M | Dock bar | Compilado |
| hive-term | 2.2M | Terminal | Compilado |

---

## Ambiente de Desenvolvimento

### VM de Build
- **OS**: Ubuntu 24.04 LTS
- **ID**: vm-ubuntu-test-60eefea9
- **Disco**: 26 GB
- **SSH**: Porta 2222 (via QEMU user networking)
- **Chave**: `qemu-workspace/keys/id_ed25519`

### Conectar na VM de Build
```bash
# Windows (Git Bash)
ssh -i qemu-workspace/keys/id_ed25519 -p 2222 lab@127.0.0.1

# Iniciar VM primeiro
start "" "C:\Program Files\qemu\qemu-system-x86_64.exe" \
    -m 2048 -smp 1 \
    -hda qemu-workspace/vms/vm-ubuntu-test-60eefea9/disk-overlay.qcow2 \
    -cdrom qemu-workspace/vms/vm-ubuntu-test-60eefea9/seed.iso \
    -netdev user,id=net0,hostfwd=tcp::2222-:22 \
    -device virtio-net-pci,netdev=net0 \
    -display none -machine pc -cpu qemu64
```

---

## Estrutura do Projeto

```
druidos/
├── dist/                          # DISTRIBUIÇÃO
│   ├── druidos-bonsai.iso         # ISO bootável (27MB)
│   ├── bonsai-kernel              # Kernel (15MB)
│   ├── bonsai-initramfs.img       # Initramfs (700KB)
│   └── README.md                  # Documentação
│
├── build/output/                  # Build temporário
│   ├── bonsai-kernel
│   └── bonsai-initramfs.img
│
├── crates/                        # Código fonte Hive Stack
│   ├── hive-common/
│   ├── hive-cortex/
│   ├── hive-synapse/
│   └── ...
│
├── bonsai/                        # Scripts de build do kernel/initramfs
│   ├── scripts/
│   │   ├── build-initramfs.sh
│   │   ├── build-kernel.sh
│   │   ├── build-iso.sh
│   │   └── run-qemu.sh
│   └── config/
│       └── bonsai_defconfig
│
├── qemu-workspace/                # VMs e artefatos QEMU
│   ├── keys/id_ed25519            # Chave SSH
│   ├── vms/                       # Discos das VMs
│   └── base-images/               # Cloud images
│
├── scripts/                       # Scripts de build (legado)
├── config/                        # Configurações
├── knowledge/                     # Base de conhecimento
│
├── Cargo.toml                     # Workspace Rust
├── CLAUDE.md                      # Guia para IA
├── STATUS.md                      # ESTE ARQUIVO
└── DEVLOG.md                      # Log de desenvolvimento
```

---

## O Que Falta Para Sistema Completo

### 1. Sistema Base
O initramfs atual é só BusyBox. Para um sistema completo:
- Root filesystem (squashfs ou ext4)
- Systemd como init
- Usuário `druid` com login
- Rede configurada

### 2. Hive Stack
Os binários estão compilados mas não integrados:
- Copiar para /usr/bin
- Criar services systemd
- Configurar /etc/hive/config.toml
- Iniciar cortex no boot

### 3. IA
Modelo funcionando via llama-server:
- Qwen 2.5 0.5B carrega no boot
- Comando `ask` permite interação
- **Próximo**: Integrar hive-synapse com llama-server API
- **Próximo**: Conectar nerves ao cortex para sugestões contextuais

### 4. Desktop
Não integrado ainda:
- Wayland/Hyprland
- Sessão gráfica
- Overlay hive-shell

---

## Decisões Arquiteturais

1. **Boot Direto vs ISO**: Suportamos ambos. Boot direto é mais rápido para dev.
2. **Kernel Ubuntu**: Usando kernel pré-compilado do Ubuntu por praticidade.
3. **BusyBox Estático**: Baixamos binário pré-compilado (musl) para evitar problemas de compilação.
4. **Build na VM**: Compilação na VM Ubuntu, não cross-compile do Windows.

---

## Problemas Conhecidos

1. **Nested Virtualization**: Boot pode ser lento sem KVM/WHPX (~1 token/s para inferência)
2. **VNC vs Serial**: Para v0.3-slm usar VNC (requer console gráfico)
3. **llama.cpp AVX**: Binário pré-compilado falha com "Illegal instruction" - precisa compilar sem AVX
4. **Loopback Network**: Initramfs precisa configurar `ifconfig lo 127.0.0.1 up` para HTTP local
3. **Line Endings**: Scripts copiados do Windows precisam de `sed -i 's/\r$//'`

---

## Próxima Sessão

> **Nota (pivot de alvo):** o projeto foi redefinido para TUI-only — sem GUI.
> bark/spore/hive-shell/hive-dock/hive-term foram movidos para `archive/`.
> Ver `DEVLOG.md` (entrada mais recente) e `CLAUDE.md`. A antiga "Opção B:
> Desktop Mínimo" não se aplica mais.

### Opção A: v0.4 - Integração Nerves
1. Conectar hive-nerve-process ao cortex
2. Nerve observa comandos executados
3. Cortex envia contexto para SLM
4. Sugestões automáticas baseadas em comandos

### Opção B: Persistência
1. Root filesystem (squashfs ou ext4)
2. Login de usuário (druid)
3. Rede automática (DHCP)

### Opção C: Grove UX
1. Definir mecanismo de notificação do Hive sem GUI (inline no Grove vs painel TUI separado — ainda em aberto)
2. Integrar Grove com hive-cortex como componente "Shell"

## Histórico de Versões

| Versão | Data | Descrição |
|--------|------|-----------|
| v0.1 | 2026-02-20 | Boot mínimo (BusyBox) |
| v0.2 | 2026-02-20 | hive-cortex funcionando |
| v0.3 | 2026-02-20 | SLM funcionando (ask) |
| v0.4-fb | 2026-02-20 | Framebuffer test (EM DESENVOLVIMENTO) |

---

## v0.4-fb - Framebuffer (ARQUIVADO)

> O alvo do projeto foi redefinido para TUI-only (sem GUI). `bark` e `spore`
> foram movidos para `archive/bark` e `archive/spore`, fora do workspace
> ativo. Os fixes descritos abaixo continuam no código arquivado, só não
> são mais compilados/testados por padrão. Seção mantida como registro
> histórico.

### Status
- `/dev/fb0` aparece com `vga=0x31B` (1280x1024x24bpp)
- `fb-test` abre framebuffer com sucesso
- **PROBLEMA**: Segfault no mmap

### Causa Raiz
O código em `bark/src/framebuffer.rs` usa `MmapMut::map_mut(&file)` que não funciona para device files. Precisa especificar tamanho explícito.

### Fixes Aplicados (NÃO COMPILADOS)

#### Fix 1: mmap com tamanho explícito (linha ~169)
```rust
// ANTES (quebrado):
let mmap = unsafe {
    MmapMut::map_mut(&file)
        .map_err(|e| BarkError::MmapFailed(...))?
};

// DEPOIS (fix):
let mmap = unsafe {
    memmap2::MmapOptions::new()
        .len(size)
        .map_mut(&file)
        .map_err(|e| BarkError::MmapFailed(...))?
};
```

#### Fix 2: flush() com suporte a 24bpp (linha ~312)
O método `flush()` foi reescrito para converter u32 backbuffer para:
- 32bpp: cópia direta
- 24bpp: converte para BGR (3 bytes por pixel)
- 16bpp: converte para RGB565

### Como Testar DruidOS v0.4
```powershell
# Iniciar DruidOS com framebuffer (VNC porta 5901)
& "C:\Program Files\qemu\qemu-system-x86_64.exe" -m 512 `
    -kernel "C:\projetos\druidos\dist\v0.4-fb\bonsai-kernel" `
    -initrd "C:\projetos\druidos\dist\v0.4-fb\bonsai-initramfs.img" `
    -append "console=tty0 noapic nolapic vga=0x31B" `
    -vga std -vnc :1

# Conectar VNC: localhost:5901
# Executar: fb-test
```

### Scripts Auxiliares
- `C:\projetos\druidos\run-fb.ps1` - Inicia DruidOS com framebuffer
- `C:\projetos\druidos\kill-all-qemu.ps1` - Mata todos QEMU
- `C:\projetos\druidos\build-fb-test.sh` - Compila fb-test (rodar no Linux)

### Próximo Passo: Compilar fb-test

**Opção 1: WSL Ubuntu (Recomendado)**
```powershell
wsl --install -d Ubuntu
# Reiniciar Windows
# Depois:
cd /mnt/c/projetos/druidos
bash build-fb-test.sh
```

**Opção 2: VM Externa**
Copiar projeto para qualquer Linux e rodar `build-fb-test.sh`

### Problema com VM Ubuntu Build
A VM Ubuntu atual (vm-ubuntu-build-529bc657) tem kernel panic:
```
Kernel panic - not syncing: IO-APIC + timer doesn't work!
Boot with the 'noapic' option.
```
- Disco foi expandido (+5GB) mas não ajuda
- WHPX não funciona: "No space left on device"
- Precisa modificar GRUB para adicionar `noapic`

### Parâmetros VESA
| vga | Resolução | bpp | /dev/fb0 |
|-----|-----------|-----|----------|
| 0x31B | 1280x1024 | 24 | SIM |
| 0x318 | 1024x768 | 24 | ? |
| 0x118 | 1024x768 | 32 | NÃO |
| 0x11B | 1280x1024 | 32 | ? |
