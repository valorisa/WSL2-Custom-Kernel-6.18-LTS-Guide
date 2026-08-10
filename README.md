# WSL2 Custom Kernel 6.18 LTS Guide (Windows 11 Enterprise)

[![Kernel](https://img.shields.io/badge/kernel-6.18.20.3--microsoft--standard--WSL2+-brightgreen.svg)]()
[![License](https://img.shields.io/badge/license-CC--BY--SA--4.0-blue.svg)]()
[![PowerShell](https://img.shields.io/badge/PowerShell-7.6.1-blue.svg)]()
[![Ubuntu](https://img.shields.io/badge/Ubuntu-25.10-orange.svg)]()

**Guide COMPLET et RIGOUREUX : Compilation du noyau Linux 6.18 LTS pour WSL2 sous Windows 11 Enterprise (PowerShell 7.6+)**

> **Créé le 25 avril 2026** - Expérience réelle avec **TOUTES les galères et solutions**
>
> **Mis à jour le 26 avril 2026 et le 10 août 2026** - Ajout de **Préparation Complète de l'Environnement**

## 🛠️ Préparation Complète de l'Environnement

Cette section **préparatoire essentielle** détaille **TOUS** les prérequis pour éviter les échecs courants. Le guide utilise **deux environnements distincts** :
- **Windows/PowerShell 7.6+** : Pour les commandes de gestion WSL (étapes 6-8 : déploiement, `.wslconfig`, activation).
- **Ubuntu 25.10/26.04 (WSL2)** : Pour la compilation du noyau (étapes 1-5 : préparation, clonage, make).

| Environnement | Parties concernées | Commandes exécutées | Prérequis |
| ------------- | ------------------ | ------------------- | --------- |
| **PowerShell 7.6.1 (Windows)** | Étapes 6,7,8 + Activation finale | `wsl --shutdown`, édition `.wslconfig` | Installation manuelle (voir ci-dessous) |
| **Ubuntu 25.10 (WSL2)** | Étapes 1-5 | `apt install`, `git clone`, `make` | WSL installé + distro Ubuntu |

**⚠️ Sans cette préparation, échecs garantis** : "wsl introuvable", "pwsh.exe manquant", compilation impossible.

### 1. Vérifier/Installer WSL2 (si manquant)

WSL2 n'est **pas toujours activé** sur Windows 11 Enterprise. Vérifiez d'abord :

```powershell
# Dans PowerShell 5.1 ou 7 (admin)
wsl --version
```

- **Si erreur "wsl introuvable"** → Installez WSL2.
- **Méthode officielle (10 min)** :

```powershell
# Terminal Admin (PowerShell ou CMD)
wsl --install
# Installe WSL2 + noyau par défaut + Ubuntu (première distro)
```

**Redémarrez Windows**, puis :
```powershell
wsl --install -d Ubuntu-25.10  # Si version spécifique souhaitée
wsl --set-default-version 2    # Force WSL2
wsl --update                   # Noyau à jour
```

**Vérification** :
```powershell
wsl --list --verbose  # Doit montrer Ubuntu-25.10 (WSL2). Sinon, installer une distro Linux de votre choix
```

**Problème courant** : Virtualisation désactivée → Activez dans BIOS/UEFI ("SVM" AMD / "VT-x" Intel).

### 2. Installer PowerShell 7.6.1 (Non Natif !)

**PowerShell 5.1** est **préinstallé** sur Windows 11 (tapez `powershell`).
**PowerShell 7.6.1** (Core) **doit être installé manuellement** car **cross-platform** et moderne.

#### Méthode Recommandée : Winget (1 ligne)
```powershell
# Terminal Admin
winget install --id Microsoft.PowerShell --source winget
```

#### Alternative : MSI Officiel
1. Téléchargez `PowerShell-7.6.1-win-x64.msi` depuis [GitHub PowerShell](https://github.com/PowerShell/PowerShell/releases/tag/v7.6.1).
2. Exécutez (avec les droits admin) : `msiexec.exe /package PowerShell-7.6.1-win-x64.msi /quiet ADD_EXPLORER_CONTEXT_MENU_OPENPOWERSHELL=1 ADD_PATH=1`

**Lancement** : Tapez `pwsh` (pas `powershell`).

**Vérification** :
```powershell
pwsh -v  # → 7.6.1
$PSVersionTable  # Détails complets
```

#### Différences PowerShell 5.1 vs 7.6.1 (Explication Simple)
| Aspect | PowerShell 5.1 (Natif Windows) | PowerShell 7.6.1 (Core) |
| ------ | ------------------------------ | ----------------------- |
| **Plateforme** | Windows seulement | Windows/Linux/macOS |
| **Performance** | Plus lente (57x moins sur gros datasets) | **57x plus rapide** sur pipelines lourds |
| **Fonctionnalités** | Base | **Nouvelles** : `ForEach-Object -Parallel`, SSH natif, ternaire (`? :`), conteneurs Docker |
| **Coexistence** | `powershell.exe` | `pwsh.exe` **côte-à-côte** (pas de conflit) |
| **Utilisation ici** | OK pour basique | **Requis** pour WSL avancé/performant |

**Pourquoi 7.6.1 ?** Meilleure compatibilité WSL2, scripts cross-platform, futur-proof.

### 3. Vérifications Finales Avant Guide
```powershell
# Dans pwsh (admin)
wsl --version              # OK
wsl -l -v                  # Ubuntu prêt
pwsh -v                    # 7.6.1
```

**Espace disque** : 6Go+ libre (C:\ + WSL VHDX).
**RAM** : 8Go+ (compilation -j$(nproc)).

**Prêt ?** Passez à la section suivante ! 🚀

## 🎯 Pourquoi ce guide ?

**Problème identifié** : `wsl --version` affiche `6.6.114.1-1` (obsolète)  
**Solution validée** : `6.18.20.3-microsoft-standard-WSL2+` (LTS jusqu'en 2027)

```text
Avant : 6.6.114.1-1 (2024) - Support fin 2026
Après : 6.18.20.3+ (2026) - Support jusqu'en 2027 ✅
```

## 📋 Environnement testé

```text
💻 Windows 11 Enterprise (10.0.26200.8246)
⚡ PowerShell Core 7.6.1
🐧 Ubuntu-25.10 (WSL2)
🐧 Oracle Linux 9.5 (WSL2)
💾 Espace requis : 6Go+ 
🧠 RAM recommandée : 8Go+
```

## 🚀 Guide pas à pas (REPRODUCTIBLE)

### 1. Préparation Ubuntu (WSL2)

```bash
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential flex bison dwarves libssl-dev libelf-dev bc cpio qemu-utils rsync git
```

### 2. Clonage sources OFFICIELLES Microsoft

```bash
# BRANCHE CRITIQUE : linux-msft-wsl-6.18.y
git clone --branch linux-msft-wsl-6.18.y https://github.com/microsoft/WSL2-Linux-Kernel.git
cd WSL2-Linux-Kernel
```

> **⚠️ ERREUR FATALE** : Sans `--branch`, vous clonez `6.6.y` par défaut !

### 3. Configuration noyau WSL2

```bash
make clean
sudo make KCONFIG_CONFIG=Microsoft/config-wsl
```

### 4. Compilation (⏱️ 20-40min)

```bash
# COMMANDE UNIQUE Microsoft OFFICIELLE
sudo make -j$(nproc) KCONFIG_CONFIG=Microsoft/config-wsl && \
sudo make INSTALL_MOD_PATH="$PWD/modules" modules_install KCONFIG_CONFIG=Microsoft/config-wsl
```

**Succès** :
```text
DEPMOD  /modules/lib/modules/6.18.20.3-microsoft-standard-WSL2+
```

### 5. Vérification

```bash
ls -lh arch/x86/boot/bzImage           # 17.5Mo ✓
ls modules/lib/modules/6.18.20.3-microsoft-standard-WSL2+/  # Modules ✓
```

### 6. Déploiement Windows

```bash
mkdir -p /mnt/c/wsl-kernels/6.18.20.3/
cp arch/x86/boot/bzImage /mnt/c/wsl-kernels/6.18.20.3/
cp -r modules/lib/modules/6.18.20.3-microsoft-standard-WSL2+ /mnt/c/wsl-kernels/6.18.20.3/modules/
```

### 7. Configuration `.wslconfig`

**Fichier** : `C:\Users\bbrod\.wslconfig`
```ini
[wsl2]
kernel=C:\\wsl-kernels\\6.18.20.3\\bzImage
```

### 8. Activation

```powershell
# PowerShell (admin)
wsl --shutdown
wsl
```

**Test final** :
```bash
uname -r
# → 6.18.20.3-microsoft-standard-WSL2+  🎉
```

### 9. Résumé (MAJ le 10 août 2026)

```bash
###############################################################################
# MIGRATION NOYAU WSL2 CUSTOM — Procédure complète
# Environnements : [UBUNTU] = terminal Ubuntu (WSL) | [POWERSHELL] = PowerShell Windows
# Dernière validation : 6.18.40.1, build réussi en ~20min sur 4 cœurs
#
# NOTE : <WIN_USER> désigne ton nom d'utilisateur Windows (ex: ton_username).
#        Vu depuis Ubuntu    : /mnt/c/Users/<WIN_USER>/...
#        Vu depuis PowerShell : C:\Users\<WIN_USER>\...
#        C'est le MÊME compte, juste deux syntaxes de chemin différentes.
###############################################################################

# ============================================================
# [UBUNTU] 1. Préparer l'environnement (une seule fois, sauf si dépendances manquantes)
# ============================================================
cd ~
sudo apt update && sudo apt upgrade -y
sudo apt install -y build-essential flex bison libssl-dev libelf-dev \
  bc dwarves python3 python3-pip pahole cpio rsync kmod tmux
df -h ~        # vérifier l'espace dispo (15-20 Go nécessaires)
nproc          # nombre de cœurs disponibles pour -j

# ============================================================
# [UBUNTU] 2. Cloner le tag kernel WSL voulu
# Remplacer VERSION par le tag exact (ex: 6.18.45.1)
# Vérifier le nom exact du tag sur : https://github.com/microsoft/WSL2-Linux-Kernel/releases
# ============================================================
VERSION="6.18.40.1"   # <-- à adapter à chaque nouvelle version
cd ~/Projets
git clone --depth 1 --branch "linux-msft-wsl-${VERSION}" \
  https://github.com/microsoft/WSL2-Linux-Kernel.git "wsl-kernel-${VERSION}"
cd "wsl-kernel-${VERSION}"

# Vérification de cohérence (optionnelle mais recommandée)
head -5 Makefile   # doit afficher VERSION/PATCHLEVEL/SUBLEVEL correspondant au tag

# ============================================================
# [UBUNTU] 3. Config officielle WSL + resynchronisation
# ============================================================
cp Microsoft/config-wsl .config
make olddefconfig
head -3 .config    # doit confirmer la bonne version dans le commentaire généré

# ============================================================
# [UBUNTU] 4. Compilation sous tmux (résiste aux déconnexions SSH/terminal)
# ============================================================
tmux new -s wsl-kernel-build
# --- dans la session tmux ---
cd ~/Projets/"wsl-kernel-${VERSION}"
time make -j$(nproc) 2>&1 | tee build.log
# --- une fois lancé, détacher avec : Ctrl+b puis d ---

# Pour suivre la progression sans se rattacher :
tmux capture-pane -t wsl-kernel-build -p | tail -30

# Pour se rattacher pleinement :
tmux attach -t wsl-kernel-build

# Si la session tmux est perdue (crash VM), simplement relancer make :
# make est incrémental, il reprend où il s'est arrêté.

# ============================================================
# [UBUNTU] 5. Vérifier le build et copier le résultat vers Windows
# Remplacer <WIN_USER> par ton nom d'utilisateur Windows
# ============================================================
ls -la arch/x86/boot/bzImage         # doit exister, ~15 Mo
grep -i "error:" build.log           # doit être vide

mkdir -p /mnt/c/Users/<WIN_USER>/wsl-kernel
cp arch/x86/boot/bzImage "/mnt/c/Users/<WIN_USER>/wsl-kernel/bzImage-${VERSION}"
ls -la /mnt/c/Users/<WIN_USER>/wsl-kernel/

# ============================================================
# [POWERSHELL] 6. Configurer .wslconfig
# Remplacer <WIN_USER> par ton nom d'utilisateur Windows
# ============================================================
# notepad C:\Users\<WIN_USER>\.wslconfig
#
# Contenu (adapter le nom de fichier à chaque version) :
# [wsl2]
# kernel=C:\\Users\\<WIN_USER>\\wsl-kernel\\bzImage-6.18.40.1

# ============================================================
# [POWERSHELL] 7. Redémarrer WSL
# ============================================================
# wsl --shutdown
# wsl

# ============================================================
# [UBUNTU] 8. Vérifier la version active
# ============================================================
uname -r    # attendu : <VERSION>-microsoft-standard-WSL2+

# ============================================================
# [UBUNTU] 9. Nettoyage du dossier de build (garder le bzImage copié)
# ============================================================
cd ~/Projets
rm -rf "wsl-kernel-${VERSION}"
tmux kill-session -t wsl-kernel-build 2>/dev/null || true

# ============================================================
# [POWERSHELL] 10. ROLLBACK — si problème au démarrage après changement de noyau
# ============================================================
# notepad C:\Users\<WIN_USER>\.wslconfig
# -> supprimer/commenter la ligne "kernel="
# wsl --shutdown
# wsl
# (retour au noyau géré par Microsoft, ex: 6.18.33.2)
###############################################################################
```

## 🐛 GALÈRES & SOLUTIONS réelles

| Problème | Cause | Solution |
|----------|-------|----------|
| `No such file or directory` (VHDX) | `WSL2+` vs `WSL2` | Copie manuelle `/modules/` |
| `wsl --version` → 6.6 | Info statique Microsoft | `uname -r` = vérité |
| OOM compilation | `-j$(nproc)` trop élevé | `make -j4` |
| Dépendances manquantes | `bc`, `rsync` | `apt install bc rsync` |

## 📊 Résultats

| Métrique | Avant | Après |
|----------|-------|-------|
| **Noyau** | `6.6.114.1-1` | **`6.18.20.3-microsoft-standard-WSL2+`** |
| **Support LTS** | Fin 2026 | **Fin 2027** |
| **Distros impactées** | Aucune | **Ubuntu + Oracle Linux** |
| **`wsl --version`** | `6.6.114.1-1` | `6.6.114.1-1` (statique) |

## 🧹 Nettoyage

```bash
cd ~
rm -rf WSL2-Linux-Kernel/  # Libère 3Go
```

## 🔄 Maintenance

**Mise à jour** :
```bash
cd WSL2-Linux-Kernel
git pull origin linux-msft-wsl-6.18.y
# Étapes 3→8
```

**Rollback** :
```ini
[wsl2]
# kernel=...  ← Supprimez la ligne
```

## 📚 Sources officielles

- [Microsoft WSL2 Kernel 6.18.y](https://github.com/microsoft/WSL2-Linux-Kernel/tree/linux-msft-wsl-6.18.y)
- [WSL .wslconfig](https://learn.microsoft.com/fr-fr/windows/wsl/wsl-config)
- [Linux 6.18 LTS](https://kernelnewbies.org/Linux_6.18)

## 🪪 Licence

```text
Copyright (c) 2026 valorisa (Bertrand Brodeau)
Licence CC-BY-SA 4.0
```

## 🙌 Crédits

**Expérience réelle du 25 avril 2026 (MAJ le 10 août 2026)** :
- Compilation réussie `6.18.20.3-microsoft-standard-WSL2+`
- Compilation réussie `6.18.40.1-microsoft-standard-WSL2+`
- Toutes galères incluses et résolues
- Guide 100% reproductible

**Vous aussi, passez à 6.18 LTS !** 🚀
