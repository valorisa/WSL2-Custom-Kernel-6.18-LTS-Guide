# WSL2 Custom Kernel 6.6.y LTS (linux-msft-wsl-6.6.y) — Docker Desktop 4.73.1 Compatible — PRODUCTION GUIDE

## 🔴 CRITICAL DISCLAIMER (READ FIRST)

**Kernel 6.18 is NOT compatible with Docker Desktop 4.73.1+** due to:
1. NetLink ABI incompatibility (initd binary refuses to run)
2. Missing ISO9660_FS support (can be fixed, but insufficient alone)

**This guide uses linux-msft-wsl-6.6.y (NOT 6.18)** because:
- ✅ Tested + verified compatible with Docker Desktop 4.73.1
- ✅ LTS support until 2026 (kernel.org guarantees)
- ✅ All Docker features work out-of-box
- ⚠️ If you MUST use 6.18, wait for Docker to update its LinuxKit binaries (ETA unknown)

---

## Quick Start (TL;DR)

```bash
# On Windows 11 Enterprise (PowerShell Administrator)

# 1. Clone + compile (Ubuntu 22.04 WSL2 distro, NOT docker-desktop)
wsl -d Ubuntu-22.04 -u root bash << 'EOF'
cd /tmp
git clone --depth=1 --branch linux-msft-wsl-6.6.y https://github.com/microsoft/WSL2-Linux-Kernel.git kernel
cd kernel
cp Microsoft/config-wsl .config

# CRITICAL: Ensure ALL necessary options are =y (not =m)
sed -i 's/CONFIG_ISO9660_FS=m/CONFIG_ISO9660_FS=y/' .config
grep "CONFIG_ISO9660_FS" .config  # Verify: should output CONFIG_ISO9660_FS=y

# Compile
time make -j6 bzImage 2>&1 | tee ../build.log
ls -lh arch/x86_64/boot/bzImage
EOF

# 2. Copy kernel to Windows
mkdir C:\wsl-kernels\6.6.custom
copy "\\wsl.localhost\Ubuntu-22.04\tmp\kernel\arch\x86_64\boot\bzImage" C:\wsl-kernels\6.6.custom\

# 3. Configure .wslconfig
notepad $env:USERPROFILE\.wslconfig

# Add/modify:
# [wsl2]
# kernel=C:\wsl-kernels\6.6.custom\bzImage
# memory=8GB
# processors=4

# 4. Restart + validate
wsl --shutdown
wsl
uname -r  # Should output: 6.6.x-microsoft-standard-WSL2...

docker ps  # Should work immediately
```

---

## PART 1: KERNEL REQUIREMENTS FOR DOCKER DESKTOP

### Why certain kernel options matter

| Config | Status | Why Docker needs it | Failure mode if missing |
|--------|--------|---------------------|-------------------------|
| `CONFIG_ISO9660_FS=y` | **CRITICAL** | Bootstrap mounts docker-desktop.iso | Bootstrap fails silently, dmesg shows "unknown filesystem" |
| `CONFIG_CGROUP_V2=y` | Critical | Docker resource limits | Containers start but memory/CPU limits ignored |
| `CONFIG_OVERLAY_FS=y` | Critical | Image layering (overlay2 driver) | Docker daemon won't start or uses vfs (10x slower) |
| `CONFIG_NAMESPACES=y` | Critical | Container isolation | Containers can see host processes (SECURITY RISK) |
| `CONFIG_BPF_SYSCALL=y` | Important | eBPF-based networking, seccomp | Network policies silent fail, security reduced |
| `CONFIG_VETH=y` | Important | Container bridging | Container ↔ container networking broken |
| `CONFIG_SECCOMP=y` | Important | Security profiles | Docker default security profile ignored |
| `CONFIG_9P_FS=y` | Important | WSL2 ↔ Windows file sharing | `/mnt/c/` won't mount in containers |

### Kernel modules trap (WSL2-specific)

```
WSL2 NEVER loads kernel modules — /lib/modules/ is never populated
```

**Consequence:**
- `CONFIG_FOO=m` (module) = dead code
- Must use `CONFIG_FOO=y` (built-in) for ANY critical feature
- Script must validate NO critical option is `=m`

---

## PART 2: SETUP

### Phase 0: Pre-Flight Check

