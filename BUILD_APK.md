# Building NoteKeeper.apk

Buildozer (the Python→APK packager) **only runs on Linux/macOS**, not native Windows.
Pick one of three paths:

---

## Path A — WSL2 (recommended, builds on your machine)

Run in PowerShell (one-time):
```powershell
wsl --install -d Ubuntu
```
Reboot, finish Ubuntu setup, then inside the Ubuntu shell:
```bash
sudo apt update
sudo apt install -y git zip unzip openjdk-17-jdk python3-pip autoconf libtool \
  pkg-config zlib1g-dev libncurses5-dev libncursesw5-dev libtinfo5 cmake \
  libffi-dev libssl-dev build-essential

pip install --user --upgrade buildozer cython==0.29.33
export PATH=$PATH:~/.local/bin

cp -r /mnt/c/Users/Super/.ollama/notekeeper ~/notekeeper
cd ~/notekeeper
buildozer -v android debug
```
First build pulls the Android SDK/NDK (~1.5 GB, 30–60 min). Resulting APK:
`~/notekeeper/bin/notekeeper-1.0.0-arm64-v8a_armeabi-v7a-debug.apk`

Copy back to Windows:
```bash
cp bin/*.apk /mnt/c/Users/Super/.ollama/notekeeper/
```

## Path B — GitHub Actions (zero local setup)

1. `cd C:\Users\Super\.ollama\notekeeper && git init && git add . && git commit -m init`
2. Create a GitHub repo, push.
3. Workflow `.github/workflows/build-apk.yml` runs automatically.
4. Download APK from the run's **Artifacts** panel.

## Path C — Docker (if Docker Desktop installed)

```bash
docker run --rm -v %cd%:/home/user/hostcwd kivy/buildozer android debug
```

---

## Install APK on your phone
1. Enable **Install unknown apps** for your file manager/browser.
2. Transfer the `.apk` via USB, Drive, or email.
3. Tap to install.

## Run on desktop (no APK needed)
```powershell
pip install kivy
python C:\Users\Super\.ollama\notekeeper\main.py
```
