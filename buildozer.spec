[app]
title = NoteKeeper
package.name = notekeeper
package.domain = org.local.notekeeper
source.dir = .
source.include_exts = py,png,jpg,kv,atlas,json
version = 1.0.0
requirements = python3,kivy
orientation = portrait
fullscreen = 0
android.archs = arm64-v8a, armeabi-v7a
android.api = 34
android.minapi = 21
android.ndk_api = 24
android.permissions = INTERNET, WRITE_EXTERNAL_STORAGE, READ_EXTERNAL_STORAGE
log_level = 2

[buildozer]
warn_on_root = 1