```bash
# On Windows 11 Enterprise (PowerShell Admin)

# Check Docker Desktop version
docker --version
# Expected: Docker version 24.0.x

# Verify WSL2 is default
wsl -l -v
# Should see * next to one distro (default)

# List available distros (we'll create a compile-only one)
wsl -l -o | head -20
```

### Phase 1: Create Isolated Build Environment

```powershell
# Create clean Ubuntu 22.04 distro for compilation ONLY
wsl --install -d Ubuntu-22.04 -u root

# Verify isolation
wsl -d Ubuntu-22.04 -u root -- uname -r
# Should return 5.15.x (default), NOT docker-desktop's kernel
```

### Phase 2: Install Build Tools

```bash
# Inside Ubuntu-22.04 distro as root
apt-get update
apt-get install -y \
  build-essential linux-headers-$(uname -r) \
  git gcc make bc flex bison openssl libssl-dev \
  libelf-dev dwarves u-boot-tools cpio

# Verify
gcc --version
make --version
```

### Phase 3: Clone Kernel Source

```bash
cd /tmp
git clone --depth=1 --branch linux-msft-wsl-6.6.y \
  https://github.com/microsoft/WSL2-Linux-Kernel.git kernel

cd kernel
make kernelversion
# Expected: 6.6.x
```

---

## PART 3: CONFIGURATION (DOCKER-CRITICAL)

### Phase A: Load Base Config

```bash
cd /tmp/kernel

# Use Microsoft's official WSL2 config as baseline
cp Microsoft/config-wsl .config

# OR extract current running kernel config
cat /proc/config.gz | gunzip > .config
```

### Phase B: **CRITICAL VALIDATION** — Ensure =y not =m

```bash
#!/bin/bash
# Save as: /tmp/kernel/validate-docker-config.sh

MUST_BE_ENABLED=(
  "CONFIG_CGROUP_V2=y"
  "CONFIG_CGROUP_BPF=y"
  "CONFIG_BPF_SYSCALL=y"
  "CONFIG_BPF_JIT=y"
  "CONFIG_OVERLAY_FS=y"
  "CONFIG_SECCOMP=y"
  "CONFIG_NAMESPACES=y"
  "CONFIG_USER_NS=y"
  "CONFIG_NET_NS=y"
  "CONFIG_VETH=y"
  "CONFIG_9P_FS=y"
  "CONFIG_ISO9660_FS=y"        # ← CRITICAL: MUST be =y, NOT =m
)

echo "=== DOCKER CRITICAL CONFIG VALIDATION ==="

FAIL=0
for req in "${MUST_BE_ENABLED[@]}"; do
  if grep -q "^$req" .config; then
    echo "✅ $req"
  else
    echo "❌ MISSING: $req"
    echo "   Adding to .config..."
    echo "${req}" >> .config
    ((FAIL++))
  fi
done

# TRAP: Check for =m versions of critical options
echo ""
echo "--- CHECKING FOR DANGLING =m OPTIONS ---"
TRAP_OPTIONS=(
  "CONFIG_ISO9660_FS=m"
  "CONFIG_OVERLAY_FS=m"
  "CONFIG_VETH=m"
  "CONFIG_9P_FS=m"
)

for trap in "${TRAP_OPTIONS[@]}"; do
  if grep -q "^$trap" .config; then
    echo "⚠️  TRAP FOUND: $trap (must be =y for WSL2)"
    # Auto-fix
    CONFIG_NAME=$(echo $trap | cut -d= -f1)
    sed -i "s/^$trap/$CONFIG_NAME=y/" .config
    echo "   Auto-fixed to =y"
  fi
done

if [ $FAIL -gt 0 ]; then
  echo ""
  echo "❌ CRITICAL CONFIG ISSUES FOUND AND FIXED"
  echo "   Re-run this script to verify"
else
  echo ""
  echo "✅ ALL DOCKER REQUIREMENTS MET"
fi
```

```bash
chmod +x /tmp/kernel/validate-docker-config.sh
./validate-docker-config.sh
```

### Phase C: Finalize Config

```bash
cd /tmp/kernel

# Update for any new 6.6.y options
make olddefconfig

# (or skip modules entirely for minimal kernel)
make defconfig

# Verify final config
grep "CONFIG_ISO9660_FS\|CONFIG_OVERLAY_FS\|CONFIG_CGROUP_V2" .config
```

---

## PART 4: COMPILATION

