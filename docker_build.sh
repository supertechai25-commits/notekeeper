#!/usr/bin/env bash
set -e

SDK_ROOT=/root/.buildozer/android/platform/android-sdk
CMDLINE=$SDK_ROOT/cmdline-tools/latest/bin

echo "=== Bypassing root check ==="
sed -i 's/cont = input/cont = "y" #/' \
  /home/user/.venv/lib/python3.12/site-packages/buildozer/__init__.py 2>/dev/null || true

echo "=== Installing cmdline-tools if missing ==="
if [ ! -f "$CMDLINE/sdkmanager" ]; then
  mkdir -p $SDK_ROOT/cmdline-tools
  cd /tmp
  python3 -c "import urllib.request; urllib.request.urlretrieve('https://dl.google.com/android/repository/commandlinetools-linux-11076708_latest.zip', 'commandlinetools-linux-11076708_latest.zip'); print('Downloaded cmdline-tools')"
  unzip -q commandlinetools-linux-11076708_latest.zip
  mv cmdline-tools $SDK_ROOT/cmdline-tools/latest
fi

echo "=== Accepting all SDK licenses ==="
mkdir -p $SDK_ROOT/licenses
echo -e "\n8933bad161af4178b1185d1a37fbf41ea5269c55\nd56f5187479451eabf01fb78af6dfcb131a6481e\n24333f8a63b6825ea9c5514f83c2829b004d1fee" \
  > $SDK_ROOT/licenses/android-sdk-license
echo -e "\n84831b9409646a918e30573bab4c9c91346d8abd" \
  > $SDK_ROOT/licenses/android-sdk-preview-license
echo -e "\nd975f751698a77b662f1254ddbeed3901e976f5a" \
  > $SDK_ROOT/licenses/intel-android-extra-license
yes | $CMDLINE/sdkmanager --licenses >/dev/null 2>&1 || true

echo "=== Installing build-tools and platform ==="
$CMDLINE/sdkmanager "build-tools;33.0.2" "platforms;android-33" "platform-tools" 2>&1 | grep -v "^$" || true

echo "=== Symlinking tools/bin for legacy buildozer path ==="
mkdir -p $SDK_ROOT/tools/bin
ln -sf $CMDLINE/sdkmanager $SDK_ROOT/tools/bin/sdkmanager 2>/dev/null || true
ln -sf $CMDLINE/avdmanager $SDK_ROOT/tools/bin/avdmanager 2>/dev/null || true

echo "=== Running buildozer ==="
cd /home/user/hostcwd
buildozer android debug 2>&1