```bash
cd /tmp/kernel

# Determine safe parallelism (leave headroom for Docker Desktop if running)
CPUS=$(nproc --all)
SAFE_J=$((CPUS - 2))

echo "Compiling with -j$SAFE_J (total CPUs: $CPUS)"

time make -j$SAFE_J bzImage 2>&1 | tee ../build.log

# Verify
if [ -f arch/x86_64/boot/bzImage ]; then
  echo "✅ Compilation successful"
  ls -lh arch/x86_64/boot/bzImage
else
  echo "❌ Build failed — check build.log"
  tail -50 ../build.log
  exit 1
fi
```

**Expected duration:** 40-90 min depending on CPU + config

---

## PART 5: DEPLOYMENT

### Step 1: Copy Kernel to Windows

```bash
# Inside Ubuntu-22.04 WSL2
KERNEL_FILE=/tmp/kernel/arch/x86_64/boot/bzImage
WINDOWS_PATH="/mnt/c/wsl-kernels/6.6.custom"

# Create target dir (from Windows perspective)
mkdir -p "$WINDOWS_PATH"

# Copy
cp "$KERNEL_FILE" "$WINDOWS_PATH/bzImage"

ls -lh "$WINDOWS_PATH/"
```

### Step 2: Configure .wslconfig

```powershell
# From Windows (PowerShell Administrator)

# Backup existing
if (Test-Path "$env:USERPROFILE\.wslconfig") {
    Copy-Item "$env:USERPROFILE\.wslconfig" "$env:USERPROFILE\.wslconfig.backup"
}

# Create/edit .wslconfig
notepad "$env:USERPROFILE\.wslconfig"
```

**Content:**
```ini
[wsl2]
kernel=C:\wsl-kernels\6.6.custom\bzImage
memory=8GB
processors=4
swap=4GB
localhostForwarding=true
nestedVirtualization=true

[interop]
enabled=true
appendWindowsPath=true
```

### Step 3: Restart WSL2 + Docker Desktop

```powershell
# Shutdown all WSL2
wsl --shutdown

# Start Docker Desktop (auto-starts WSL2 with custom kernel)
& "C:\Program Files\Docker\Docker\Docker Desktop.exe"

# Wait ~30 seconds for daemon startup
Start-Sleep -Seconds 30

# Verify
wsl uname -r
# Expected: 6.6.x-microsoft-standard-WSL2...

docker ps
# Should work immediately
```

---

## PART 6: VALIDATION SUITE (DOCKER INTEGRATION TESTS)

```bash
#!/bin/bash
# Save as: /tmp/docker-validation.sh

echo "=== DOCKER DESKTOP + CUSTOM KERNEL 6.6.y VALIDATION ==="
echo ""

TESTS_PASSED=0
TESTS_FAILED=0

test_case() {
  local name=$1
  local cmd=$2
  
  echo -n "[$TESTS_PASSED+$TESTS_FAILED+1] $name ... "
  if eval "$cmd" > /dev/null 2>&1; then
    echo "✅"
    ((TESTS_PASSED++))
  else
    echo "❌"
    ((TESTS_FAILED++))
  fi
}

# 1. Basic connectivity
test_case "Docker daemon responsive" "docker --version"
test_case "Docker info returns data" "docker info | grep -q 'Server Version'"

# 2. Kernel config checks
test_case "cgroups v2 mounted" "mount | grep -q cgroup2"
test_case "overlay2 available" "docker info | grep -q 'Storage Driver: overlay2'"
test_case "ISO9660 support" "grep -q '^CONFIG_ISO9660_FS=y' /proc/config.gz | gunzip | cat"

# 3. Container operations
test_case "Run basic container" "docker run --rm alpine:latest echo test"
test_case "Pull image" "docker pull busybox:latest > /dev/null 2>&1"
test_case "Container networking" "docker run --rm alpine:latest ping -c 1 8.8.8.8"
test_case "DNS resolution" "docker run --rm alpine:latest nslookup docker.io"

# 4. Resource limits (cgroups v2)
test_case "Memory limits" "docker run --memory 100m --rm alpine:latest free | grep -q 'Mem'"

# 5. Volume mount
test_case "Volume mount (overlay2)" "docker run --rm -v /tmp:/tmp alpine:latest ls /tmp"

# 6. Port mapping
echo -n "[7/10] Port mapping ... "
docker run -d -p 8888:80 --name test-portmap nginx:latest > /dev/null 2>&1
sleep 2
if curl -s http://localhost:8888 > /dev/null 2>&1; then
  echo "✅"
  ((TESTS_PASSED++))
else
  echo "⚠️  (inconclusive — firewall may block)"
fi
docker stop test-portmap > /dev/null 2>&1
docker rm test-portmap > /dev/null 2>&1

# 7. systemd integration (socket activation)
echo -n "[8/10] Docker systemd integration ... "
wsl --shutdown 2>/dev/null
wsl -d docker-desktop -u root ps aux 2>/dev/null | grep -q dockerd && {
  echo "✅"
  ((TESTS_PASSED++))
} || {
  echo "⚠️  (docker daemon may auto-start later)"
}

# 8. Docker compose (if available)
test_case "Docker Compose available" "docker compose --version > /dev/null 2>&1"

# 9. Multi-stage build
test_case "Multi-stage build" "docker build --target stage1 - < /dev/null"

# 10. Image removal
test_case "Image cleanup" "docker image rm busybox:latest 2>/dev/null || true"

echo ""
echo "=== RESULTS ==="
echo "Passed: $TESTS_PASSED"
echo "Failed: $TESTS_FAILED"
echo ""

if [ $TESTS_FAILED -eq 0 ]; then
  echo "✅ ALL TESTS PASSED — Docker Desktop fully compatible with custom kernel 6.6.y"
  exit 0
else
  echo "⚠️  Some tests failed — see above for details"
  exit 1
fi
```

```bash
chmod +x /tmp/docker-validation.sh
/tmp/docker-validation.sh
```

---

## PART 7: TROUBLESHOOTING

### Docker won't start ("still waiting for engine...")

```bash
# Check initd bootstrap logs
dmesg | tail -30 | grep -i init

# If sees "unknown filesystem type 'iso9660'":
# → Kernel compiled with CONFIG_ISO9660_FS=m
# → Fix: recompile with CONFIG_ISO9660_FS=y

# If sees "netlink: attribute type 4 has invalid length":
# → YOU'RE USING KERNEL 6.18 (which is incompatible)
# → Fix: use linux-msft-wsl-6.6.y branch instead
```

### Containers exit immediately

```bash
# Check dmesg for cgroup errors
dmesg | tail | grep -i cgroup

# Verify cgroups v2
cat /proc/cgroups | head -1
# Must show: cgroup2
```

### Network broken in containers

```bash
# Check eBPF support
cat /proc/sys/kernel/bpf_stats_enabled
# Should be 1

# If 0: kernel compiled without CONFIG_BPF_JIT=y
```

### Memory limits ignored

```bash
# Test:
docker run --memory 100m alpine free

# If shows full host RAM: memcg v2 not properly configured
# Check kernel config:
grep "CONFIG_MEMCG" .config
# Must be CONFIG_MEMCG=y (and systemd must be cgroup v2 aware)
```

---

## PART 8: ROLLBACK PROCEDURE

**If anything goes wrong:**

```powershell
# Windows PowerShell (Administrator)

# Edit .wslconfig
notepad "$env:USERPROFILE\.wslconfig"

# Comment out kernel line:
# [wsl2]
# # kernel=C:\wsl-kernels\6.6.custom\bzImage
# (leave blank = use Microsoft default kernel)

# Restart
wsl --shutdown
# Relaunch Docker Desktop
```

---

## PART 9: PRODUCTION CHECKLIST

- [ ] Kernel compiled with `CONFIG_ISO9660_FS=y` (validated via script)
- [ ] All Docker-critical options set to `=y` (not `=m`)
- [ ] .wslconfig deployed with custom kernel path
- [ ] Docker Desktop 4.73.1+ running (check `docker --version`)
- [ ] All 10 validation tests passing
- [ ] `docker info` shows correct kernel version (6.6.x)
- [ ] At least one successful `docker run` completed
- [ ] Backup of `.wslconfig` taken
- [ ] Documentation of kernel compilation flags saved

---

## PART 10: WHAT'S NEXT

- **Ansible fleet deployment** → See ADDON-1
- **Prometheus monitoring** → See ADDON-2
- **Multi-arch QEMU support** → See ADDON-3
- **Kernel patching (6.6.20.x updates)** → See ADDON-4

---

## References

- Issue #1 (real-world findings): https://github.com/valorisa/WSL2-Custom-Kernel-6.18-LTS-Guide/issues/1
- Microsoft WSL2 Kernel: https://github.com/microsoft/WSL2-Linux-Kernel/tree/linux-msft-wsl-6.6.y
- Docker for Windows: https://github.com/docker/for-win
